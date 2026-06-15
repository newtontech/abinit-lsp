"""Closed-loop fixture tests for abinit-lsp.

These tests exercise the canonical fixture directories declared in
``lsp-capabilities.json`` (``tests/fixtures/{valid,invalid,logs}``) through
the agent CLI surface (``abinit-lsp-tool check`` / log parser). They are the
single-command gate that OpenQC's ``lsp:check-family`` coordinator consumes.

Issues addressed:
- #37 closed-loop fixtures, repair previews, output diagnostics, OpenQC smoke
- #36 DiagnosticEnvelope/v1 with rule IDs, severity, blocking, source
       provenance, and version scope
- #35 official-docs -> wiki -> rules -> provenance -> fixtures pipeline
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
VALID_DIR = FIXTURES / "valid"
INVALID_DIR = FIXTURES / "invalid"
LOG_DIR = FIXTURES / "logs"


def _run_tool(*args: str) -> dict:
    """Run ``abinit-lsp-tool`` and return its parsed JSON payload."""
    cmd = [sys.executable, "-m", "abinit_lsp.tool", *args]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert proc.returncode in (0, 1), proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["diagnostic_envelope"] == "v1", payload
    assert payload["software"] == "abinit", payload
    return payload


def test_canonical_fixture_directories_exist() -> None:
    """The canonical paths advertised in lsp-capabilities.json must exist."""
    for path in (VALID_DIR, INVALID_DIR, LOG_DIR):
        assert path.is_dir(), f"missing canonical fixture dir: {path}"
    # at least one fixture in each
    assert any(VALID_DIR.glob("*.abi"))
    assert any(INVALID_DIR.glob("*.abi"))
    assert any(LOG_DIR.iterdir())


@pytest.mark.parametrize(
    "fixture",
    sorted(p.name for p in VALID_DIR.glob("*.abi")),
)
def test_valid_fixtures_are_clean(fixture: str) -> None:
    """Valid fixtures produce no diagnostics (no false positives)."""
    payload = _run_tool("check", str(VALID_DIR / fixture))
    assert payload["ok"] is True, payload
    assert payload["summary"]["count"] == 0, payload["diagnostics"]


def test_missing_natom_is_blocking_error_with_provenance() -> None:
    """Invalid fixture: ABINIT102 blocking error with official source URL."""
    payload = _run_tool("check", str(INVALID_DIR / "missing_natom.abi"))
    assert payload["ok"] is False
    errors = [d for d in payload["diagnostics"] if d["code"] == "ABINIT102"]
    assert errors, payload["diagnostics"]
    diag = errors[0]
    assert diag["severity"] == "error"
    assert diag["blocking"] is True
    prov = diag.get("source_provenance") or {}
    assert prov.get("kind") == "official_docs"
    assert prov.get("url") == "https://docs.abinit.org/variables/natom/"
    assert diag.get("manual_ref") == "https://docs.abinit.org/variables/natom/"


def test_inconsistent_typat_znucl_is_blocking_error() -> None:
    """Invalid fixture: ABINIT103 blocking error with typat source URL."""
    payload = _run_tool("check", str(INVALID_DIR / "inconsistent_typat_znucl.abi"))
    assert payload["ok"] is False
    errors = [d for d in payload["diagnostics"] if d["code"] == "ABINIT103"]
    assert errors, payload["diagnostics"]
    diag = errors[0]
    assert diag["severity"] == "error"
    assert diag["blocking"] is True
    prov = diag.get("source_provenance") or {}
    assert prov.get("url") == "https://docs.abinit.org/variables/typat/"


def test_loose_tolerance_is_non_blocking_warning() -> None:
    """Invalid fixture: ABINIT106 warning that does NOT block the gate."""
    payload = _run_tool("check", str(INVALID_DIR / "loose_tolerance.abi"))
    # warnings exist but ok is True because nothing blocks
    warnings = [d for d in payload["diagnostics"] if d["code"] == "ABINIT106"]
    assert warnings, payload["diagnostics"]
    assert all(d["severity"] == "warning" for d in warnings)
    assert all(d["blocking"] is False for d in warnings)
    assert payload["ok"] is True, payload
    for diag in warnings:
        prov = diag.get("source_provenance") or {}
        assert prov.get("url") == "https://docs.abinit.org/variables/toldfe/"


def test_unknown_keyword_is_non_blocking_warning() -> None:
    """Invalid fixture: ABINIT107 warning for unknown keyword."""
    payload = _run_tool("check", str(INVALID_DIR / "unknown_keyword.abi"))
    warnings = [d for d in payload["diagnostics"] if d["code"] == "ABINIT107"]
    assert warnings, payload["diagnostics"]
    diag = warnings[0]
    assert diag["severity"] == "warning"
    assert diag["blocking"] is False
    prov = diag.get("source_provenance") or {}
    assert prov.get("kind") == "official_docs"
    assert prov.get("url") == "https://docs.abinit.org/variables/"


def test_fix_operation_returns_action_plan() -> None:
    """``fix`` returns a preview patch / action plan, not a destructive edit."""
    payload = _run_tool("fix", str(INVALID_DIR / "missing_natom.abi"))
    # fix is documented as a preview/action plan; we only assert it returns
    # the stable envelope and does not crash.
    assert payload["operation"] == "fix"
    assert "diagnostics" in payload


def test_log_fixture_emits_runtime_diagnostic() -> None:
    """Runtime log fixture yields ABINIT200 SCF convergence diagnostic."""
    from abinit_lsp.log_parser import parse_log_file

    diagnostics = parse_log_file(LOG_DIR / "scf_not_converged.out")
    assert diagnostics, "expected at least one log diagnostic"
    diag = diagnostics[0].to_json()
    assert diag["code"] == "ABINIT200"
    assert diag["severity"] == "error"
    assert diag["source_provenance"], "log diagnostic must carry provenance"
    assert diag["source_provenance"]["url"] == "https://docs.abinit.org/tutorial/base1/"


def test_capabilities_payload_advertises_canonical_fixture_paths() -> None:
    """lsp-capabilities.json must advertise the canonical fixture dirs."""
    capabilities = json.loads((REPO_ROOT / "lsp-capabilities.json").read_text())
    fixture_paths = capabilities["fixturePaths"]
    assert "tests/fixtures/valid" in fixture_paths["valid"]
    assert "tests/fixtures/invalid" in fixture_paths["invalid"]
    assert "tests/fixtures/logs" in fixture_paths["logs"]


def test_rule_manifest_carries_provenance_for_every_rule() -> None:
    """Every rule in the manifest must trace to an official source URL."""
    from abinit_lsp.lint import get_rule_manifest

    manifest = get_rule_manifest()
    assert manifest, "rule manifest must not be empty"
    for entry in manifest:
        assert entry.get("source_provenance"), entry
        url = entry["source_provenance"].get("url", "")
        assert url.startswith("https://docs.abinit.org/"), entry
        assert entry.get("manual_ref"), entry
        assert "blocking" in entry, entry


def test_openqc_compatibility_report_exists_and_references_fixtures() -> None:
    """The OpenQC compatibility report must be present and up-to-date."""
    report = REPO_ROOT / "diagnostics" / "openqc-compatibility.md"
    assert report.is_file(), "missing diagnostics/openqc-compatibility.md"
    text = report.read_text(encoding="utf-8")
    # each canonical fixture must be referenced
    for fixture in (
        "tests/fixtures/valid/silicon_scf.abi",
        "tests/fixtures/invalid/missing_natom.abi",
        "tests/fixtures/logs/scf_not_converged.out",
    ):
        assert fixture in text, f"openqc report missing reference: {fixture}"
    # Blocking policy table must list ABINIT102 as a blocker
    assert "ABINIT102" in text
