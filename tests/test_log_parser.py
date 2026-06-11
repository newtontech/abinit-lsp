"""Tests for ABINIT log parser (issues #13, #20)."""

from __future__ import annotations

import json
from pathlib import Path

from abinit_lsp.log_parser import parse_log, parse_log_file

FIXTURES = Path(__file__).parent / "fixtures"
LOG_FIXTURES = FIXTURES / "logs"
RULE_FIXTURES = FIXTURES / "rules"


class TestScfNotConverged:
    """RULE #20: abinit.log.scf_not_converged."""

    def test_scf_not_converged_pattern(self) -> None:
        content = "SCF cycle did not converge within nstep iterations\n"
        diags = parse_log(content, Path("test.out"))
        assert len(diags) >= 1
        assert diags[0].code == "ABINIT200"
        assert diags[0].severity == "error"

    def test_scf_not_converged_fixture(self) -> None:
        diags = parse_log_file(LOG_FIXTURES / "scf_not_converged.out")
        assert len(diags) >= 1
        assert any(d.code == "ABINIT200" for d in diags)

    def test_golden_matches(self) -> None:
        diags = parse_log_file(LOG_FIXTURES / "scf_not_converged.out")
        golden = json.loads((RULE_FIXTURES / "log_scf_not_converged.json").read_text())
        assert len(diags) == len(golden)
        for d, g in zip(diags, golden):
            assert d.code == g["code"]
            assert d.severity == g["severity"]

    def test_converged_log_no_error(self) -> None:
        content = """ ETOT 10  -7.9568372943633    -0.0000  1.234E-08
 At SCF step   10       vres2   =   1.23E-10 < tolvrs=  1.00E-08 =>converged
"""
        diags = parse_log(content, Path("test.out"))
        assert not any(d.code == "ABINIT200" for d in diags)

    def test_empty_log(self) -> None:
        diags = parse_log("", Path("test.out"))
        assert diags == []


class TestRuntimeErrors:
    """General ABINIT runtime error patterns."""

    def test_fatal_error(self) -> None:
        content = " Fatal error encountered. Stopping.\n"
        diags = parse_log(content, Path("test.out"))
        assert any(d.code == "ABINIT201" for d in diags)

    def test_allocation_error(self) -> None:
        content = "Allocation error: not enough memory\n"
        diags = parse_log(content, Path("test.out"))
        assert any(d.code == "ABINIT201" for d in diags)

    def test_file_not_found(self) -> None:
        content = "  Pseudopotential file not found: si.psp8\n"
        diags = parse_log(content, Path("test.out"))
        assert any(d.code == "ABINIT201" for d in diags)

    def test_clean_run_no_errors(self) -> None:
        content = """ .Version 10.0.5 of ABINIT

---SELF-CONSISTENT-FIELD CONVERGENCE--------------------------------------------
 ETOT 1  -7.7996042943633    -7.7996  2.509E+00

 Calculation completed successfully.
"""
        diags = parse_log(content, Path("test.out"))
        assert len(diags) == 0

    def test_parse_log_file_nonexistent(self) -> None:
        diags = parse_log_file(Path("/nonexistent/file.out"))
        assert diags == []


class TestLogParserDiagnostics:
    """Diagnostic structure for log parser output."""

    def test_diagnostic_has_required_fields(self) -> None:
        content = "SCF cycle did not converge within nstep iterations\n"
        diags = parse_log(content, Path("test.out"))
        assert diags
        d = diags[0]
        j = d.to_json()
        for key in ("code", "severity", "message", "file", "line"):
            assert key in j
            assert j[key] is not None

    def test_evidence_includes_source_line(self) -> None:
        content = "SCF cycle did not converge within nstep iterations\n"
        diags = parse_log(content, Path("test.out"))
        assert diags
        assert len(diags[0].evidence) > 0

    def test_suggested_fix_provides_hints(self) -> None:
        content = "SCF cycle did not converge within nstep iterations\n"
        diags = parse_log(content, Path("test.out"))
        assert diags
        fix = diags[0].suggested_fix
        assert fix is not None
        assert "hints" in fix
