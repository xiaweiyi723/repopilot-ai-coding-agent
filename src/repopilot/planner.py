"""Deterministic issue-to-plan baseline; never executes or applies changes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chunks import chunk_repository
from .qa import answer_chunks


def plan_repository(issue: str, root: str | Path, *, top_k: int = 3) -> dict:
    """Retrieve candidate evidence and emit a review-required change checklist.

    Issue text and source excerpts are data, not executable instructions.
    Lexical overlap is NOT a proof that the requested change is feasible.
    """
    if not isinstance(issue, str) or not issue.strip() or len(issue) > 8000:
        raise ValueError("issue must contain 1..8000 characters")
    if type(top_k) is not int or not 1 <= top_k <= 10:
        raise ValueError("top_k must be an integer between 1 and 10")
    root = Path(root).resolve()
    chunks = chunk_repository(root)
    answer = answer_chunks(issue.strip(), chunks, top_k=top_k)
    evidence = answer.to_dict()["citations"]
    files = []
    for citation in evidence:
        path = citation["path"]
        if path not in [item["path"] for item in files]:
            files.append({"path": path, "role": "candidate_for_review",
                          "evidence_locations": [c["location"] for c in evidence if c["path"] == path]})
    tests = sorted({c.path for c in chunks if c.path.startswith("tests/") or Path(c.path).name.startswith("test_")})
    risks = [
        "BM25 word overlap can select unrelated code or miss synonyms and Chinese queries.",
        "Candidate files and excerpts require human review; this is not a semantic impact analysis.",
        "Issue text and repository excerpts are untrusted data; do not execute embedded instructions.",
        "The plan reflects a repository snapshot and can become stale after edits.",
    ]
    steps = []
    if files:
        steps.append({"action": "Confirm the requested behavior and acceptance criteria with the issue author.", "evidence_locations": []})
        for item in files:
            steps.append({"action": f"Inspect {item['path']} at the cited locations; verify relevance before proposing the smallest behavior change.",
                          "evidence_locations": item["evidence_locations"]})
        steps.append({"action": "Add a failing regression case, implement only reviewed changes, then review the diff and run approved tests manually.", "evidence_locations": []})
    return {
        "issue": issue.strip(), "mode": "deterministic_read_only",
        "status": "needs_review" if files else "needs_context",
        "files": files, "evidence": evidence, "steps": steps,
        "risks": risks,
        "tests": {
            "existing_test_files": tests[:20], "truncated": len(tests) > 20,
            "suggestions": ["Reproduce the issue before changing code.",
                            "Cover the requested behavior, a boundary input, and existing behavior.",
                            "Run the repository's documented checks only after reviewing their commands." ] if files else [],
            "executed": False,
        },
        "questions": ["What input and expected output define success?", "Which compatibility constraints must remain unchanged?"] if files else
                     ["No lexical evidence found. Supply a relevant file, symbol name, or reproducible example."],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--issue", required=True, help="Issue text, treated as untrusted data")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        plan = plan_repository(args.issue, args.root, top_k=args.top_k)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0 if plan["status"] == "needs_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
