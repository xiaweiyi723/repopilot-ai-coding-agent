"""Model-independent, read-only repository tools and JSON schemas.

Run ``python -m repopilot.tools --help`` for the standalone CLI.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from fnmatch import fnmatchcase
import json
from pathlib import Path, PurePosixPath

from .scanner import scan_repository
from .symbols import build_python_symbol_map


def tool_schemas() -> list[dict]:
    """Return fresh provider-neutral function definitions."""
    specifications = [
        ("file_search", "Find scanned source files by case-sensitive path glob.", "pattern"),
        ("symbol_lookup", "Find Python symbols by exact name or qualified name.", "name"),
        ("dependency_lookup", "List static Python imports for a repository-relative file.", "path"),
    ]
    return [
        {"name": name, "description": description, "parameters": {
            "type": "object",
            "properties": {
                argument: {"type": "string", "minLength": 1, "maxLength": 256},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
            "required": [argument], "additionalProperties": False,
        }}
        for name, description, argument in specifications
    ]


class RepositoryTools:
    """Bind the repository root in trusted host code, not model arguments.

    Results describe a static snapshot. No source code is executed, no shell
    commands are run, and no files are changed. Refresh by creating a new instance.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.inventory = scan_repository(self.root)
        self._modules = None

    def _python_modules(self):
        if self._modules is None:
            self._modules = build_python_symbol_map(self.root)
        return self._modules

    def call(self, name: str, arguments: dict) -> dict:
        """Validate a tool call and return a bounded JSON-serializable result."""
        schemas = {schema["name"]: schema for schema in tool_schemas()}
        if name not in schemas:
            raise ValueError(f"Unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object")
        key = schemas[name]["parameters"]["required"][0]
        if set(arguments) - {key, "limit"}:
            raise ValueError("Unexpected tool arguments")
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError(f"{key} must be a nonempty string of at most 256 characters")
        limit = arguments.get("limit", 20)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer between 1 and 100")

        errors = []
        if name == "file_search":
            rows = [asdict(file) for file in self.inventory.files
                    if fnmatchcase(file.path, value)]
        elif name == "symbol_lookup":
            rows = []
            for module in self._python_modules():
                if module.parse_error:
                    errors.append({"path": module.path, "error": module.parse_error})
                rows.extend({"path": module.path, **asdict(symbol)}
                            for symbol in module.symbols
                            if value in (symbol.name, symbol.qualified_name))
        else:
            # Membership in the safe scan is mandatory. Never read arbitrary paths.
            normalized = value.replace("\\", "/")
            path = PurePosixPath(normalized)
            if path.is_absolute() or ".." in path.parts or ":" in normalized:
                raise ValueError("path must stay inside the bound repository")
            normalized = path.as_posix()
            if normalized not in {file.path for file in self.inventory.files}:
                raise ValueError("path is not an available scanned source file")
            module = next((m for m in self._python_modules() if m.path == normalized), None)
            if module is None:
                raise ValueError("dependency_lookup currently supports Python files only")
            if module.parse_error:
                errors.append({"path": module.path, "error": module.parse_error})
            rows = [{"path": module.path, **asdict(reference)} for reference in module.imports]
        return {"tool": name, "results": rows[:limit], "total": len(rows),
                "truncated": len(rows) > limit, "errors": errors[:limit],
                "errors_truncated": len(errors) > limit}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--schemas", action="store_true")
    parser.add_argument("--tool", choices=[s["name"] for s in tool_schemas()])
    parser.add_argument("--arguments", default="{}", help="JSON object")
    args = parser.parse_args(argv)
    try:
        if args.schemas:
            result = tool_schemas()
        else:
            if not args.tool:
                parser.error("provide --schemas or --tool")
            result = RepositoryTools(args.root).call(args.tool, json.loads(args.arguments))
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
