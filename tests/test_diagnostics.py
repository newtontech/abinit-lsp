"""Tests for enhanced ABINIT diagnostics — TDD second batch."""

from __future__ import annotations

from pathlib import Path

from abinit_lsp.analyzer import analyze_file, analyze_path

FIXTURES = Path(__file__).parent / "fixtures"


class TestBasicDiagnostics:
    """Existing and basic diagnostic behaviors."""

    def test_valid_scf_no_errors(self) -> None:
        diags = analyze_path(FIXTURES / "si_scf.abi")
        errors = [d for d in diags if d.severity == "error"]
        assert not errors

    def test_valid_relaxation_no_errors(self) -> None:
        diags = analyze_path(FIXTURES / "relaxation.abi")
        errors = [d for d in diags if d.severity == "error"]
        assert not errors

    def test_missing_ecut_warns(self) -> None:
        diags = analyze_path(FIXTURES / "bad_missing_ecut.abi")
        codes = [d.code for d in diags]
        assert "ABINIT101" in codes

    def test_unknown_keyword_warns(self) -> None:
        diags = analyze_path(FIXTURES / "bad_unknown_keyword.abi")
        unknown = [d for d in diags if d.code == "ABINIT001"]
        assert unknown
        assert "unknownkeyword" in unknown[0].message

    def test_missing_structure_warns(self) -> None:
        diags = analyze_path(FIXTURES / "bad_structure.abi")
        codes = [d.code for d in diags]
        assert "ABINIT010" in codes

    def test_non_utf8_file_error(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.abi"
        bad.write_bytes(b"\x80\x81\x82")
        diags = analyze_path(bad)
        assert any(d.code == "ABINIT202" for d in diags)

    def test_no_supported_files_in_dir(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("hello")
        diags = analyze_path(tmp_path)
        assert any(d.code == "ABINIT201" for d in diags)

    def test_duplicate_keyword_warns(self) -> None:
        """Duplicate keywords are a common mistake."""
        diags = analyze_path(FIXTURES / "bad_duplicate.abi")
        dup = [
            d for d in diags if "duplicate" in d.message.lower() or "repeated" in d.message.lower()
        ]
        assert dup, "Expected a duplicate keyword diagnostic"

    def test_invalid_file_suffix_not_analyzed(self, tmp_path: Path) -> None:
        txt = tmp_path / "notes.txt"
        txt.write_text("ecut 30.0\n")
        diags = analyze_path(tmp_path)
        assert not diags or all("notes.txt" not in d.file for d in diags)


class TestDiagnosticStructure:
    """Diagnostics conform to expected JSON schema."""

    def test_diagnostic_has_all_fields(self) -> None:
        diags = analyze_path(FIXTURES / "bad_unknown_keyword.abi")
        assert diags
        d = diags[0]
        j = d.to_json()
        for key in ("code", "severity", "message", "file", "line"):
            assert key in j
            assert j[key] is not None

    def test_lint_json_output(self, tmp_path: Path) -> None:
        """CLI --json produces valid JSON array."""
        import json

        from abinit_lsp.cli import lint_main

        fixture = tmp_path / "test.abi"
        fixture.write_text("foo 1\n", encoding="utf-8")
        # Capture stdout
        import io
        from unittest.mock import patch

        with patch("sys.stdout", new_callable=io.StringIO) as out:
            lint_main([str(fixture), "--json"])
        data = json.loads(out.getvalue())
        assert isinstance(data, list)
        assert len(data) > 0


class TestValueValidation:
    """Validate keyword values when possible."""

    def test_ecut_negative_warns(self, tmp_path: Path) -> None:
        """ecut should be positive."""
        f = tmp_path / "test.abi"
        f.write_text("ecut -5.0\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n")
        diags = analyze_file(f)
        val_diags = [
            d
            for d in diags
            if "ecut" in d.message.lower()
            and (
                "positive" in d.message.lower()
                or "negative" in d.message.lower()
                or "range" in d.message.lower()
            )
        ]
        assert val_diags, "Expected a value validation warning for negative ecut"

    def test_natom_non_integer_warns(self, tmp_path: Path) -> None:
        """natom must be a positive integer."""
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 2.5\ntypat 1\nznucl 1\nxred 0 0 0\n")
        diags = analyze_file(f)
        val_diags = [
            d
            for d in diags
            if "natom" in d.message.lower()
            and ("integer" in d.message.lower() or "invalid" in d.message.lower())
        ]
        assert val_diags, "Expected a value validation warning for non-integer natom"

    def test_natom_zero_warns(self, tmp_path: Path) -> None:
        """natom must be positive."""
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 0\ntypat 1\nznucl 1\nxred 0 0 0\n")
        diags = analyze_file(f)
        val_diags = [
            d
            for d in diags
            if "natom" in d.message.lower()
            and ("positive" in d.message.lower() or "zero" in d.message.lower())
        ]
        assert val_diags, "Expected a value validation warning for natom=0"
