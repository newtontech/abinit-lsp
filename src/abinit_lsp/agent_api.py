"""Agent-facing API for ABINIT LSP capabilities.

Provides a unified JSON interface for:
- Rule manifest export (issue #5, #8, #11)
- Parser-backed diagnostics (issue #5)
- Code actions (issue #21)
- Hover documentation (issue #23)
- Log parsing (issue #13, #20)
- OpenQC smoke test (issue #7)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .code_actions import get_code_actions
from .completion import ALL_KEYWORDS, KEYWORD_DOCS
from .hover import get_hover_docs
from .lint import get_rule_manifest, lint_path
from .log_parser import parse_log, parse_log_file
from .rich_diagnostics import agent_check_payload

SOFTWARE = "abinit"


def describe_domain_language() -> dict[str, Any]:
    """Return a description of the ABINIT domain language.

    Used by agents and IDEs to understand the ABINIT input format.
    """
    return {
        "domain": "abinit",
        "software": SOFTWARE,
        "file_extensions": [".abi", ".abinit", ".in"],
        "syntax": {
            "format": "free-form key-value pairs",
            "comment_prefixes": ["#", "!", ";"],
            "separator": "space or equals",
            "multiline_arrays": True,
            "dataset_suffixes": True,
            "star_notation": True,
        },
        "keywords": {
            "total": len(ALL_KEYWORDS),
            "documented": len(KEYWORD_DOCS),
        },
        "rules": {
            "total": len(get_rule_manifest()),
        },
    }


def get_hover(keyword: str) -> dict[str, Any]:
    """Return hover documentation for a keyword (issue #23).

    Args:
        keyword: The ABINIT keyword to look up.

    Returns:
        Dict with 'keyword', 'documentation', and 'found' keys.
    """
    docs = get_hover_docs(keyword)
    return {
        "keyword": keyword,
        "documentation": docs,
        "found": docs is not None,
    }


def check_and_serialize(path: Path) -> dict[str, Any]:
    """Run parser-backed lint and return rich JSON payload (issues #5, #11).

    Combines lint diagnostics with the Diagnostic Engine v1 serialization.
    """
    path = Path(path)
    diagnostics = lint_path(path)
    return agent_check_payload(
        software=SOFTWARE,
        uri=path.resolve().as_uri(),
        operation="check",
        diagnostics=diagnostics,
        path=str(path),
        file_type=_file_type(path),
    )


def get_code_actions_json(path: Path) -> list[dict[str, Any]]:
    """Return code actions as JSON-serializable list (issue #21)."""
    actions = get_code_actions(path)
    return [a.to_json() for a in actions]


def parse_abinit_log(path: Path) -> list[dict[str, Any]]:
    """Parse an ABINIT log file and return diagnostics as JSON (issues #13, #20)."""
    diagnostics = parse_log_file(path)
    return [d.to_json() for d in diagnostics]


def parse_abinit_log_content(content: str) -> list[dict[str, Any]]:
    """Parse ABINIT log content string and return diagnostics as JSON."""
    diagnostics = parse_log(content, Path("<log>"))
    return [d.to_json() for d in diagnostics]


def openqc_smoke() -> dict[str, Any]:
    """OpenQC smoke test endpoint (issue #7).

    Returns capability status for each feature.
    """
    manifest = get_rule_manifest()
    return {
        "software": SOFTWARE,
        "version": "0.1.0",
        "capabilities": {
            "lint": True,
            "format": True,
            "completion": True,
            "hover": True,
            "code_actions": True,
            "log_parser": True,
            "agent_json": True,
        },
        "rules": {
            "total": len(manifest),
            "ids": [r["rule_id"] for r in manifest],
        },
        "keywords": {
            "total": len(ALL_KEYWORDS),
            "documented": len(KEYWORD_DOCS),
        },
    }


def explain_rule(rule_id: str) -> dict[str, Any] | None:
    """Explain a specific rule by its rule_id (issue #11).

    Returns rule metadata or None if not found.
    """
    for r in get_rule_manifest():
        if r["rule_id"] == rule_id:
            return r
    return None


def _file_type(path: Path) -> str:
    """Determine file type from path."""
    name = path.name.upper()
    if "." in path.name:
        return path.suffix.lstrip(".").lower()
    return name.lower()
