#!/usr/bin/env python3
"""Package an accepted STS2 build by its exact file allowlist. Python 3.9+."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

CHUNK = 1024 * 1024


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return stream_hash(stream)


def stream_hash(stream) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(CHUNK), b""):
        digest.update(block)
    return digest.hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def safe_relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or path.is_absolute()
            or any(part in ("", ".", "..") for part in name.split("/"))):
        raise ValueError("Unsafe relative path: " + name)
    return path


def checked_files(build: dict, source: Path) -> dict[str, dict]:
    expected = build.get("files")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Build report must contain a nonempty 'files' SHA-256 map")
    result = {}
    for name, digest in sorted(expected.items()):
        relative = safe_relative(name)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid SHA-256: " + name)
        candidate = source.joinpath(*relative.parts)
        if candidate.resolve() != candidate.absolute() or not candidate.is_file():
            raise ValueError("Missing file or symlink in build: " + name)
        if sha256(candidate) != digest:
            raise ValueError("Build file hash mismatch: " + name)
        result[name] = {"sha256": digest, "bytes": candidate.stat().st_size}
    return result


def inspect_archive(path: Path) -> dict[str, str]:
    """Hash every regular entry; fully reading also checks each ZIP CRC."""
    result = {}
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            safe_relative(entry.filename.rstrip("/"))
            if entry.is_dir():
                continue
            if entry.filename in result:
                raise ValueError("Duplicate ZIP entry: " + entry.filename)
            if stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Symlink in ZIP: " + entry.filename)
            with archive.open(entry) as stream:
                result[entry.filename] = stream_hash(stream)
    return result


def add_bytes(archive: zipfile.ZipFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data)


def create_package(source: Path, build_path: Path, acceptance_path: Path,
                   mod_id: str, platform: str, install_notes: Path,
                   output: Path, reuse_zip: Path | None = None) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", mod_id):
        raise ValueError("Invalid mod ID")
    source = source.resolve()
    output = output.absolute()
    sidecar = output.with_suffix(".manifest.json")
    checksums = output.with_suffix(".sha256")
    if any(path.exists() for path in (output, sidecar, checksums)):
        raise ValueError("Output already exists; choose a new name or inspect it first")
    build = json.loads(build_path.read_text(encoding="utf-8-sig"))
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8-sig"))
    if acceptance.get("passed") is not True:
        raise ValueError("Acceptance report has not passed")
    if acceptance.get("artifacts") != build.get("files"):
        raise ValueError("Acceptance artifact map does not match the build")
    files = checked_files(build, source)
    manifest_name = mod_id + ".json"
    if manifest_name not in files:
        raise ValueError("Missing mod manifest in the accepted file map")
    manifest = json.loads((source / manifest_name).read_text(encoding="utf-8-sig"))
    version = manifest.get("version")
    if (manifest.get("id") != mod_id or not isinstance(version, str)
            or acceptance.get("version") != version):
        raise ValueError("Mod ID/version does not match acceptance")
    for flag, suffix in (("has_pck", ".pck"), ("has_dll", ".dll")):
        if manifest.get(flag) and mod_id + suffix not in files:
            raise ValueError("Manifest requires missing runtime file: " + suffix)
    notes = install_notes.read_bytes()
    if not notes.strip():
        raise ValueError("Installation notes must not be empty")
    extras = sorted(str(path.relative_to(source)) for path in source.rglob("*")
                    if path.is_file() and str(path.relative_to(source)) not in files)
    metadata = {
        "schema": 1, "mod_id": mod_id, "version": version, "platform": platform,
        "min_game_version": manifest.get("min_game_version"),
        "dependencies": manifest.get("dependencies", []),
        "affects_gameplay": manifest.get("affects_gameplay"),
        "runtime_files": files, "excluded_unlisted_files": extras,
        "verification": {
            "acceptance_passed": True,
            "acceptance_report_sha256": sha256(acceptance_path),
            "artifact_hashes_match": True,
            "acceptance_checks": {key: value for key, value in acceptance.get("checks", {}).items()
                                  if isinstance(value, bool)},
        },
    }
    for field in ("full_native_checks", "fixed_native_checks", "scope_limits"):
        if field in acceptance:
            metadata["verification"][field] = acceptance[field]
    payloads = {
        "RELEASE/INSTALL.md": notes,
        "RELEASE/manifest.json": json_bytes(metadata),
    }
    expected = {mod_id + "/" + name: item["sha256"] for name, item in files.items()}
    expected.update({name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()})
    payloads["RELEASE/SHA256SUMS"] = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(expected.items())).encode()
    expected["RELEASE/SHA256SUMS"] = hashlib.sha256(payloads["RELEASE/SHA256SUMS"]).hexdigest()
    if reuse_zip:
        old_expected = {mod_id + "/" + name: item["sha256"] for name, item in files.items()}
        if inspect_archive(reuse_zip) != old_expected:
            raise ValueError("Reuse ZIP does not contain exactly the accepted runtime files")
    output.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".packaging-", suffix=".zip", dir=output.parent)
    os.close(handle)
    temporary = Path(name)
    try:
        if reuse_zip:
            shutil.copyfile(reuse_zip, temporary)
        with zipfile.ZipFile(temporary, "a" if reuse_zip else "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            if not reuse_zip:
                for name in files:
                    # Stream large PCKs rather than allocating them in memory.
                    path = source / name
                    info = zipfile.ZipInfo(mod_id + "/" + name, (2020, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | (path.stat().st_mode & 0o777)) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    with path.open("rb") as reader, archive.open(info, "w", force_zip64=True) as writer:
                        shutil.copyfileobj(reader, writer, CHUNK)
            for name, data in payloads.items():
                add_bytes(archive, name, data)
        if inspect_archive(temporary) != expected:
            raise ValueError("Final ZIP read-back does not match accepted files and release metadata")
        summary = {
            "passed": True, "archive": output.name, "bytes": temporary.stat().st_size,
            "sha256": sha256(temporary), "zip_files": len(expected), "release": metadata,
        }
        # Recheck destinations in case another process completed the same package.
        if any(path.exists() for path in (output, sidecar, checksums)):
            raise ValueError("Output appeared during packaging; existing files were preserved")
        os.rename(temporary, output)
        sidecar.write_bytes(json_bytes(summary))
        checksums.write_text(f"{summary['sha256']}  {output.name}\n", encoding="utf-8")
        return summary
    finally:
        temporary.unlink(missing_ok=True)


def verify_release(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        metadata = json.loads(archive.read("RELEASE/manifest.json"))
        notes = archive.read("RELEASE/INSTALL.md")
        sums = archive.read("RELEASE/SHA256SUMS")
    mod_id = metadata["mod_id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", mod_id):
        raise ValueError("Invalid packaged mod ID")
    expected = {mod_id + "/" + name: item["sha256"]
                for name, item in metadata["runtime_files"].items()}
    expected["RELEASE/manifest.json"] = hashlib.sha256(json_bytes(metadata)).hexdigest()
    expected["RELEASE/INSTALL.md"] = hashlib.sha256(notes).hexdigest()
    declared_sums = "".join(f"{digest}  {name}\n" for name, digest in sorted(expected.items())).encode()
    if sums != declared_sums:
        raise ValueError("Release checksum document does not match the manifest")
    expected["RELEASE/SHA256SUMS"] = hashlib.sha256(sums).hexdigest()
    if inspect_archive(path) != expected:
        raise ValueError("Release archive content/hash mismatch")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", type=Path, help="Read back an existing release ZIP only")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--mod-id")
    parser.add_argument("--platform", choices=("macos-arm64", "macos-x64", "windows-x64", "linux-x64"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--build", type=Path)
    parser.add_argument("--acceptance", type=Path)
    parser.add_argument("--install-notes", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reuse-zip", type=Path)
    args = parser.parse_args()
    try:
        if args.verify:
            metadata = verify_release(args.verify)
            print(json.dumps({"passed": True, "sha256": sha256(args.verify),
                              "runtime_files": len(metadata["runtime_files"]),
                              "version": metadata["version"]}, ensure_ascii=False))
            return
        if not all((args.mod_id, args.platform, args.install_notes, args.output)):
            parser.error("Packaging requires --mod-id, --platform, --install-notes and --output")
        project = args.project.resolve()
        source = args.source or project / "dist" / args.mod_id
        manifest = json.loads((source / (args.mod_id + ".json")).read_text(encoding="utf-8-sig"))
        summary = create_package(source, args.build or project / "dist/build.json",
                                 args.acceptance or project / "work" / ("acceptance-" + manifest["version"] + ".json"),
                                 args.mod_id, args.platform, args.install_notes, args.output, args.reuse_zip)
        print(json.dumps({key: value for key, value in summary.items() if key != "release"}, ensure_ascii=False))
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
