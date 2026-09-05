"""Command-line interface for RepoPilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .chunks import chunk_repository
from .retrieval import BM25Index
from .scanner import scan_repository
from .symbols import build_python_symbol_map


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repopilot",
        description="Inspect a repository before asking an AI agent to change it.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    scan = subcommands.add_parser("scan", help="Build a deterministic source inventory.")
    scan.add_argument("path", nargs="?", default=".", type=Path)
    scan.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    scan.add_argument(
        "--max-file-bytes",
        type=int,
        default=1_000_000,
        help="Skip source files larger than this value (default: 1000000).",
    )
    symbols = subcommands.add_parser("symbols", help="Build a Python AST symbol map.")
    symbols.add_argument("path", nargs="?", default=".", type=Path)
    symbols.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    chunks = subcommands.add_parser("chunks", help="Build retrieval-ready code chunks.")
    chunks.add_argument("path", nargs="?", default=".", type=Path)
    chunks.add_argument("--max-lines", type=int, default=80)
    chunks.add_argument("--overlap-lines", type=int, default=10)
    chunks.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    search = subcommands.add_parser("search", help="Search code locally using BM25.")
    search.add_argument("query")
    search.add_argument("path", nargs="?", default=".", type=Path)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "search":
        if args.top_k < 1:
            raise SystemExit("--top-k must be positive")
        hits = BM25Index(chunk_repository(args.path)).search(args.query, args.top_k)
        if args.json:
            print(json.dumps({"results": [hit.to_dict() for hit in hits]}, indent=2))
        elif not hits:
            print("No matching code found.")
        else:
            for hit in hits:
                c = hit.chunk
                print(f"{hit.score:.3f} {c.path}:L{c.line_start}-L{c.line_end} [{c.symbol or 'module'}]")
        return 0
    if args.command == "chunks":
        chunks = chunk_repository(
            args.path,
            max_lines=args.max_lines,
            overlap_lines=args.overlap_lines,
        )
        if args.json:
            print(json.dumps({"chunks": [chunk.to_dict() for chunk in chunks]}, indent=2))
            return 0
        for chunk in chunks:
            label = f" [{chunk.symbol}]" if chunk.symbol else ""
            print(f"{chunk.path}:L{chunk.line_start}-L{chunk.line_end}{label}")
        return 0

    if args.command == "symbols":
        modules = build_python_symbol_map(args.path)
        if args.json:
            print(
                json.dumps(
                    {"modules": [module.to_dict() for module in modules]},
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        for module in modules:
            print(f"{module.path}:")
            if module.parse_error:
                print(f"  ! {module.parse_error}")
                continue
            for symbol in module.symbols:
                print(f"  {symbol.kind:<14} {symbol.qualified_name}  L{symbol.line_start}")
        return 0

    if args.command != "scan":
        return 2

    inventory = scan_repository(args.path, max_file_bytes=args.max_file_bytes)
    if args.json:
        print(json.dumps(inventory.to_dict(), indent=2, ensure_ascii=False))
        return 0

    languages = ", ".join(
        f"{language}={count}" for language, count in inventory.languages.items()
    ) or "none"
    print(f"Repository: {inventory.root}")
    print(f"Source files: {len(inventory.files)}")
    print(f"Lines of code: {inventory.total_lines}")
    print(f"Languages: {languages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

