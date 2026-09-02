"""Safe, deterministic source-repository inventory.

The scanner is intentionally model-free. It provides trusted metadata for the
retrieval and agent layers that will be added later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Iterable


DEFAULT_EXTENSIONS = {
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".md": "Markdown",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sql": "SQL",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".vue": "Vue",
    ".yaml": "YAML",
    ".yml": "YAML",
}

DEFAULT_IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".repopilot",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "build",
    "dist",
    "node_modules",
    "target",
    "venv",
}


@dataclass(frozen=True, slots=True)
class SourceFile:
    """Metadata for one readable source file."""

    path: str
    language: str
    lines: int
    bytes: int
    sha256: str


@dataclass(frozen=True, slots=True)
class RepositoryInventory:
    """Stable repository-level scan result."""

    root: str
    files: tuple[SourceFile, ...]

    @property
    def total_lines(self) -> int:
        return sum(file.lines for file in self.files)

    @property
    def languages(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for file in self.files:
            counts[file.language] = counts.get(file.language, 0) + 1
        return dict(sorted(counts.items()))

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "source_files": len(self.files),
            "total_lines": self.total_lines,
            "languages": self.languages,
            "files": [asdict(file) for file in self.files],
        }


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
    except (OSError, ValueError):
        return False
    return True


def _iter_candidates(root: Path, ignored: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in ignored for part in relative_parts):
            continue
        if path.is_file() and not path.is_symlink():
            yield path


def scan_repository(
    root: str | Path,
    *,
    max_file_bytes: int = 1_000_000,
    extensions: dict[str, str] | None = None,
    ignored_directories: set[str] | None = None,
) -> RepositoryInventory:
    """Scan source files under *root* without following symlinks.

    Files that cannot be decoded as UTF-8, exceed ``max_file_bytes``, or have
    unsupported extensions are skipped. Paths are returned relative to the
    repository root and sorted for reproducible output.
    """

    resolved_root = Path(root).expanduser().resolve()
    if not resolved_root.is_dir():
        raise ValueError(f"Repository root is not a directory: {resolved_root}")

    language_map = extensions or DEFAULT_EXTENSIONS
    ignored = ignored_directories or DEFAULT_IGNORED_DIRECTORIES
    records: list[SourceFile] = []

    for path in _iter_candidates(resolved_root, ignored):
        if not _is_within_root(path, resolved_root):
            continue
        language = language_map.get(path.suffix.lower())
        if language is None:
            continue
        try:
            size = path.stat().st_size
            if size > max_file_bytes:
                continue
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        line_count = len(text.splitlines())
        records.append(
            SourceFile(
                path=path.relative_to(resolved_root).as_posix(),
                language=language,
                lines=line_count,
                bytes=size,
                sha256=sha256(raw).hexdigest(),
            )
        )

    records.sort(key=lambda record: record.path.casefold())
    return RepositoryInventory(root=str(resolved_root), files=tuple(records))

