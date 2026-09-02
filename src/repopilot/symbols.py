"""Python AST symbol extraction for repository-aware code retrieval."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path

from .scanner import scan_repository


@dataclass(frozen=True, slots=True)
class CodeSymbol:
    """A class or callable discovered in one Python source file."""

    name: str
    qualified_name: str
    kind: str
    line_start: int
    line_end: int
    signature: str


@dataclass(frozen=True, slots=True)
class ImportReference:
    """A normalized import statement and its source location."""

    module: str
    names: tuple[str, ...]
    line: int


@dataclass(frozen=True, slots=True)
class PythonModuleMap:
    """Symbols and imports extracted from a Python module."""

    path: str
    symbols: tuple[CodeSymbol, ...]
    imports: tuple[ImportReference, ...]
    parse_error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "symbols": [asdict(symbol) for symbol in self.symbols],
            "imports": [asdict(reference) for reference in self.imports],
            "parse_error": self.parse_error,
        }


def _format_annotation(annotation: ast.expr | None) -> str:
    return f": {ast.unparse(annotation)}" if annotation is not None else ""


def _format_default(default: ast.expr | None) -> str:
    return f" = {ast.unparse(default)}" if default is not None else ""


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(arguments.defaults))
    defaults.extend(arguments.defaults)

    parts = [
        f"{argument.arg}{_format_annotation(argument.annotation)}{_format_default(default)}"
        for argument, default in zip(positional, defaults, strict=True)
    ]
    if arguments.posonlyargs:
        parts.insert(len(arguments.posonlyargs), "/")

    if arguments.vararg is not None:
        parts.append(f"*{arguments.vararg.arg}{_format_annotation(arguments.vararg.annotation)}")
    elif arguments.kwonlyargs:
        parts.append("*")

    parts.extend(
        f"{argument.arg}{_format_annotation(argument.annotation)}{_format_default(default)}"
        for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True)
    )
    if arguments.kwarg is not None:
        parts.append(f"**{arguments.kwarg.arg}{_format_annotation(arguments.kwarg.annotation)}")

    return_annotation = (
        f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    )
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(parts)}){return_annotation}"


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[tuple[str, str]] = []
        self.symbols: list[CodeSymbol] = []
        self.imports: list[ImportReference] = []

    def _qualified_name(self, name: str) -> str:
        return ".".join([*(scope_name for scope_name, _ in self.scope), name])

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        bases = ", ".join(ast.unparse(base) for base in node.bases)
        signature = f"class {node.name}({bases})" if bases else f"class {node.name}"
        self.symbols.append(
            CodeSymbol(
                name=node.name,
                qualified_name=self._qualified_name(node.name),
                kind="class",
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                signature=signature,
            )
        )
        self.scope.append((node.name, "class"))
        self.generic_visit(node)
        self.scope.pop()

    def _visit_callable(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        inside_class = bool(self.scope and self.scope[-1][1] == "class")
        is_async = isinstance(node, ast.AsyncFunctionDef)
        kind = "async_method" if inside_class and is_async else "method" if inside_class else (
            "async_function" if is_async else "function"
        )
        self.symbols.append(
            CodeSymbol(
                name=node.name,
                qualified_name=self._qualified_name(node.name),
                kind=kind,
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                signature=_format_signature(node),
            )
        )
        self.scope.append((node.name, "function"))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_callable(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_callable(node)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        self.imports.append(
            ImportReference(
                module="",
                names=tuple(alias.name for alias in node.names),
                line=node.lineno,
            )
        )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = f"{'.' * node.level}{node.module or ''}"
        self.imports.append(
            ImportReference(
                module=module,
                names=tuple(alias.name for alias in node.names),
                line=node.lineno,
            )
        )


def extract_python_module(path: str, source: str) -> PythonModuleMap:
    """Extract code symbols without executing the supplied Python source."""

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        location = f"line {error.lineno}" if error.lineno is not None else "unknown line"
        return PythonModuleMap(
            path=path,
            symbols=(),
            imports=(),
            parse_error=f"{error.msg} ({location})",
        )

    visitor = _SymbolVisitor()
    visitor.visit(tree)
    return PythonModuleMap(
        path=path,
        symbols=tuple(visitor.symbols),
        imports=tuple(visitor.imports),
    )


def build_python_symbol_map(root: str | Path) -> tuple[PythonModuleMap, ...]:
    """Build a deterministic symbol map for all scanned Python files."""

    resolved_root = Path(root).expanduser().resolve()
    inventory = scan_repository(resolved_root)
    modules: list[PythonModuleMap] = []
    for record in inventory.files:
        if record.language != "Python":
            continue
        file_path = resolved_root / record.path
        try:
            source = file_path.read_text(encoding="utf-8")
        except OSError as error:
            modules.append(
                PythonModuleMap(
                    path=record.path,
                    symbols=(),
                    imports=(),
                    parse_error=str(error),
                )
            )
            continue
        modules.append(extract_python_module(record.path, source))
    return tuple(modules)

