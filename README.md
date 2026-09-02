# RepoPilot — Evidence-first AI Coding Agent

RepoPilot is a portfolio project for exploring how an AI coding agent can
understand an unfamiliar repository, retrieve the right context, propose a
reviewable patch, and verify the result with tests.

The project deliberately starts with a model-free repository scanner. Later
iterations will add code-aware retrieval, tool calling, patch planning, and an
evaluation harness. This keeps every public commit runnable and makes progress
easy to verify.

## Day 1 status

- Recursively scan a local source repository.
- Ignore common generated, dependency, cache, and secret directories.
- Collect path, language, line count, byte size, and content hash.
- Produce a JSON inventory that later retrieval and agent tools can consume.
- Unit tests cover filtering, metadata, and stable ordering.

## Day 2 status

- Parse Python source safely with the standard-library AST without executing it.
- Extract classes, functions, async functions, methods, qualified names, line
  ranges, signatures, and imports.
- Isolate syntax errors so one malformed file does not stop the repository map.
- Expose human-readable and JSON symbol maps through the CLI.
- Add tests for symbol kinds, signatures, relative imports, malformed source,
  stable ordering, and ignored directories.

## Architecture target

```text
User issue
   |
   v
Repository scanner -> symbol map -> chunk/index -> context retriever
                                               |
                                               v
                                      planning agent
                                               |
                                               v
                                      reviewable diff
                                               |
                                               v
                                    lint/test verification
```

RepoPilot will default to **read-only analysis and diff-only proposals**. It
will never execute generated commands or modify a target repository without an
explicit user action.

## Quick start

```bash
python -m pip install -e .
repopilot scan .
repopilot scan . --json
repopilot symbols .
repopilot symbols . --json
```

Run the tests:

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
```

You can also run the module directly without installation:

```bash
PYTHONPATH=src python -m repopilot.cli scan . --json
```

## Example output

```text
Repository: C:/projects/example
Source files: 12
Lines of code: 846
Languages: Python=8, Markdown=4
```

## Two-week build log

The dated plan and acceptance criteria are in
[docs/14-day-build-plan.md](docs/14-day-build-plan.md). Each day ends with a
working feature, tests or evaluation evidence, and one focused commit.

## Design references

The design is informed by public coding-agent projects, especially Aider's
repository map, SWE-agent's issue-to-fix workflow, and Continue's source-
controlled checks. RepoPilot is an independent educational implementation and
does not copy their source code.

## License

MIT
