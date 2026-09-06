import json
import unittest

from repopilot.chunks import CodeChunk
from repopilot.qa import answer_chunks


def chunk(path, symbol, text, start=10):
    return CodeChunk(path, "Python", start, start + 2, text, symbol, "function")


class RepositoryQuestionAnsweringTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            chunk("files.py", "read_file", "def read_file(path): Read UTF-8 file contents."),
            chunk("symbols.py", "parse_syntax", "def parse_syntax(source): Parse Python syntax with AST."),
            chunk("chunks.py", "split_chunks", "def split_chunks(source): Split code with overlap."),
            chunk("retrieval.py", "rank_results", "def rank_results(query): Rank BM25 search results."),
            chunk("output.py", "serialize_json", "def serialize_json(value): Serialize JSON output."),
        ]

    def test_five_grounded_questions_have_expected_primary_citations(self):
        cases = [
            ("How are files read?", "files.py"),
            ("Where is Python syntax parsed?", "symbols.py"),
            ("How are code chunks split?", "chunks.py"),
            ("Which function ranks BM25 results?", "retrieval.py"),
            ("Where is JSON output serialized?", "output.py"),
        ]
        for question, path in cases:
            with self.subTest(question=question):
                result = answer_chunks(question, self.chunks)
                self.assertTrue(result.supported)
                self.assertEqual(result.citations[0].path, path)
                self.assertIn(f"{path}:L10-L12", result.answer)

    def test_unsupported_question_is_refused_without_citations(self):
        result = answer_chunks("What database handles customer invoices?", self.chunks)
        self.assertFalse(result.supported)
        self.assertEqual(result.citations, ())
        self.assertIn("cannot answer", result.answer)

    def test_answer_is_json_serializable_and_excerpt_is_bounded(self):
        result = answer_chunks("files read", self.chunks)
        encoded = json.dumps(result.to_dict())
        self.assertIn('"location": "files.py:L10-L12"', encoded)
        self.assertLessEqual(len(result.citations[0].excerpt), 220)


if __name__ == "__main__":
    unittest.main()
