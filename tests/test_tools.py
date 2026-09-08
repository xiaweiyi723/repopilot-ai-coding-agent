import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from repopilot.tools import RepositoryTools, main, tool_schemas


class RepositoryToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "pkg").mkdir()
        (self.root / "pkg" / "service.py").write_text(
            "import json\nfrom .helpers import load\nclass Service:\n"
            "    def run(self):\n        return load()\n", encoding="utf-8")
        (self.root / "broken.py").write_text("def broken(:", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=private", encoding="utf-8")
        (self.root / "README.md").write_text("demo", encoding="utf-8")
        self.tools = RepositoryTools(self.root)

    def test_search_is_deterministic_bounded_and_filters_secrets(self):
        result = self.tools.call("file_search", {"pattern": "*.py", "limit": 1})
        self.assertEqual(result["total"], 2)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["results"][0]["path"], "broken.py")
        self.assertEqual(result, self.tools.call("file_search", {"pattern": "*.py", "limit": 1}))
        self.assertEqual(self.tools.call("file_search", {"pattern": ".env"})["results"], [])

    def test_symbol_lookup_has_exact_location_and_parse_errors(self):
        result = self.tools.call("symbol_lookup", {"name": "Service.run"})
        self.assertEqual(len(result["results"]), 1)
        symbol = result["results"][0]
        self.assertEqual((symbol["path"], symbol["line_start"], symbol["line_end"]),
                         ("pkg/service.py", 4, 5))
        self.assertEqual(result["errors"][0]["path"], "broken.py")
        self.assertEqual(self.tools.call("symbol_lookup", {"name": "missing"})["results"], [])

    def test_dependencies_preserve_relative_imports_and_lines(self):
        rows = self.tools.call("dependency_lookup", {"path": "pkg/service.py"})["results"]
        self.assertEqual([(r["module"], r["names"], r["line"]) for r in rows],
                         [("", ("json",), 1), (".helpers", ("load",), 2)])
        result = self.tools.call("dependency_lookup", {"path": "broken.py"})
        self.assertEqual(result["results"], [])
        self.assertTrue(result["errors"])

    def test_invalid_calls_and_paths_are_rejected(self):
        cases = [("shell", {}), ("file_search", []), ("file_search", {}),
                 ("file_search", {"pattern": "*", "root": "/"}),
                 ("file_search", {"pattern": "*", "limit": True}),
                 ("file_search", {"pattern": "*", "limit": 101})]
        cases += [("dependency_lookup", {"path": p}) for p in
                  ["../outside.py", "/outside.py", "C:\\outside.py", ".env", "missing.py", "README.md"]]
        for name, args in cases:
            with self.subTest(name=name, args=args), self.assertRaises(ValueError):
                self.tools.call(name, args)

    def test_schemas_cli_and_read_only_behavior(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(len(tool_schemas()), 3)
        self.assertTrue(all(not s["parameters"]["additionalProperties"] for s in tool_schemas()))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main([str(self.root), "--tool", "file_search", "--arguments", '{"pattern":"*.py"}'])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["total"], 2)
        self.tools.call("symbol_lookup", {"name": "Service"})
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
