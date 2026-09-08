"""Reproducible retrieval and citation evaluation; no model calls."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .chunks import chunk_repository
from .qa import answer_chunks


def load_cases(path):
    cases = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    seen = set()
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"] or case["id"] in seen:
            raise ValueError("Each case needs a unique nonempty id")
        seen.add(case["id"])
        if not isinstance(case.get("question"), str) or not case["question"].strip():
            raise ValueError("Each case needs a question")
        if type(case.get("answerable")) is not bool:
            raise ValueError("answerable must be boolean")
        if case["answerable"] and (not isinstance(case.get("path"), str) or not isinstance(case.get("symbol"), str)):
            raise ValueError("Answerable cases need path and symbol labels")
    if not cases:
        raise ValueError("Dataset must not be empty")
    return cases


def evaluate(chunks, cases, top_k=3):
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    chunks = tuple(chunks)
    rows = []
    for case in cases:
        # Fail loudly on stale labels rather than silently lowering scores.
        if case["answerable"] and not any(c.path == case["path"] and c.symbol == case["symbol"] for c in chunks):
            raise ValueError(f"Unresolvable label: {case['id']}")
        result = answer_chunks(case["question"], chunks, top_k=top_k)
        relevant = [c.path == case.get("path") and c.symbol == case.get("symbol") for c in result.citations]
        valid = []
        for citation in result.citations:
            # Verify both coordinates and excerpt against the indexed source.
            candidates = [c for c in chunks if (c.path, c.line_start, c.line_end, c.symbol) ==
                          (citation.path, citation.line_start, citation.line_end, citation.symbol)]
            excerpt = citation.excerpt.removesuffix("…")
            valid.append(bool(excerpt) and any(excerpt in " ".join(line.strip() for line in c.content.splitlines() if line.strip()) for c in candidates))
        rank = next((i + 1 for i, hit in enumerate(relevant) if hit), None)
        rows.append({"id": case["id"], "question": case["question"], "answerable": case["answerable"],
                     "supported": result.supported, "hit_at_k": rank is not None,
                     "primary_correct": bool(relevant and relevant[0]),
                     "reciprocal_rank": 1 / rank if rank else 0,
                     "citation_count": len(valid), "valid_citations": sum(valid),
                     "citations": [c.location for c in result.citations]})
    positive = [r for r in rows if r["answerable"]]
    negative = [r for r in rows if not r["answerable"]]
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else None
    return {"schema_version": 1, "top_k": top_k, "case_count": len(rows),
            "answerable_count": len(positive), "unanswerable_count": len(negative),
            "metrics": {
                "hit_at_k": ratio(sum(r["hit_at_k"] for r in positive), len(positive)),
                "primary_citation_accuracy": ratio(sum(r["primary_correct"] for r in positive), len(positive)),
                "mrr_at_k": ratio(sum(r["reciprocal_rank"] for r in positive), len(positive)),
                "citation_source_validity": ratio(sum(r["valid_citations"] for r in rows), sum(r["citation_count"] for r in rows)),
                "refusal_accuracy": ratio(sum(not r["supported"] for r in negative), len(negative)),
            }, "cases": rows}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Source root, excluding benchmark labels and reports")
    parser.add_argument("dataset")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        chunks = chunk_repository(args.root)
        report = evaluate(chunks, load_cases(args.dataset), args.top_k)
        report["dataset_sha256"] = sha256(Path(args.dataset).read_bytes()).hexdigest()
        # Content-normalized fingerprint survives checkout newline conversion.
        payload = json.dumps([c.to_dict() for c in chunks], sort_keys=True, ensure_ascii=False)
        report["corpus_sha256"] = sha256(payload.encode("utf-8")).hexdigest()
        report["chunk_count"] = len(chunks)
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
