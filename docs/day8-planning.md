# Day 8 — Issue-to-change planning baseline

## Problem and design

A coding assistant should show the evidence and uncertainty behind a proposed change before editing anything. `planner.py` reuses the scanner, code chunks and lexical Q&A retrieval to return a JSON planning checklist. Candidate paths only come from scanned chunks. It groups citations by file, supplies review steps, risks, test suggestions and clarification questions. Issue text is bounded to 8,000 characters and top-k to 1–10. It does not evaluate code, invoke shell commands, write target files, or call an external model.

This is a rule-based baseline, not semantic planning or an autonomous agent. Steps are intentionally review checklists rather than fabricated implementation details. A lexical hit does not establish that a feature is missing or that every candidate needs editing.

## Three example GitHub-style issues

These are synthetic example issue texts, not real reported GitHub issues. All commands were run against `src/repopilot` with `--top-k 2`. Paths below are relative to that root. Each result was `needs_review`, with `tests.executed=false`. Full JSON includes excerpts, risks and questions.

### 1. Report skipped files

```bash
python -m repopilot.planner src/repopilot --issue "scan_repository should report skipped files" --top-k 2
```

Returned candidates: `scanner.py:L118-L167` (`scan_repository`) and `benchmark.py:L70-L88` (`main`). Generated steps ask for acceptance criteria, inspection of both cited candidates, a failing regression case, reviewed changes and manual verification.

Human review: the scanner is relevant; the benchmark CLI is a secondary lexical match, not an established edit target. Before implementation, decide whether to expose counts or reasons and how to avoid disclosing secret filenames. Suggested acceptance cases: ignored directories, oversized files and binary input. These issue-specific suggestions are human-authored commentary, not planner output.

### 2. Preserve deterministic retrieval ties

```bash
python -m repopilot.planner src/repopilot --issue "BM25Index.search should preserve deterministic ties" --top-k 2
```

Returned candidates: `retrieval.py:L26-L55` (`BM25Index`) and `cli.py:L16-L49` (`_build_parser`). Generated steps request inspection of those locations and a regression-first review workflow.

Human review: the retrieved class already advertises deterministic ties. Confirm whether there is a reproducible bug before changing it; the planner cannot distinguish an existing feature from a new requirement. Suggested checks: repeated equal-score searches and stable ordering. The CLI candidate may require no changes.

### 3. Refuse unsupported repository questions

```bash
python -m repopilot.planner src/repopilot --issue "answer_chunks should refuse unsupported questions" --top-k 2
```

Returned one candidate file, `qa.py`, with evidence at `L45-L57` (`answer_chunks`) and `L59-L60` (`answer_repository`). Steps group both citations under one file review.

Human review: refusal already exists for no matching terms, but Day 7 found false support from generic word overlap. A useful future change would be evaluated against that negative case while preserving positive retrieval cases. Do not assume all low-ranking results should be refused without measuring the trade-off.

## Shared output and reproduction notes

All plans include risks for lexical mismatch, untrusted content and stale repository snapshots; questions ask for expected input/output and compatibility constraints. Because these examples index only the source directory, their existing-test-file lists are empty. Run against `.` to discover test files as well (rankings may change). File listings are bounded to 20 and include a truncation flag; they do not prove coverage.

## Validation

`python -m unittest discover -s tests -v`: 30 tests run, 29 passed, one Windows symlink-privilege skip. Four new tests cover deterministic cited plans, unchanged target files, missing-context behavior, input limits, JSON CLI output and issue instructions remaining inert data. The three commands above were also exercised. No live-model quality claim is made.

## Next risk

Generic planning steps cannot replace engineering judgment. Exact edits, semantic relevance, dependency impact and downstream prompt-injection defenses remain outside this baseline. Day 9 will add guarded diff-only proposals; today creates no patch and runs no generated command.
