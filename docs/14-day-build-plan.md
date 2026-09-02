# 14-day public build plan

Dates: 2 September 2026 to 15 September 2026.

The goal is not to manufacture contribution activity. Each daily update must
contain a runnable change, evidence, and a focused explanation of the design
trade-off. If a feature is incomplete, document it honestly instead of using
an empty commit.

| Day | Date | Deliverable | Verification evidence | Suggested commit |
|---:|---|---|---|---|
| 1 | Sep 2 | Project scope, Python package, repository scanner, JSON inventory | Scanner unit tests and sample output | `feat: add safe repository scanner` |
| 2 | Sep 3 | Python AST symbol extractor for classes, functions, imports, and signatures | Fixture repo plus symbol snapshot tests | `feat: build Python symbol map` |
| 3 | Sep 4 | Code-aware chunking with file, symbol, and line-range metadata | Boundary and overlap tests | `feat: add symbol-aware code chunks` |
| 4 | Sep 5 | Local BM25/TF-IDF retrieval baseline; optional embedding adapter interface | Top-k retrieval examples on five questions | `feat: add local code retrieval baseline` |
| 5 | Sep 6 | Repo question answering with filename and line citations | Five grounded Q&A cases; unsupported answer refusal | `feat: answer repository questions with citations` |
| 6 | Sep 7 | Read-only tools: file search, symbol lookup, dependency lookup | Tool schemas and deterministic tool tests | `feat: expose read-only repository tools` |
| 7 | Sep 8 | Evaluation dataset and first benchmark for retrieval and citation accuracy | Versioned JSONL cases and metrics report | `test: add repository QA benchmark` |
| 8 | Sep 9 | Issue-to-change planning agent that outputs files, steps, risks, and tests | Plans for three example GitHub issues | `feat: generate evidence-backed change plans` |
| 9 | Sep 10 | Unified-diff proposal generator with path validation and diff-only default | Reject traversal/binary/oversized edits | `feat: generate guarded patch proposals` |
| 10 | Sep 11 | Sandboxed verification adapter for allowlisted lint/test commands | Timeout, failure, and redaction tests | `feat: verify proposals with safe test runner` |
| 11 | Sep 12 | FastAPI service and small web UI for scan, ask, plan, and inspect-diff flows | API tests and a short demo GIF | `feat: add interactive coding-agent demo` |
| 12 | Sep 13 | Prompt-injection defenses, secret redaction, structured logs, error handling | Adversarial cases and no-secret log test | `security: harden agent inputs and logs` |
| 13 | Sep 14 | GitHub Actions, Dockerfile, architecture decision records, usage tutorial | Green CI and clean-container run | `ci: add reproducible quality pipeline` |
| 14 | Sep 15 | Final benchmark, limitations, demo video, release notes, v0.1.0 tag | Results table and reproducible release checklist | `release: publish RepoPilot v0.1.0` |

## Daily update format

Use the same four-part structure in every commit or project note:

1. **Problem:** one sentence describing what an AI coding agent needs.
2. **Implementation:** the files and core design choice added that day.
3. **Evidence:** tests, benchmark numbers, screenshots, or a reproducible command.
4. **Next risk:** one known limitation that the next update will address.

## Portfolio evidence at the end

- A concise architecture diagram and a two-minute demo.
- A reproducible benchmark with success and failure cases.
- A security section covering secrets, untrusted repositories, prompt
  injection, command execution, and explicit approval boundaries.
- Clean setup instructions, automated tests, CI, and a tagged release.
- A short case study showing how one issue becomes retrieved evidence, a plan,
  a proposed diff, and a verified result.
