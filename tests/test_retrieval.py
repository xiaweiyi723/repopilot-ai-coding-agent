import unittest
from repopilot.chunks import CodeChunk
from repopilot.retrieval import BM25Index, tokenize


class RetrievalTests(unittest.TestCase):
    def test_five_queries_find_relevant_code(self):
        cases = [
            ("read file", "read_file", "Read file contents from disk"),
            ("parse syntax", "parse_syntax", "Parse syntax using AST"),
            ("split chunks", "split_chunks", "Split chunks with overlap"),
            ("rank results", "rank_results", "Rank results by relevance"),
            ("serialize json", "serialize_json", "Serialize JSON output"),
        ]
        index = BM25Index(CodeChunk(f"{name}.py", "Python", 1, 2, body, name)
                          for _, name, body in cases)
        for query, name, _ in cases:
            with self.subTest(query=query):
                self.assertEqual(index.search(query, 3)[0].chunk.symbol, name)

    def test_unknown_empty_and_invalid_queries(self):
        index = BM25Index([CodeChunk("a.py", "Python", 1, 1, "hello")])
        self.assertEqual(index.search(""), ())
        self.assertEqual(index.search("zebra"), ())
        self.assertEqual(BM25Index([]).search("hello"), ())
        with self.assertRaises(ValueError):
            index.search("hello", 0)

    def test_ties_and_identifier_splitting(self):
        self.assertEqual(tokenize("readFile read_file"), ["read", "file", "read", "file"])
        chunks = [CodeChunk(p, "Python", 1, 1, "same") for p in ["b.py", "a.py"]]
        self.assertEqual([h.chunk.path for h in BM25Index(chunks).search("same")], ["a.py", "b.py"])
