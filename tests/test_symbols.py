import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repopilot.symbols import build_python_symbol_map, extract_python_module


SAMPLE_SOURCE = """\
import os
from .helpers import load_data as load

class Repository:
    def scan(self, path: str, *, strict: bool = False) -> list[str]:
        return []

    async def refresh(self) -> None:
        return None

def create(name: str = "demo") -> Repository:
    return Repository()
"""


class SymbolExtractionTests(unittest.TestCase):
    def test_extracts_classes_callables_imports_and_signatures(self):
        module = extract_python_module("sample.py", SAMPLE_SOURCE)

        self.assertIsNone(module.parse_error)
        self.assertEqual(
            [(symbol.qualified_name, symbol.kind) for symbol in module.symbols],
            [
                ("Repository", "class"),
                ("Repository.scan", "method"),
                ("Repository.refresh", "async_method"),
                ("create", "function"),
            ],
        )
        self.assertEqual(
            module.symbols[1].signature,
            "def scan(self, path: str, *, strict: bool = False) -> list[str]",
        )
        self.assertEqual(module.imports[0].module, "")
        self.assertEqual(module.imports[0].names, ("os",))
        self.assertEqual(module.imports[1].module, ".helpers")
        self.assertEqual(module.imports[1].names, ("load_data",))

    def test_reports_syntax_error_without_executing_source(self):
        module = extract_python_module("broken.py", "def broken(:\n    pass\n")

        self.assertEqual(module.symbols, ())
        self.assertIn("line 1", module.parse_error or "")

    def test_build_map_is_stable_and_respects_scanner_ignores(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "b.py").write_text("def second():\n    pass\n", encoding="utf-8")
            (root / "a.py").write_text("def first():\n    pass\n", encoding="utf-8")
            (root / ".venv").mkdir()
            (root / ".venv" / "ignored.py").write_text(
                "def ignored():\n    pass\n", encoding="utf-8"
            )

            modules = build_python_symbol_map(root)

        self.assertEqual([module.path for module in modules], ["a.py", "b.py"])
        self.assertEqual(modules[0].symbols[0].name, "first")

    def test_module_map_is_json_serializable(self):
        module = extract_python_module("sample.py", SAMPLE_SOURCE)

        encoded = json.dumps(module.to_dict())

        self.assertIn("Repository.scan", encoded)


if __name__ == "__main__":
    unittest.main()

