from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .lint import lint_path


def lsp_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-lsp")
    parser.add_argument("--stdio", action="store_true", help="start the LSP server on stdio")
    args = parser.parse_args(argv)
    if not args.stdio:
        parser.error("only --stdio is currently supported")
    # Issue #7: stdio JSON-RPC smoke path
    # Read JSON-RPC messages from stdin and respond on stdout
    _stdio_smoke()
    return 0


def _stdio_smoke() -> None:
    """Minimal stdio JSON-RPC smoke implementation.

    Reads Content-Length framed JSON-RPC messages from stdin,
    responds to initialize and textDocument/diagnostic requests.
    Other messages receive empty responses.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    print("abinit-lsp: stdio JSON-RPC smoke path active", file=sys.stderr)

    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            if line.startswith("Content-Length:"):
                length = int(line.split(":")[1].strip())
                # Read the blank line separator
                sys.stdin.readline()
                # Read the JSON body
                body = sys.stdin.read(length)
                try:
                    msg = json.loads(body)
                except json.JSONDecodeError:
                    continue
                response = _handle_rpc(msg)
                if response is not None:
                    _send_response(response)
            elif line.strip():
                # Try to parse as bare JSON (for testing)
                try:
                    msg = json.loads(line)
                    response = _handle_rpc(msg)
                    if response is not None:
                        _send_response(response)
                except json.JSONDecodeError:
                    pass
            if line.strip() == "":
                break
    except (EOFError, KeyboardInterrupt, OSError):
        pass


def _handle_rpc(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Handle a single JSON-RPC message.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "capabilities": {
                    "textDocumentSync": 1,
                    "completionProvider": {"triggerCharacters": []},
                    "hoverProvider": True,
                    "codeActionProvider": True,
                },
                "serverInfo": {
                    "name": "abinit-lsp",
                    "version": __version__,
                },
            },
        }

    if method == "initialized":
        return None  # notification, no response

    if method == "shutdown":
        return {"jsonrpc": "2.0", "id": msg_id, "result": None}

    if method == "exit":
        return None

    if method == "textDocument/diagnostic":
        uri = params.get("textDocument", {}).get("uri", "")
        path_str = uri.replace("file://", "")
        path = Path(path_str)
        from .agent_api import check_and_serialize

        try:
            payload = check_and_serialize(path)
        except Exception:
            payload = {"diagnostics": []}
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "kind": "full",
                "items": payload.get("diagnostics", []),
            },
        }

    # Unknown method - return empty result
    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "result": None}
    return None


def _send_response(response: dict[str, Any]) -> None:
    """Send a JSON-RPC response with Content-Length framing.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    body = json.dumps(response)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    sys.stdout.write(header)
    sys.stdout.write(body)
    sys.stdout.flush()


def lint_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-lint")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    diagnostics = lint_path(args.path)
    if args.json:
        print(json.dumps([item.to_json() for item in diagnostics], indent=2, sort_keys=True))
    else:
        for item in diagnostics:
            print(
                f"{item.file}:{item.line}:{item.column}: {item.severity} {item.code} {item.message}"
            )
    return 1 if any(item.severity == "error" for item in diagnostics) else 0


def fmt_main(argv: list[str] | None = None) -> int:
    from .analyzer import format_text

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
