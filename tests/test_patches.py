import contextlib
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from repopilot.patches import main, propose_patch


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = b"value = 1\n"
        (self.root / "app.py").write_bytes(self.raw)

    def edit(self, path="app.py", content="value = 2\n", raw=None):
        return {"path": path, "content": content, "before_sha256": sha256(self.raw if raw is None else raw).hexdigest()}

    def test_exact_diff_and_unchanged_source(self):
        result = propose_patch(self.root, [self.edit()])
        self.assertEqual(result["diff"], "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n")
        self.assertFalse(result["applied"])
        self.assertEqual((self.root / "app.py").read_bytes(), self.raw)
        self.assertEqual(result, propose_patch(self.root, [self.edit()]))

    def test_rejects_unsafe_paths(self):
        for path in ("../app.py", "/app.py", "C:/app.py", "a\\app.py", "./app.py", "a//app.py", ".git/config", ".env", "secrets.py", "NUL.py", "app.py\n+++ b/evil", "missing.py", "node_modules/a.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                propose_patch(self.root, [self.edit(path)])

    def test_symlink_component_is_rejected_without_requiring_os_privilege(self):
        with patch.object(Path, "is_symlink", return_value=True), self.assertRaises(ValueError):
            propose_patch(self.root, [self.edit()])

    def test_stale_duplicate_and_schema_rejected(self):
        for edits in ([], [self.edit()] * 9, [self.edit(), self.edit()], [self.edit() | {"apply": True}], [self.edit() | {"before_sha256": "0" * 64}], [self.edit() | {"content": None}]):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                propose_patch(self.root, edits)

    def test_binary_encoding_and_size_guards(self):
        for raw in (b"\x00binary", b"\xff", b"a" * (128 * 1024 + 1)):
            (self.root / "app.py").write_bytes(raw)
            with self.assertRaises(ValueError):
                propose_patch(self.root, [self.edit(raw=raw)])
        (self.root / "app.py").write_bytes(self.raw)
        for content in ("\x00", "\x1b[31m", "a\rb", "a" * (128 * 1024 + 1), "汉" * 50000):
            with self.assertRaises(ValueError):
                propose_patch(self.root, [self.edit(content=content)])
        with patch("repopilot.patches.MAX_DIFF_BYTES", 10), self.assertRaises(ValueError):
            propose_patch(self.root, [self.edit()])

    def test_noop_empty_and_missing_newline(self):
        self.assertEqual(propose_patch(self.root, [self.edit(content=self.raw.decode())])["diff"], "")
        result = propose_patch(self.root, [self.edit(content="value = 2")])
        self.assertTrue(result["diff"].endswith("+value = 2\n\\ No newline at end of file\n"))
        self.assertIn("@@ -1 +0,0 @@", propose_patch(self.root, [self.edit(content="")])["diff"])
        (self.root / "app.py").write_bytes(b"")
        self.assertIn("@@ -0,0 +1 @@", propose_patch(self.root, [self.edit(raw=b"")])["diff"])

    def test_cli_json_and_failure_does_not_emit_partial_diff(self):
        request = self.root / "edits.json"
        request.write_text(json.dumps([self.edit()]), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main([str(self.root), "--edits", str(request), "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "diff_only")
        request.write_text(json.dumps([self.edit(), self.edit("../bad.py")]), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main([str(self.root), "--edits", str(request)])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertEqual((self.root / "app.py").read_bytes(), self.raw)


if __name__ == "__main__":
    unittest.main()
