#!/usr/bin/env python3
"""Exercise release integrity and Workshop preparation without contacting Steam."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_mod import create_package, sha256, verify_release
from prepare_workshop import prepare


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "dist/TestMod"
        self.source.mkdir(parents=True)
        manifest = {"id": "TestMod", "name": "测试角色", "version": "1.2.3",
                    "has_pck": True, "has_dll": True, "affects_gameplay": False,
                    "dependencies": [{"id": "Library", "min_version": "1.0"}]}
        (self.source / "TestMod.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.source / "TestMod.dll").write_bytes(b"fake managed assembly")
        (self.source / "TestMod.pck").write_bytes(bytes(range(256)) * 100)
        self.files = {p.name: sha256(p) for p in self.source.iterdir()}
        self.build = self.root / "build.json"
        self.build.write_text(json.dumps({"files": self.files}))
        self.acceptance = self.root / "acceptance.json"
        self.acceptance.write_text(json.dumps({"version": "1.2.3", "passed": True,
                                              "artifacts": self.files, "checks": {"engine": True}}))
        self.notes = self.root / "INSTALL.md"
        self.notes.write_text("Install to the game's mods directory.\n")
        self.output = self.root / "release.zip"
        self.preview = self.root / "image.png"
        import base64
        self.preview.write_bytes(base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aN8sAAAAASUVORK5CYII="))

    def package(self, **kwargs):
        return create_package(self.source, self.build, self.acceptance, "TestMod",
                              "macos-arm64", self.notes, self.output, **kwargs)

    def test_allowlist_omits_stale_files_and_readback_matches(self):
        (self.source / "TestMod 2.pck").write_bytes(b"old artifact")
        (self.source / "settings.save").write_text("private data")
        result = self.package()
        self.assertEqual(result["sha256"], sha256(self.output))
        metadata = verify_release(self.output)
        self.assertEqual(set(metadata["runtime_files"]), set(self.files))
        self.assertEqual(metadata["excluded_unlisted_files"], ["TestMod 2.pck", "settings.save"])
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(len(archive.namelist()), 6)
            self.assertFalse(any("settings.save" in name for name in archive.namelist()))

    def test_changed_source_is_rejected_before_output(self):
        (self.source / "TestMod.pck").write_bytes(b"changed after QA")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.package()
        self.assertFalse(self.output.exists())

    def test_stale_acceptance_is_rejected(self):
        report = json.loads(self.acceptance.read_text())
        report["artifacts"]["TestMod.dll"] = "0" * 64
        self.acceptance.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.package()

    def test_failed_acceptance_is_rejected(self):
        report = json.loads(self.acceptance.read_text())
        report["passed"] = False
        self.acceptance.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, "not passed"):
            self.package()

    def test_unsafe_file_path_is_rejected(self):
        self.files["../secret"] = "0" * 64
        self.build.write_text(json.dumps({"files": self.files}))
        self.acceptance.write_text(json.dumps({"version": "1.2.3", "passed": True, "artifacts": self.files}))
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.package()

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b"existing release")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.package()
        self.assertEqual(self.output.read_bytes(), b"existing release")

    def test_reuse_zip_checks_payload(self):
        original = self.root / "original.zip"
        with zipfile.ZipFile(original, "w") as archive:
            for path in self.source.iterdir():
                archive.write(path, "TestMod/" + path.name)
        result = self.package(reuse_zip=original)
        self.assertTrue(result["passed"])
        self.assertEqual(verify_release(self.output)["version"], "1.2.3")

    def test_duplicate_reuse_zip_is_rejected(self):
        original = self.root / "duplicate.zip"
        import warnings
        with warnings.catch_warnings(), zipfile.ZipFile(original, "w") as archive:
            warnings.simplefilter("ignore", UserWarning)
            archive.writestr("TestMod/TestMod.dll", b"a")
            archive.writestr("TestMod/TestMod.dll", b"b")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.package(reuse_zip=original)

    def test_tampered_release_fails_verification(self):
        self.package()
        changed = self.root / "changed.zip"
        with zipfile.ZipFile(self.output) as source, zipfile.ZipFile(changed, "w") as target:
            for entry in source.infolist():
                data = b"tampered" if entry.filename.endswith("TestMod.pck") else source.read(entry)
                target.writestr(entry, data)
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verify_release(changed)

    def test_workshop_layout_and_numeric_dependency(self):
        self.package()
        workspace = self.root / "workshop"
        result = prepare(self.output, workspace, self.preview, {"Library": 123456})
        self.assertFalse(result["uploaded"])
        self.assertFalse((workspace / "mod_id.txt").exists())
        self.assertEqual(json.loads((workspace / "workshop.json").read_text())["dependencies"], [123456])
        self.assertEqual({p.name for p in (workspace / "content").iterdir()}, set(self.files))
        self.assertEqual({p.name: sha256(p) for p in (workspace / "content").iterdir()}, self.files)

    def test_missing_dependency_mapping_does_not_create_workspace(self):
        self.package()
        workspace = self.root / "workshop"
        with self.assertRaisesRegex(ValueError, "Map every"):
            prepare(self.output, workspace, self.preview, {})
        self.assertFalse(workspace.exists())

    def test_existing_workshop_item_id_is_preserved(self):
        workspace = self.root / "workshop"
        workspace.mkdir()
        item = workspace / "mod_id.txt"
        item.write_text("123456")
        with self.assertRaisesRegex(ValueError, "Workspace exists"):
            prepare(self.output, workspace, self.preview, {})
        self.assertEqual(item.read_text(), "123456")


if __name__ == "__main__":
    unittest.main(verbosity=2)
