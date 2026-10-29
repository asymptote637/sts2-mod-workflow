#!/usr/bin/env python3
"""Prepare a new official ModUploader workspace without contacting Steam."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from package_mod import CHUNK, json_bytes, safe_relative, sha256, verify_release


def prepare(package: Path, workspace: Path, preview: Path, dependency_map: dict[str, int],
            visibility: str = "private", title: str | None = None,
            description: str | None = None) -> dict:
    if workspace.exists():
        raise ValueError("Workspace exists; preserve its mod_id.txt and update content deliberately")
    if visibility not in ("private", "public", "unlisted", "friends_only"):
        raise ValueError("Invalid Workshop visibility")
    if not preview.is_file() or not 0 < preview.stat().st_size < 1_000_000:
        raise ValueError("Preview image must be below 1 MB")
    with preview.open("rb") as stream:
        if stream.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Preview must be a PNG file")
    metadata = verify_release(package)
    required = {item["id"] for item in metadata["dependencies"]}
    if set(dependency_map) != required or any(not isinstance(value, int) or value <= 0
                                              for value in dependency_map.values()):
        raise ValueError("Map every manifest dependency ID to its numeric Steam Workshop item ID")
    workspace = workspace.absolute()
    workspace.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".workshop-", dir=workspace.parent))
    try:
        with zipfile.ZipFile(package) as archive:
            mod_id = metadata["mod_id"]
            manifest = json.loads(archive.read(mod_id + "/" + mod_id + ".json"))
            for name, item in metadata["runtime_files"].items():
                target = temporary / "content" / safe_relative(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                info = archive.getinfo(mod_id + "/" + name)
                with archive.open(info) as reader, target.open("wb") as writer:
                    shutil.copyfileobj(reader, writer, CHUNK)
                target.chmod((info.external_attr >> 16) & 0o777 or 0o644)
                if sha256(target) != item["sha256"]:
                    raise ValueError("Workspace read-back mismatch: " + name)
            (temporary / "README.md").write_bytes(archive.read("RELEASE/INSTALL.md"))
        shutil.copy2(preview, temporary / "image.png")
        config = {
            "title": title or (manifest.get("name", mod_id) + " [" + metadata["platform"] + "]"),
            "description": description or manifest.get("description", ""),
            "visibility": visibility,
            "changeNote": "Version " + metadata["version"],
            "tags": [],
            "dependencies": [dependency_map[key] for key in sorted(required)],
            "contentDescriptors": [],
        }
        (temporary / "workshop.json").write_bytes(json_bytes(config))
        record = {
            "prepared": True, "uploaded": False, "mod_id": mod_id,
            "version": metadata["version"], "platform": metadata["platform"],
            "package_sha256": sha256(package), "visibility": visibility,
            "runtime_files": metadata["runtime_files"],
            "workshop_dependencies": config["dependencies"],
        }
        (temporary / "PREPARED.json").write_bytes(json_bytes(record))
        if workspace.exists():
            raise ValueError("Workspace appeared during preparation; existing directory preserved")
        os.rename(temporary, workspace)
        return record
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--preview", required=True, type=Path)
    parser.add_argument("--dependency", action="append", default=[], metavar="MOD_ID=WORKSHOP_ID")
    parser.add_argument("--visibility", choices=("private", "public", "unlisted", "friends_only"), default="private")
    parser.add_argument("--title")
    parser.add_argument("--description-file", type=Path)
    args = parser.parse_args()
    try:
        mapping = {}
        for item in args.dependency:
            key, value = item.split("=", 1)
            if key in mapping:
                raise ValueError("Duplicate dependency mapping: " + key)
            mapping[key] = int(value)
        description = args.description_file.read_text(encoding="utf-8") if args.description_file else None
        record = prepare(args.package, args.workspace, args.preview, mapping,
                         args.visibility, args.title, description)
        print(json.dumps({key: value for key, value in record.items() if key != "runtime_files"}, ensure_ascii=False))
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
