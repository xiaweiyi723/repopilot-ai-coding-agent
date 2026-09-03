"""Symbol-aware source chunking for repository retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .scanner import scan_repository
from .symbols import CodeSymbol, extract_python_module


@dataclass(frozen=True, slots=True)
class CodeChunk:
    """A retrieval-ready slice of source code with traceable metadata."""

    path: str
    language: str
    line_start: int
    line_end: int
    content: str
    symbol: str | None = None
    symbol_kind: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _top_level_symbols(symbols: tuple[CodeSymbol, ...]) -> list[CodeSymbol]:
    return sorted(
        (symbol for symbol in symbols if "." not in symbol.qualified_name),
        key=lambda symbol: (symbol.line_start, symbol.line_end),
    )


def _line_windows(
    *,
    path: str,
    language: str,
    lines: list[str],
    line_start: int,
    line_end: int,
    max_lines: int,
    overlap_lines: int,
    symbol: CodeSymbol | None = None,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    step = max_lines - overlap_lines
    window_start = line_start
    while window_start <= line_end:
        window_end = min(window_start + max_lines - 1, line_end)
        content = "\n".join(lines[window_start - 1 : window_end]).strip("\n")
        if content.strip():
            chunks.append(
                CodeChunk(
                    path=path,
                    language=language,
                    line_start=window_start,
                    line_end=window_end,
                    content=content,
                    symbol=symbol.qualified_name if symbol else None,
                    symbol_kind=symbol.kind if symbol else None,
                )
            )
        if window_end == line_end:
            break
        window_start += step
    return chunks


def chunk_source(
    path: str,
    source: str,
    *,
    language: str = "Python",
    max_lines: int = 80,
    overlap_lines: int = 10,
) -> tuple[CodeChunk, ...]:
    """Split source at Python symbol boundaries, then by overlapping windows."""

    if max_lines < 1:
        raise ValueError("max_lines must be at least 1")
    if overlap_lines < 0 or overlap_lines >= max_lines:
        raise ValueError("overlap_lines must satisfy 0 <= overlap_lines < max_lines")

    lines = source.splitlines()
    if not lines:
        return ()

    symbols: list[CodeSymbol] = []
    if language == "Python":
        module = extract_python_module(path, source)
        if module.parse_error is None:
            symbols = _top_level_symbols(module.symbols)

    if not symbols:
        return tuple(
            _line_windows(
                path=path,
                language=language,
                lines=lines,
                line_start=1,
                line_end=len(lines),
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            )
        )

    chunks: list[CodeChunk] = []
    cursor = 1
    for symbol in symbols:
        if cursor < symbol.line_start:
            chunks.extend(
                _line_windows(
                    path=path,
                    language=language,
                    lines=lines,
                    line_start=cursor,
                    line_end=symbol.line_start - 1,
                    max_lines=max_lines,
                    overlap_lines=overlap_lines,
                )
            )
        chunks.extend(
            _line_windows(
                path=path,
                language=language,
                lines=lines,
                line_start=symbol.line_start,
                line_end=symbol.line_end,
                max_lines=max_lines,
                overlap_lines=overlap_lines,
                symbol=symbol,
            )
        )
        cursor = max(cursor, symbol.line_end + 1)

    if cursor <= len(lines):
        chunks.extend(
            _line_windows(
                path=path,
                language=language,
                lines=lines,
                line_start=cursor,
                line_end=len(lines),
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            )
        )
    return tuple(chunks)


def chunk_repository(
    root: str | Path,
    *,
    max_lines: int = 80,
    overlap_lines: int = 10,
) -> tuple[CodeChunk, ...]:
    """Build deterministic chunks for every readable scanned source file."""

    resolved_root = Path(root).expanduser().resolve()
    inventory = scan_repository(resolved_root)
    chunks: list[CodeChunk] = []
    for record in inventory.files:
        try:
            source = (resolved_root / record.path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        chunks.extend(
            chunk_source(
                record.path,
                source,
                language=record.language,
                max_lines=max_lines,
                overlap_lines=overlap_lines,
            )
        )
    return tuple(chunks)
