from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import analyze_path, format_text


def lsp_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-lsp")
    parser.add_argument("--stdio", action="store_true", help="start the LSP server on stdio")
    args = parser.parse_args(argv)
    if not args.stdio:
        parser.error("only --stdio is currently supported")
    print(
        f"{'abinit-lsp'} scaffold: full JSON-RPC LSP is tracked in roadmap issues", file=sys.stderr
    )
    return 0


def lint_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-lint")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    diagnostics = analyze_path(args.path)
    if args.json:
        print(json.dumps([item.to_json() for item in diagnostics], indent=2, sort_keys=True))
    else:
        for item in diagnostics:
            print(
                f"{item.file}:{item.line}:{item.column}: {item.severity} {item.code} {item.message}"
            )
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def fmt_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-fmt")
    parser.add_argument("-w", "--write", action="store_true", help="write files in place")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    for path in args.files:
        formatted = format_text(path.read_text(encoding="utf-8"))
        if args.write:
            path.write_text(formatted, encoding="utf-8")
        else:
            print(formatted, end="")
    return 0


def test_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-test")
    subparsers = parser.add_subparsers(dest="command", required=True)
    static = subparsers.add_parser("static", help="run static parser/linter checks")
    static.add_argument("path", type=Path)
    static.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "static":
        return lint_main([str(args.path), *(["--json"] if args.json else [])])
    return 2
