from __future__ import annotations

from abinit_lsp.rich_diagnostics import (
    DIAGNOSTIC_CATEGORIES,
    agent_check_payload,
    diagnostic_to_dict,
)


def test_diagnostic_engine_v1_contract_shape() -> None:
    payload = agent_check_payload(
        software="abinit",
        uri="file:///tmp/input",
        diagnostics=[],
    )
    assert payload["diagnostic_engine"] == "1.0"
    assert payload["ok"] is True
    assert payload["diagnostics"] == []
    assert set(DIAGNOSTIC_CATEGORIES) >= {"syntax", "schema", "type/value"}


def test_legacy_diagnostic_is_enriched() -> None:
    diagnostic = {
        "code": "ABINIT001",
        "severity": "error",
        "message": "unknown keyword",
        "line": 2,
        "column": 3,
        "source": "abinit-lsp",
    }
    item = diagnostic_to_dict(diagnostic, software="abinit", path="input")
    assert item["severity"] == "error"
    assert item["category"] == "schema"
    assert item["blocking"] is True
    assert item["range"]["start"] == {"line": 1, "character": 2}
    assert item["fix_hints"] == []
