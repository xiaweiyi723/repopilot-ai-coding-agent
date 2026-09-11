# Day 9 — Guarded diff-only proposals

## Problem

Before a coding agent edits a repository, its proposed content should be converted into a reviewable diff with explicit path, size and source-version checks.

## Implementation

`propose_patch(root, edits)` accepts a host-selected root and an array of full replacements. Each object contains exactly `path`, `before_sha256` and `content`. The digest is SHA-256 of the original file bytes, not newline-normalized text. Missing or stale hashes reject the entire request. No partial diff is printed on validation failure.

```python
from hashlib import sha256
from pathlib import Path
from repopilot.patches import propose_patch

root = Path("your-repository")
old = (root / "app.py").read_bytes()
result = propose_patch(root, [{
    "path": "app.py",
    "before_sha256": sha256(old).hexdigest(),
    "content": "value = 2\n",
}])
print(result["diff"])
assert result["applied"] is False
```

For an original `value = 1` followed by a newline, the result is:

```diff
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-value = 1
+value = 2
```

To use the CLI, save the same array as `edits.json` with the actual digest, then run:

```bash
python -m repopilot.patches your-repository --edits edits.json
python -m repopilot.patches your-repository --edits edits.json --json
```

Default output is raw unified diff; JSON adds before/after hashes, changed flags, `requires_review=true`, warnings and `applied=false`. Exit 0 means validation succeeded, not that the change is correct or applied; invalid requests exit 2. Identical replacements yield an empty diff. Empty content empties a file in the proposal, rather than deleting the file. Missing final newlines use conventional diff markers. LF and CRLF are retained, so avoid accidental whole-file line-ending changes.

## Guardrails and limits

- Existing files only, with scanner-supported source extensions. No create, rename, delete or permission changes.
- Portable ASCII relative paths, at most 240 characters; no spaces, hidden components, traversal, drive paths, backslashes, control characters or reserved Windows device names.
- Reject ignored build/dependency directories, common sensitive filename patterns, symlinks and junctions along the target path. Resolved paths must remain inside the root.
- Strict UTF-8; reject binary/control bytes and bare CR line endings.
- At most 8 edits, 128 KiB per original/replacement, 512 KiB total diff and 2 MiB CLI request. Duplicate paths are rejected case-insensitively.
- No apply switch, command execution, model call or external request.

## Evidence

37 unit tests ran: 36 passed and one existing Windows symlink-creation test was skipped for missing OS privilege. Seven new test methods cover exact diff output, unchanged source, path attacks, simulated symlink detection, stale hashes, duplicate/schema errors, binary/encoding/size guards, empty and no-newline cases, JSON CLI output and fail-closed multi-edit requests. Simulated link detection is not a claim of live Windows junction testing.

## Limitations and next risk

Day 8 produces a review checklist; Day 9 requires a human or future model adapter to supply explicit replacement content. It does not translate natural-language plans into edits or verify their semantic correctness. Filename filtering is not comprehensive secret scanning: inspect source and diff contents before sharing them. Use a stable trusted repository snapshot; this path-checking layer is not a race-safe filesystem sandbox and does not defend against concurrent link swaps or adversarial mounts. Always recheck hashes and review changes before manual application. Sandboxed command verification remains a separate Day 10 task.
