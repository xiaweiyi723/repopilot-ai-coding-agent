"""RepoPilot package."""

from .chunks import CodeChunk, chunk_repository, chunk_source
from .scanner import RepositoryInventory, SourceFile, scan_repository
from .symbols import CodeSymbol, PythonModuleMap, build_python_symbol_map

__all__ = [
    "CodeChunk",
    "CodeSymbol",
    "PythonModuleMap",
    "RepositoryInventory",
    "SourceFile",
    "build_python_symbol_map",
    "chunk_repository",
    "chunk_source",
    "scan_repository",
]
__version__ = "0.1.0"
