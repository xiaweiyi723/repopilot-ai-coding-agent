"""Guarded, replacement-based unified diffs. No apply or execution capability."""

from __future__ import annotations

import argparse
import difflib
from hashlib import sha256
import json
from pathlib import Path
import re

from .scanner import DEFAULT_EXTENSIONS, DEFAULT_IGNORED_DIRECTORIES

MAX_FILE_BYTES = 128 * 1024
MAX_DIFF_BYTES = 512 * 1024
MAX_EDITS = 8
MAX_REQUEST_BYTES = 2 * 1024 * 1024


def _target(root: Path, name: str) -> Path:
    # Conservative portable names also prevent injecting diff headers.
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_./-]{1,240}", name):
        raise ValueError("path must be a portable relative source path")
    parts = name.split("/")
    if any(not p or p in {".", ".."} or p.startswith(".") or p.endswith(".") for p in parts):
        raise ValueError("hidden, empty, dot and traversal components are forbidden")
    if any(p.casefold() in DEFAULT_IGNORED_DIRECTORIES for p in parts):
        raise ValueError("generated and dependency paths are forbidden")
    if any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p) for p in parts):
        raise ValueError("reserved device paths are forbidden")
    if any(word in name.casefold() for word in ("secret", "credential", "private_key", "id_rsa")):
        raise ValueError("sensitive filenames are forbidden")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError("symlinks and junctions are forbidden")
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("target must be an existing file inside the repository")
    if path.suffix.lower() not in DEFAULT_EXTENSIONS:
        raise ValueError("unsupported source extension")
    return path


def _text(raw: bytes) -> str:
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("file exceeds byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("only UTF-8 text is supported") from exc
    if any(ord(c) < 32 and c not in "\t\r\n" or ord(c) == 127 for c in text):
        raise ValueError("binary/control-byte content is forbidden")
    if "\r" in text.replace("\r\n", ""):
        raise ValueError("bare CR line endings are unsupported")
    return text


def _diff(before: str, after: str, name: str) -> str:
    def lines_of(text):
        parts = text.split("\n")
        return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])

    lines = difflib.unified_diff(lines_of(before), lines_of(after),
                                 fromfile=f"a/{name}", tofile=f"b/{name}", n=3)
    # difflib omits the conventional missing-final-newline marker.
    return "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines)


def propose_patch(root: str | Path, edits: list[dict]) -> dict:
    """Validate full replacements against byte hashes and return a diff only.

    The host chooses root; each edit is {path, before_sha256, content}.
    A missing/stale hash rejects the entire proposal. Nothing is written.
    """
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("repository root must be a directory")
    if not isinstance(edits, list) or not 1 <= len(edits) <= MAX_EDITS:
        raise ValueError(f"edits must contain 1..{MAX_EDITS} replacements")
    seen, results, diffs = set(), [], []
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"path", "before_sha256", "content"}:
            raise ValueError("each edit requires exactly path, before_sha256 and content")
        path = _target(root, edit["path"])
        key = edit["path"].casefold()
        if key in seen:
            raise ValueError("duplicate target path")
        seen.add(key)
        expected = edit["before_sha256"]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("before_sha256 must be a lowercase SHA-256 digest")
        with path.open("rb") as source:
            raw = source.read(MAX_FILE_BYTES + 1)
        before = _text(raw)
        if sha256(raw).hexdigest() != expected:
            raise ValueError("stale source: before_sha256 does not match")
        content = edit["content"]
        if not isinstance(content, str) or len(content) > MAX_FILE_BYTES:
            raise ValueError("content must be a bounded string")
        try:
            new_raw = content.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("content must encode as UTF-8") from exc
        after = _text(new_raw)
        diff = _diff(before, after, edit["path"])
        diffs.append(diff)
        if sum(len(d.encode("utf-8")) for d in diffs) > MAX_DIFF_BYTES:
            raise ValueError("combined diff exceeds byte limit")
        results.append({"path": edit["path"], "before_sha256": expected,
                        "after_sha256": sha256(new_raw).hexdigest(), "changed": bool(diff)})
    return {"mode": "diff_only", "applied": False, "files": results,
            "diff": "".join(diffs), "requires_review": True,
            "warnings": ["No semantic correctness, secret scanning or execution safety is established.",
                         "Review the diff and recheck source hashes before any manual application.",
                         "Use a stable trusted snapshot; this is not a sandbox against concurrent filesystem changes."]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--edits", required=True, type=Path, help="JSON array of explicit replacements")
    parser.add_argument("--json", action="store_true", help="Include hashes and review metadata")
    args = parser.parse_args(argv)
    try:
        with args.edits.open("rb") as source:
            raw = source.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise ValueError("request exceeds byte limit")
        result = propose_patch(args.root, json.loads(raw))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["diff"], end="\n" if args.json else "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
