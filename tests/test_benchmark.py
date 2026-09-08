import json
from pathlib import Path
import tempfile
import unittest

from repopilot.benchmark import evaluate, load_cases
from repopilot.chunks import CodeChunk


class BenchmarkTests(unittest.TestCase):
    def test_metrics_have_independent_denominators(self):
        chunks = [CodeChunk("a.py", "Python", 1, 2, "def alpha():\n    return 1", "alpha"),
                  CodeChunk("b.py", "Python", 1, 2, "def beta():\n    return 2", "beta")]
        cases = [{"id":"hit", "question":"alpha", "answerable":True, "path":"a.py", "symbol":"alpha"},
                 {"id":"miss", "question":"unknown", "answerable":True, "path":"b.py", "symbol":"beta"},
                 {"id":"refuse", "question":"invoices", "answerable":False},
                 {"id":"false-positive", "question":"alpha invoices", "answerable":False}]
        report = evaluate(chunks, cases, 1)
        self.assertEqual(report["metrics"], {"hit_at_k":0.5, "primary_citation_accuracy":0.5,
                         "mrr_at_k":0.5, "citation_source_validity":1.0, "refusal_accuracy":0.5})
        self.assertEqual(report, evaluate(chunks, cases, 1))

    def test_missing_labels_and_invalid_k_fail(self):
        with self.assertRaises(ValueError):
            evaluate([], [{"id":"stale", "question":"x", "answerable":True, "path":"x.py", "symbol":"x"}])
        with self.assertRaises(ValueError):
            evaluate([], [], 0)
        self.assertIsNone(evaluate([], [{"id":"n", "question":"nothing", "answerable":False}])["metrics"]["citation_source_validity"])

    def test_dataset_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            case = {"id":"one", "question":"test", "answerable":False}
            path.write_text(json.dumps(case), encoding="utf-8")
            self.assertEqual(load_cases(path), [case])
            for text in ["", json.dumps(case) + "\n" + json.dumps(case), '{"id":"bad"}']:
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_cases(path)


if __name__ == "__main__":
    unittest.main()
