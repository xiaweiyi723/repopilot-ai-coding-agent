# Day 7 benchmark — 9 September 2026

## Reproduce

From the repository root, install with `python -m pip install -e .`, then run:

```bash
python -m repopilot.benchmark src/repopilot docs/qa-benchmark-v1.jsonl --top-k 3
```

The command prints full per-case JSON results and corpus/dataset fingerprints.
This run evaluated 53 chunks from the Day 7 source tree, based on Day 6 commit
0258131 plus benchmark.py. Labels and this report reside outside the source root.
No network or model is used. New source changes can alter ranking; compare fingerprints.

## Results

| Metric | Result | Denominator and meaning |
|---|---:|---|
| Hit@3 | 70% (7/10) | Answerable questions with the labelled path AND symbol in the first three Q&A citations |
| Primary citation accuracy | 50% (5/10) | Answerable questions with the labelled path AND symbol ranked first |
| MRR@3 | 0.60 | Mean reciprocal rank over 10 answerable questions; misses score zero |
| Citation source validity | 100% (27/27) | Returned locations and excerpts match indexed source chunks |
| Refusal accuracy | 66.7% (2/3) | Unanswerable questions correctly refused |

Source validity does not establish relevance or answer correctness. The payment
question returns real source excerpts that do not answer the question.

| Case ID | Expected symbol | Rank within top 3 / outcome |
|---|---|---|
| scan | scan_repository | miss; metadata classes outrank the implementation |
| parse | extract_python_module | 1 |
| chunk | chunk_source | 1 |
| window | _line_windows | 2 |
| rank | BM25Index | 1 |
| token | tokenize | 1 |
| schema | tool_schemas | 2 |
| excerpt | _excerpt | 1 |
| synonym | scan_repository | incorrectly refused |
| chinese | extract_python_module | incorrectly refused |
| absent | no answer | correctly refused |
| overlap-negative | no answer | incorrectly supported due to generic word overlap |
| empty-terms | no answer | correctly refused |

## Interpretation and limits

These 13 author-labelled development cases are a small regression baseline,
not a held-out benchmark or a claim of general AI accuracy. Each positive case
has one selected path/symbol; other helpful chunks are not credited. The Q&A
retriever removes stopwords, so these scores specifically measure the `ask`
pipeline rather than the raw `search` command. No answer semantics are graded.

Lexical matching misses synonyms and Chinese phrasing; any positive lexical
score can cause false support on unanswerable questions. Future work should
evaluate identifier weighting, semantic retrieval, and an evidence relevance
threshold against additional held-out cases. The baseline was not tuned to
remove these failures.

Validation: 26 unit tests, 25 passed, one Windows symlink privilege skip.
Tests check metric denominators, known hits/misses, false support, dataset
validation, stale labels, undefined metrics, and deterministic output.

Corpus SHA-256: e7b0df773c1a2e45333159c63445526f01503c14b39a96f8d192a78597491755

Dataset byte SHA-256 at evaluation: 33d2d1e1a9ed2ce602b34f9f11934a4977a70be99a8f3c80799606a1df06abfc
(Dataset byte hashes may differ after Git newline conversion.)
