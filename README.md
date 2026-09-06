# RepoPilot — Evidence-first AI Coding Agent

RepoPilot is a portfolio project that explores how an AI coding agent can understand an unfamiliar repository, retrieve the right context, answer questions with evidence, propose reviewable patches, and verify results with tests.

## Build progress

### Day 1 — Repository scanner

- Recursively scans source repositories while ignoring generated, dependency, cache, and secret directories.
- Collects paths, languages, line counts, byte sizes, and content hashes.
- Produces deterministic human-readable and JSON inventories.

### Day 2 — Python AST symbol map

- Parses Python without executing source code.
- Extracts classes, functions, methods, signatures, imports, qualified names, and line ranges.
- Isolates syntax errors so one malformed file cannot stop repository analysis.

### Day 3 — Symbol-aware chunking

- Splits Python at class and function boundaries before applying size limits.
- Attaches source path, language, symbol, kind, and exact line range to every chunk.
- Supports configurable overlapping windows for large code regions.

### Day 4 — Local BM25 retrieval

- Ranks repository chunks with a standard-library in-memory BM25 index.
- Indexes paths, symbols, and source while splitting snake_case and camelCase terms.
- Returns scores, source content, symbols, and line ranges without an API key.

BM25 matches words rather than meaning, so synonyms and cross-language questions may miss relevant code. Scores are ranking values, not confidence percentages.

### Day 5 — Grounded repository Q&A

The new ask command answers only from retrieved repository chunks. Every supported answer includes a verbatim excerpt and path:Lstart-Lend citations. JSON output exposes structured evidence for future agent or UI integrations.

Questions without meaningful matching code return an explicit refusal and exit status 1 instead of inventing an answer. Five grounded cases cover file reading, AST parsing, code chunking, BM25 ranking, and JSON serialization; additional tests cover refusal and bounded excerpts.

This first version is extractive: it identifies and quotes the strongest evidence but does not yet synthesize explanations across several files.

## Architecture target

User issue → repository scanner → symbol map → chunk/index → context retrieval → grounded answer/planning → reviewable diff → test verification

RepoPilot defaults to read-only analysis and diff-only proposals. It will never execute generated commands or modify a target repository without explicit user action.

## Quick start

~~~bash
python -m pip install -e .
repopilot scan .
repopilot symbols . --json
repopilot chunks . --max-lines 80 --overlap-lines 10 --json
repopilot search "parse syntax" src/repopilot --top-k 3
repopilot ask "Where is Python syntax parsed?" src/repopilot
repopilot ask "Where is Python syntax parsed?" src/repopilot --json
~~~

Run the tests:

~~~bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
~~~

## Two-week build log

The dated plan and acceptance criteria are in [docs/14-day-build-plan.md](docs/14-day-build-plan.md). Each day ends with a working feature, tests or evaluation evidence, and one focused public update.

## Design references

The design is informed by public coding-agent projects, especially Aider's repository map, SWE-agent's issue-to-fix workflow, and Continue's source-controlled checks. RepoPilot is an independent educational implementation and does not copy their source code.

## License

MIT
