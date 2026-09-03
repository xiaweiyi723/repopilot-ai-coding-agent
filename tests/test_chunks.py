import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from repopilot.chunks import chunk_repository, chunk_source


SOURCE = """\
import os

VALUE = 1

def first():
    return VALUE

def second(name: str):
    message = f"hello {name}"
    return message
"""


class CodeChunkTests(unittest.TestCase):
    def test_uses_python_symbol_boundaries_and_metadata(self):
        chunks = chunk_source("example.py", SOURCE, max_lines=20, overlap_lines=2)

        self.assertEqual(
            [(chunk.symbol, chunk.line_start, chunk.line_end) for chunk in chunks],
            [(None, 1, 4), ("first", 5, 6), ("second", 8, 10)],
        )
        self.assertEqual(chunks[-1].symbol_kind, "function")
        self.assertEqual(chunks[-1].path, "example.py")

    def test_overlaps_only_when_a_segment_exceeds_the_limit(self):
        source = "\n".join(f"line_{number}" for number in range(1, 11))

        chunks = chunk_source(
            "notes.txt", source, language="Text", max_lines=4, overlap_lines=1
        )

        self.assertEqual(
            [(chunk.line_start, chunk.line_end) for chunk in chunks],
            [(1, 4), (4, 7), (7, 10)],
        )
        self.assertTrue(chunks[0].content.endswith("line_4"))
        self.assertTrue(chunks[1].content.startswith("line_4"))

    def test_rejects_invalid_window_settings(self):
        with self.assertRaises(ValueError):
            chunk_source("a.py", "x = 1", max_lines=4, overlap_lines=4)

    def test_repository_chunks_are_stable_and_json_serializable(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "b.py").write_text("def second():\n    pass\n", encoding="utf-8")
            (root / "a.py").write_text("def first():\n    pass\n", encoding="utf-8")

            chunks = chunk_repository(root)

        self.assertEqual([chunk.path for chunk in chunks], ["a.py", "b.py"])
        self.assertIn('"symbol": "first"', json.dumps(chunks[0].to_dict()))


if __name__ == "__main__":
    unittest.main()
