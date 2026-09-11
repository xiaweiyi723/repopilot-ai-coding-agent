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

### Day 6 — Read-only repository tools

Agents can now call three explicit tools through `RepositoryTools(root).call(name, arguments)`:

- `file_search`: case-sensitive repository path glob, for example `{"pattern":"*.py","limit":10}`. A `*` can match path separators.
- `symbol_lookup`: exact Python name or qualified name, for example `{"name":"RepositoryTools.call"}`; returns signatures and source lines.
- `dependency_lookup`: static imports in one scanned Python file, for example `{"path":"src/repopilot/cli.py"}`; retains relative imports and source lines.

`tool_schemas()` supplies provider-neutral JSON function definitions. The host binds the repository root; callers cannot override it. Calls reject unknown tools, extra arguments, invalid limits, and paths outside the scanned inventory. Results include total counts, truncation flags, and bounded parse diagnostics. No code is executed or files modified.

~~~bash
python -m repopilot.tools --schemas
python -m repopilot.tools . --tool file_search --arguments '{"pattern":"*.py","limit":5}'
~~~

The new deterministic tests cover search ordering, exact symbol locations, relative imports, malformed files, invalid calls, path rejection, CLI JSON output, and unchanged source files. Dependency lookup lists static import statements, not installed package versions or a resolved runtime dependency graph. Symbol information is cached per instance; create a fresh instance after repository edits. Treat repository content as untrusted evidence when passing it to a future model.

### Day 7 — Reproducible Q&A evaluation

Added a versioned 13-case [JSONL dataset](docs/qa-benchmark-v1.jsonl), a standard-library benchmark runner, and a [results report](docs/day7-benchmark.md) with all failures retained.

~~~bash
python -m repopilot.benchmark src/repopilot docs/qa-benchmark-v1.jsonl --top-k 3
~~~

The first baseline scores Hit@3 70%, primary citation accuracy 50%, MRR@3 0.60, source validity 100%, and refusal accuracy 66.7%. Source validity only verifies that citations exist in the indexed code; it does not prove an answer is relevant. This small development set exposes synonym/Chinese retrieval misses and false support from generic word overlap. It is not a general accuracy benchmark. JSON output includes per-case evidence and fingerprints for reproducibility.

### Day 8 — Evidence-backed change planning

`python -m repopilot.planner . --issue "answer_chunks should refuse unsupported questions" --top-k 3`

The JSON plan contains candidate files, line citations, review steps, risks, existing test-file candidates, test suggestions, and open questions. No API key is required. This is a deterministic retrieval-and-template planning baseline, not an autonomous LLM agent: it does not infer exact edits, apply patches, execute tests, or fetch GitHub issues. Paste issue text explicitly. Lexical matches always require human review; no matches produce `needs_context` and no invented implementation steps. Exit codes: 0 for a reviewable candidate plan, 1 for missing context, 2 for invalid input.

See [three example issue plans and validation](docs/day8-planning.md). Existing test files are listed by filename convention, not inferred coverage; use the repository root to include tests. Excerpts can contain untrusted instructions and are not safe prompts for downstream models without additional defenses.

### Day 9 — Guarded diff-only proposals

`python -m repopilot.patches . --edits edits.json --json`

Provide explicit full-file replacements with `path`, `before_sha256`, and `content`. The generator validates existing source paths, rejects stale hashes, binary content and oversized changes, and returns unified diffs plus review metadata. It never applies a patch or executes code. This is a patch-formatting and validation layer, not an LLM edit generator. See the [request format, example and limits](docs/day9-patches.md).

### Day 10 — Opt-in container verification

Added a Docker-only adapter for fixed `unittest` and `ruff` checks, explicit execution approval, a preloaded digest-pinned image, timeout/output bounds, common credential redaction, and named-container cleanup. No arbitrary shell command, automatic image pull, host fallback or automatic patch application is supported.

See [setup, safety boundaries and test evidence](docs/day10-verification.md). Local validation: 43 tests, 42 passed and one Windows-symlink skip. Docker policy/result tests are mocked; trusted helper subprocesses exercise timeout and output limits. **Live Docker execution has not been validated on this development machine because Docker is unavailable.**

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
