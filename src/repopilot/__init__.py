"""RepoPilot package."""

from .chunks import CodeChunk, chunk_repository, chunk_source
from .qa import Citation, RepositoryAnswer, answer_repository
from .scanner import RepositoryInventory, SourceFile, scan_repository
from .symbols import CodeSymbol, PythonModuleMap, build_python_symbol_map

__all__ = [
    "CodeChunk",
    "Citation",
    "CodeSymbol",
    "PythonModuleMap",
    "RepositoryInventory",
    "RepositoryAnswer",
    "SourceFile",
    "build_python_symbol_map",
    "answer_repository",
    "chunk_repository",
    "chunk_source",
    "scan_repository",
]
__version__ = "0.1.0"
