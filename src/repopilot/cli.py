"""Command-line interface for RepoPilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .scanner import scan_repository


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
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

