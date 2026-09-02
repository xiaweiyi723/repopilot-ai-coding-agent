from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from repopilot.scanner import scan_repository


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = TemporaryDirectory()
        self.root = Path(self.temp_directory.name)

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_scan_collects_metadata_and_stable_order(self):
        (self.root / "z.py").write_text("print('hello')\n", encoding="utf-8")
        (self.root / "a.md").write_text("# Notes\nsecond line\n", encoding="utf-8")

        inventory = scan_repository(self.root)

        self.assertEqual([file.path for file in inventory.files], ["a.md", "z.py"])
        self.assertEqual(inventory.total_lines, 3)
        self.assertEqual(inventory.languages, {"Markdown": 1, "Python": 1})
        self.assertEqual(
            inventory.files[0].sha256,
            sha256((self.root / "a.md").read_bytes()).hexdigest(),
        )

    def test_scan_skips_ignored_unsupported_large_and_binary_files(self):
        (self.root / ".git").mkdir()
        (self.root / ".git" / "secret.py").write_text(
            "TOKEN='do-not-read'", encoding="utf-8"
        )
        (self.root / "notes.txt").write_text("unsupported", encoding="utf-8")
        (self.root / "large.py").write_text("x" * 20, encoding="utf-8")
        (self.root / "binary.py").write_bytes(b"\xff\xfe")
        (self.root / "kept.py").write_text("value = 1\n", encoding="utf-8")

        inventory = scan_repository(self.root, max_file_bytes=15)

        self.assertEqual([file.path for file in inventory.files], ["kept.py"])

    def test_scan_does_not_follow_symlink(self):
        target = self.root / "target.py"
        target.write_text("value = 1\n", encoding="utf-8")
        link = self.root / "linked.py"
        try:
            link.symlink_to(target)
        except OSError as error:
            self.skipTest(f"Symlink creation is unavailable: {error}")

        inventory = scan_repository(self.root)

        self.assertEqual([file.path for file in inventory.files], ["target.py"])

    def test_scan_rejects_non_directory(self):
        file_path = self.root / "single.py"
        file_path.write_text("value = 1\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "not a directory"):
            scan_repository(file_path)


if __name__ == "__main__":
    unittest.main()
