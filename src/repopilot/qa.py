"""Grounded repository question answering with line-level citations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .chunks import CodeChunk, chunk_repository
from .retrieval import BM25Index, tokenize

_STOP_WORDS = {"a", "an", "and", "are", "does", "for", "how", "in", "is", "it", "of", "on", "or", "the", "this", "to", "what", "where", "which"}

@dataclass(frozen=True, slots=True)
class Citation:
    """A verbatim code excerpt and its repository location."""
    path: str
    line_start: int
    line_end: int
    symbol: str | None
    excerpt: str

    @property
    def location(self) -> str:
        return f"{self.path}:L{self.line_start}-L{self.line_end}"

@dataclass(frozen=True, slots=True)
class RepositoryAnswer:
    question: str
    supported: bool
    answer: str
    citations: tuple[Citation, ...]

    def to_dict(self) -> dict[str, object]:
        return {"question": self.question, "supported": self.supported, "answer": self.answer, "citations": [asdict(citation) | {"location": citation.location} for citation in self.citations]}

def _query_terms(question: str) -> list[str]:
    return [term for term in tokenize(question) if term not in _STOP_WORDS]

def _excerpt(chunk: CodeChunk, limit: int = 220) -> str:
    lines = [line.strip() for line in chunk.content.splitlines() if line.strip()]
    text = " ".join(lines)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

def answer_chunks(question: str, chunks: Iterable[CodeChunk], *, top_k: int = 3) -> RepositoryAnswer:
    """Answer from lexical evidence, refusing when no meaningful term matches."""
    terms = _query_terms(question)
    if not terms:
        return RepositoryAnswer(question, False, "I cannot answer from the repository because the question has no searchable code terms.", ())
    hits = BM25Index(chunks).search(" ".join(terms), top_k=top_k)
    if not hits:
        return RepositoryAnswer(question, False, "I cannot answer from the repository because no supporting code was found.", ())
    citations = tuple(Citation(path=hit.chunk.path, line_start=hit.chunk.line_start, line_end=hit.chunk.line_end, symbol=hit.chunk.symbol, excerpt=_excerpt(hit.chunk)) for hit in hits)
    primary = citations[0]
    subject = f"{primary.symbol}" if primary.symbol else "the cited module section"
    answer = f"The strongest repository evidence is {subject} at {primary.location}. Evidence: {primary.excerpt}"
    return RepositoryAnswer(question, True, answer, citations)

def answer_repository(question: str, root: str | Path, *, top_k: int = 3) -> RepositoryAnswer:
    return answer_chunks(question, chunk_repository(root), top_k=top_k)
