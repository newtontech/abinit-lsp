"""Agent-facing CLI for Diagnostic Engine v1 operations.

LLM Wiki: wiki/synthesis/openqc-agent-context.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent_operations import operation_path, with_capabilities
from .rich_diagnostics import agent_check_payload

SOFTWARE = "abinit"


def _capabilities_payload() -> dict[str, Any]:
    for parent in Path(__file__).resolve().parents:
        manifest_path = parent / "lsp-capabilities.json"
        if manifest_path.exists():
            payload: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
            return payload
    return {
        "schema": "OpenQCLspCapabilities",
        "version": 1,
        "software": SOFTWARE,
        "capabilities": [
            "diagnostics",
            "rich-diagnostics",
            "completion",
            "hover",
            "symbols",
            "fix-preview",
            "llm-wiki",
            "openqc-context",
            "preflight",
        ],
        "agentCli": {
            "operations": [
                "capabilities",
                "check",
                "preflight",
                "manifest",
                "context",
                "complete",
                "hover",
                "symbols",
                "fix",
            ],
            "jsonFormat": True,
            "failOnBlocking": True,
        },
    }


def _file_type(path: Path) -> str:
    name = path.name.upper()
    if name in {"INCAR", "POSCAR", "KPOINTS", "POTCAR", "CONTCAR"}:
        return name
    if "." in path.name:
        return path.suffix.lstrip(".").lower()
    return name.lower()


def _collect_diagnostics(path: Path) -> list[Any]:
    if path.is_file() and path.suffix.lower() in {".log", ".out"}:
        from .log_parser import parse_log_file

        return list(parse_log_file(path))

    from .lint import lint_path

    return list(lint_path(path))


def _load_intent(path: Path) -> dict[str, Any] | None:
    """Load the optional preflight intent contract for a case directory.

    The intent contract is the only place preflight policy overrides live
    (e.g. ``software_version``, ``ecut_warning_ha``,
    ``high_accuracy_production``). It is a workspace-local artifact, never a
    MatMaster/Bohrium runtime concept.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    case_dir = path if path.is_dir() else path.parent
    intent_path = case_dir / ".abinit-lsp" / "intent.json"
    if not intent_path.exists():
        return None
    try:
        data = json.loads(intent_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _looks_like_workspace(case_dir: Path) -> bool:
    """True when a directory is a real generated-input workspace.

    Preflight needs at least a primary ``.abi`` input to build a meaningful
    cross-artifact graph. A directory with no recognized input keeps the
    legacy single-file lint path so callers that lint one file at a time are
    unaffected.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    if not case_dir.is_dir():
        return False
    for pattern in ("*.abi", "*.abinit", "*.in"):
        for _ in case_dir.glob(pattern):
            return True
    return False


def _collect_preflight(
    path: Path, intent: dict[str, Any] | None
) -> tuple[list[Any], list[dict[str, Any]], dict[str, Any]]:
    """Return (preflight_diagnostics, artifact_graph, version_assumption).

    Imported lazily so callers that never touch preflight (e.g. single-file
    LSP hover) pay no import cost.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    from .preflight import preflight_diagnostics, resolve_version_assumption

    case_dir = path if path.is_dir() else path.parent
    diagnostics, graph = preflight_diagnostics(case_dir, intent=intent)
    version_assumption = resolve_version_assumption(intent)
    return diagnostics, graph.to_json(), version_assumption


def check_path(path: Path) -> dict[str, Any]:
    uri = path.resolve().as_uri()
    intent = _load_intent(path)
    diagnostics = _collect_diagnostics(path)
    # Universal preflight diagnostics augment the legacy lint output, but only
    # when the caller passes a *case directory*. A bare single input file
    # keeps the legacy single-file behavior so existing consumers that lint
    # one input at a time are unaffected (ABINIT inputs are single files, so
    # there is no cross-file graph to build for an isolated file path).
    artifacts: list[dict[str, Any]] = []
    version_assumption: dict[str, Any] | None = None
    if path.is_dir() and _looks_like_workspace(path):
        preflight, artifacts, version_assumption = _collect_preflight(path, intent)
        diagnostics.extend(preflight)
    payload = agent_check_payload(
        software=SOFTWARE,
        uri=uri,
        operation="check",
        diagnostics=diagnostics,
        path=str(path),
        file_type=_file_type(path),
        intent=intent,
        version_assumption=version_assumption,
        artifacts=artifacts,
    )
    return payload


def preflight_path(path: Path) -> dict[str, Any]:
    """Return a preflight-only payload (universal checks, no legacy lint).

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    from .preflight import preflight_diagnostics, resolve_version_assumption

    intent = _load_intent(path)
    case_dir = path if path.is_dir() else path.parent
    diagnostics, graph = preflight_diagnostics(case_dir, intent=intent)
    version_assumption = resolve_version_assumption(intent)
    payload = agent_check_payload(
        software=SOFTWARE,
        uri=case_dir.resolve().as_uri(),
        operation="preflight",
        diagnostics=diagnostics,
        path=str(case_dir),
        file_type="case-dir",
        intent=intent,
        version_assumption=version_assumption,
        artifacts=graph.to_json(),
    )
    return with_capabilities(payload, "preflight")


def manifest_path(path: Path | None = None) -> dict[str, Any]:
    """Return the fleet preflight manifest.

    When ``path`` is given, fixture expectations declared in
    ``.abinit-lsp/fixtures.json`` are merged in so the parent probe can confirm
    a case directory exercises the documented codes.

    LLM Wiki: wiki/synthesis/openqc-agent-context.md
    """
    from .preflight import fleet_manifest

    fixtures: list[dict[str, Any]] = []
    if path is not None:
        case_dir = path if path.is_dir() else path.parent
        fixtures_path = case_dir / ".abinit-lsp" / "fixtures.json"
        if fixtures_path.exists():
            try:
                data = json.loads(fixtures_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = None
            if isinstance(data, list):
                fixtures = [item for item in data if isinstance(item, dict)]
            elif isinstance(data, dict) and isinstance(data.get("fixtures"), list):
                fixtures = [item for item in data["fixtures"] if isinstance(item, dict)]
    return fleet_manifest(fixtures=fixtures)


def _operation_payload(
    path: Path,
    operation: str,
    line: int = 0,
    character: int = 0,
) -> dict[str, Any]:
    return operation_path(
        path,
        operation,
        software=SOFTWARE,
        file_type_func=_file_type,
        collect_diagnostics=_collect_diagnostics,
        line=line,
        character=character,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abinit-lsp-tool")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    capabilities = subparsers.add_parser("capabilities")
    capabilities.add_argument("--format", choices=["json"], default="json")
    for operation in (
        "check",
        "preflight",
        "manifest",
        "context",
        "complete",
        "hover",
        "symbols",
        "fix",
    ):
        sub = subparsers.add_parser(operation)
        if operation == "manifest":
            sub.add_argument(
                "path",
                type=Path,
                nargs="?",
                help="Optional case directory to merge fixture expectations from.",
            )
        else:
            sub.add_argument("path", type=Path)
        sub.add_argument("--format", choices=["json"], default="json")
        sub.add_argument(
            "--line",
            type=int,
            default=0,
            help="0-based line for position-aware operations.",
        )
        sub.add_argument(
            "--character",
            type=int,
            default=0,
            help="0-based character for position-aware operations.",
        )
        if operation in {"check", "preflight"}:
            sub.add_argument("--fail-on-blocking", action="store_true")
    args = parser.parse_args(argv)

    if args.operation == "capabilities":
        print(json.dumps(_capabilities_payload(), indent=2, sort_keys=True))
        return 0
    if args.operation == "check":
        payload = with_capabilities(check_path(args.path), "check")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    if args.operation == "preflight":
        payload = preflight_path(args.path)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1 if getattr(args, "fail_on_blocking", False) and not payload["ok"] else 0
    if args.operation == "manifest":
        payload = manifest_path(getattr(args, "path", None))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    payload = _operation_payload(args.path, args.operation, args.line, args.character)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
