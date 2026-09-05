"""Dependency-free BM25 retrieval over source chunks; no model calls."""

import math
import re
from collections import Counter
from dataclasses import dataclass

from .chunks import CodeChunk


def tokenize(text: str) -> list[str]:
    """Split snake_case and camelCase identifiers for lexical matching."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE)


@dataclass(frozen=True)
class SearchHit:
    chunk: CodeChunk
    score: float

    def to_dict(self) -> dict:
        return {"score": self.score, **self.chunk.to_dict()}


class BM25Index:
    """In-memory index with deterministic ties and positive-score results."""

    def __init__(self, chunks):
        self.chunks = tuple(chunks)
        self.terms = [Counter(tokenize(f"{c.path} {c.symbol or ''} {c.content}"))
                      for c in self.chunks]
        self.lengths = [sum(t.values()) for t in self.terms]
        self.average_length = sum(self.lengths) / len(self.lengths) if self.lengths else 1
        self.document_frequency = Counter(t for terms in self.terms for t in terms)

    def search(self, query: str, top_k: int = 5) -> tuple[SearchHit, ...]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        query_terms = set(tokenize(query))
        hits = []
        for chunk, terms, length in zip(self.chunks, self.terms, self.lengths):
            score = 0.0
            for term in sorted(query_terms):
                frequency = terms[term]
                if not frequency:
                    continue
                df = self.document_frequency[term]
                idf = math.log(1 + (len(self.chunks) - df + 0.5) / (df + 0.5))
                normalization = 1.5 * (0.25 + 0.75 * length / (self.average_length or 1))
                score += idf * frequency * 2.5 / (frequency + normalization)
            if score > 0:
                hits.append(SearchHit(chunk, score))
        hits.sort(key=lambda h: (-h.score, h.chunk.path, h.chunk.line_start, h.chunk.line_end))
        return tuple(hits[:top_k])
