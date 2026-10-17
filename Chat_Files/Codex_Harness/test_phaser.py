import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from Codex_Harness import phaser


class PhaserHelperTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=phaser.BASE)
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name) / "project"
        self.project.mkdir()
        self.cache = Path(self.directory.name) / "cache"

    def test_provision_checks_archive_integrity_and_extracts_only_runtime_and_license(self):
        contents = {"package/package.json": json.dumps({"version": phaser.VERSION}).encode(),
                    "package/dist/phaser.min.js": b"test runtime", "package/LICENSE.md": b"MIT license",
                    "../escape": b"must not be extracted"}
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as package:
            for name, content in contents.items():
                member = tarfile.TarInfo(name)
                member.size = len(content)
                package.addfile(member, io.BytesIO(content))
        archive = stream.getvalue()
        integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
        metadata = {"version": phaser.VERSION, "dist": {
            "tarball": f"https://registry.npmjs.org/phaser/-/phaser-{phaser.VERSION}.tgz",
            "integrity": integrity}}
        with patch.object(phaser, "CACHE", self.cache), patch.object(phaser, "urlopen", side_effect=[
                io.BytesIO(json.dumps(metadata).encode()), io.BytesIO(archive)]):
            self.assertEqual(phaser.provision(), self.cache)
        self.assertEqual({path.name for path in self.cache.iterdir()}, set(phaser.FILES))
        self.assertEqual((self.cache / "phaser.min.js").read_bytes(), b"test runtime")
        self.assertFalse((Path(self.directory.name) / "escape").exists())

    def test_corrupt_download_is_rejected_before_files_are_written(self):
        metadata = {"version": phaser.VERSION, "dist": {
            "tarball": f"https://registry.npmjs.org/phaser/-/phaser-{phaser.VERSION}.tgz",
            "integrity": "sha512-invalid"}}
        with patch.object(phaser, "CACHE", self.cache), patch.object(phaser, "urlopen", side_effect=[
                io.BytesIO(json.dumps(metadata).encode()), io.BytesIO(b"corrupt archive")]):
            with self.assertRaisesRegex(ValueError, "integrity"):
                phaser.provision()
        self.assertFalse(self.cache.exists())

    def test_copy_is_offline_idempotent_and_preserves_different_existing_files(self):
        self.cache.mkdir()
        for name in phaser.FILES:
            (self.cache / name).write_bytes(name.encode())
        with patch.object(phaser, "CACHE", self.cache), patch.object(phaser, "urlopen") as download:
            result = phaser.install(self.project)
            self.assertEqual(phaser.install(self.project), result)
            script = self.project / result["script"]
            script.write_bytes(b"existing customized runtime")
            with self.assertRaises(FileExistsError):
                phaser.install(self.project)
            self.assertEqual(script.read_bytes(), b"existing customized runtime")
        download.assert_not_called()
        self.assertTrue((self.project / result["license"]).is_file())

    def test_missing_cache_and_outside_projects_are_rejected(self):
        with patch.object(phaser, "CACHE", self.cache):
            with self.assertRaises(FileNotFoundError):
                phaser.install(self.project)
            with self.assertRaises(ValueError):
                phaser.install(phaser.BASE.parent)


if __name__ == "__main__":
    unittest.main()
