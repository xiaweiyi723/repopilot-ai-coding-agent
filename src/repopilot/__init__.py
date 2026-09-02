"""RepoPilot package."""

from .scanner import RepositoryInventory, SourceFile, scan_repository
from .symbols import CodeSymbol, PythonModuleMap, build_python_symbol_map

__all__ = [
    "CodeSymbol",
    "PythonModuleMap",
    "RepositoryInventory",
    "SourceFile",
    "build_python_symbol_map",
    "scan_repository",
]
__version__ = "0.1.0"
