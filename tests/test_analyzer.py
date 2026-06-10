from __future__ import annotations

from pathlib import Path

from abinit_lsp.analyzer import analyze_path, format_text


def test_valid_fixture_has_no_errors(tmp_path: Path) -> None:
    fixture = tmp_path / "run.abi"
    fixture.write_text(
        "ecut 30\nnatom 2\ntypat 1 1\nznucl 14\nxred 0 0 0 0.25 0.25 0.25\n", encoding="utf-8"
    )

    diagnostics = analyze_path(tmp_path)

    assert not [item for item in diagnostics if item.severity == "error"]


def test_invalid_fixture_reports_diagnostic(tmp_path: Path) -> None:
    fixture = tmp_path / "bad.abi"
    fixture.write_text("foo 1\n", encoding="utf-8")

    diagnostics = analyze_path(tmp_path)

    assert diagnostics


def test_formatter_is_idempotent() -> None:
    first = format_text("ecut 30\nnatom 2\ntypat 1 1\nznucl 14\nxred 0 0 0 0.25 0.25 0.25\n")
    second = format_text(first)

    assert second == first
