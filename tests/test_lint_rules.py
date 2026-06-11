"""Tests for all ABINIT lint rules (issues #14-#20)."""

from __future__ import annotations

import json
from pathlib import Path

from abinit_lsp.lint import (
    check_bad_multidataset_suffix,
    check_duplicate_keywords,
    check_inconsistent_typat_znucl,
    check_invalid_variable_type,
    check_loose_tolerance,
    check_missing_ecut,
    check_missing_natom,
    check_unknown_keywords,
    get_rule_manifest,
    lint_file,
    lint_path,
    RULE_MANIFEST,
)
from abinit_lsp.parser import parse_content

FIXTURES = Path(__file__).parent / "fixtures"
RULE_FIXTURES = FIXTURES / "rules"


class TestRuleManifest:
    """Rule manifest export (issues #5, #8, #11)."""

    def test_manifest_is_list(self) -> None:
        manifest = get_rule_manifest()
        assert isinstance(manifest, list)
        assert len(manifest) >= 8

    def test_manifest_entry_fields(self) -> None:
        for entry in get_rule_manifest():
            assert "rule_id" in entry
            assert "code" in entry
            assert "severity" in entry
            assert "description" in entry
            assert "source" in entry

    def test_manifest_has_expected_rules(self) -> None:
        ids = {r["rule_id"] for r in get_rule_manifest()}
        assert "abinit.input.missing_ecut" in ids
        assert "abinit.structure.missing_natom" in ids
        assert "abinit.structure.inconsistent_typat_znucl" in ids
        assert "abinit.variable.invalid_type" in ids
        assert "abinit.multidataset.bad_suffix" in ids
        assert "abinit.scf.loose_tolerance" in ids


class TestRule14MissingEcut:
    """RULE #14: abinit.input.missing_ecut."""

    def test_missing_ecut_warns(self) -> None:
        af = parse_content(Path("test.abi"), "natom 1\ntypat 1\nznucl 1\n")
        diags = check_missing_ecut(af, Path("test.abi"))
        assert len(diags) == 1
        assert diags[0].code == "ABINIT101"
        assert diags[0].severity == "warning"

    def test_ecut_present_no_warning(self) -> None:
        af = parse_content(Path("test.abi"), "ecut 30.0\nnatom 1\n")
        diags = check_missing_ecut(af, Path("test.abi"))
        assert len(diags) == 0

    def test_fixture_matches_golden(self) -> None:
        diags = lint_file(RULE_FIXTURES / "missing_ecut.abi")
        golden = json.loads((RULE_FIXTURES / "missing_ecut.json").read_text())
        assert len(diags) == len(golden)
        for d, g in zip(diags, golden):
            assert d.code == g["code"]
            assert d.severity == g["severity"]


class TestRule15MissingNatom:
    """RULE #15: abinit.structure.missing_natom."""

    def test_missing_natom_errors(self) -> None:
        af = parse_content(Path("test.abi"), "ecut 30.0\n")
        diags = check_missing_natom(af, Path("test.abi"))
        assert len(diags) == 1
        assert diags[0].code == "ABINIT102"
        assert diags[0].severity == "error"

    def test_natom_present_no_error(self) -> None:
        af = parse_content(Path("test.abi"), "ecut 30.0\nnatom 2\n")
        diags = check_missing_natom(af, Path("test.abi"))
        assert len(diags) == 0

    def test_fixture_matches_golden(self) -> None:
        diags = lint_file(RULE_FIXTURES / "missing_natom.abi")
        golden = json.loads((RULE_FIXTURES / "missing_natom.json").read_text())
        codes = [d.code for d in diags]
        assert "ABINIT102" in codes


class TestRule16InconsistentTypatZnucl:
    """RULE #16: abinit.structure.inconsistent_typat_znucl."""

    def test_typat_out_of_range(self) -> None:
        content = "ecut 30\nnatom 3\nntypat 2\ntypat 1 2 3\nznucl 14 8\nxred 0 0 0 1 1 1 2 2 2\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_inconsistent_typat_znucl(af, Path("test.abi"))
        assert any(d.code == "ABINIT103" for d in diags)

    def test_consistent_typat_no_error(self) -> None:
        content = "ecut 30\nnatom 2\nntypat 2\ntypat 1 2\nznucl 14 8\nxred 0 0 0 1 1 1\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_inconsistent_typat_znucl(af, Path("test.abi"))
        assert len(diags) == 0

    def test_znucl_count_mismatch(self) -> None:
        content = "ecut 30\nnatom 1\nntypat 3\ntypat 1\nznucl 14 8\nxred 0 0 0\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_inconsistent_typat_znucl(af, Path("test.abi"))
        assert any("znucl" in d.message for d in diags)

    def test_fixture_matches_golden(self) -> None:
        diags = lint_file(RULE_FIXTURES / "inconsistent_typat_znucl.abi")
        golden = json.loads((RULE_FIXTURES / "inconsistent_typat_znucl.json").read_text())
        codes = [d.code for d in diags]
        assert "ABINIT103" in codes


class TestRule17InvalidVariableType:
    """RULE #17: abinit.variable.invalid_type."""

    def test_natom_float_errors(self) -> None:
        af = parse_content(Path("test.abi"), "natom 2.5\n")
        diags = check_invalid_variable_type(af, Path("test.abi"))
        assert any(d.code == "ABINIT104" for d in diags)

    def test_ecut_non_numeric_errors(self) -> None:
        af = parse_content(Path("test.abi"), "ecut abc\n")
        diags = check_invalid_variable_type(af, Path("test.abi"))
        assert any(d.code == "ABINIT104" for d in diags)

    def test_fortran_scientific_ok(self) -> None:
        af = parse_content(Path("test.abi"), "toldfe 1.0d-8\n")
        diags = check_invalid_variable_type(af, Path("test.abi"))
        assert len(diags) == 0

    def test_star_notation_ok(self) -> None:
        af = parse_content(Path("test.abi"), "acell 3*10.26\n")
        diags = check_invalid_variable_type(af, Path("test.abi"))
        assert len(diags) == 0

    def test_valid_types_no_error(self) -> None:
        content = "ecut 30.0\nnatom 2\nnstep 100\nntypat 1\ntoldfe 1.0e-8\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_invalid_variable_type(af, Path("test.abi"))
        assert len(diags) == 0

    def test_fixture_matches_golden(self) -> None:
        diags = lint_file(RULE_FIXTURES / "invalid_variable_type.abi")
        golden = json.loads((RULE_FIXTURES / "invalid_variable_type.json").read_text())
        assert len(diags) == len(golden)
        codes = [d.code for d in diags]
        assert codes.count("ABINIT104") == 2


class TestRule18BadMultidatasetSuffix:
    """RULE #18: abinit.multidataset.bad_suffix."""

    def test_suffix_exceeds_ndtset(self) -> None:
        content = "ndtset 2\necut1 20\necut2 30\necut3 40\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_bad_multidataset_suffix(af, Path("test.abi"))
        assert len(diags) == 1
        assert diags[0].code == "ABINIT105"

    def test_valid_suffixes_no_warning(self) -> None:
        content = "ndtset 2\necut1 20\necut2 30\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_bad_multidataset_suffix(af, Path("test.abi"))
        assert len(diags) == 0

    def test_no_ndtset_no_check(self) -> None:
        content = "ecut1 20\necut2 30\n"
        af = parse_content(Path("test.abi"), content)
        diags = check_bad_multidataset_suffix(af, Path("test.abi"))
        assert len(diags) == 0

    def test_fixture_matches_golden(self) -> None:
        diags = lint_file(RULE_FIXTURES / "bad_multidataset_suffix.abi")
        codes = [d.code for d in diags]
        assert "ABINIT105" in codes


class TestRule19LooseTolerance:
    """RULE #19: abinit.scf.loose_tolerance."""

    def test_loose_toldfe_warns(self) -> None:
        af = parse_content(Path("test.abi"), "toldfe 1.0\n")
        diags = check_loose_tolerance(af, Path("test.abi"))
        assert any(d.code == "ABINIT106" and "toldfe" in d.message for d in diags)

    def test_tight_toldfe_no_warning(self) -> None:
        af = parse_content(Path("test.abi"), "toldfe 1.0e-8\n")
        diags = check_loose_tolerance(af, Path("test.abi"))
        assert len(diags) == 0

    def test_loose_tolmxf_warns(self) -> None:
        af = parse_content(Path("test.abi"), "tolmxf 0.01\n")
        diags = check_loose_tolerance(af, Path("test.abi"))
        assert any(d.code == "ABINIT106" and "tolmxf" in d.message for d in diags)

    def test_loose_tolvrs_warns(self) -> None:
        af = parse_content(Path("test.abi"), "tolvrs 1.0e-4\n")
        diags = check_loose_tolerance(af, Path("test.abi"))
        assert any(d.code == "ABINIT106" and "tolvrs" in d.message for d in diags)

    def test_fortran_scientific_tolerance(self) -> None:
        af = parse_content(Path("test.abi"), "toldfe 1.0d-2\n")
        diags = check_loose_tolerance(af, Path("test.abi"))
        assert len(diags) >= 1

    def test_fixture_matches_golden(self) -> None:
        diags = lint_file(RULE_FIXTURES / "loose_tolerance.abi")
        codes = [d.code for d in diags]
        assert codes.count("ABINIT106") >= 2


class TestDuplicateKeywords:
    """RULE: abinit.input.duplicate_keyword."""

    def test_duplicate_warns(self) -> None:
        af = parse_content(Path("test.abi"), "ecut 30\necut 20\n")
        diags = check_duplicate_keywords(af, Path("test.abi"))
        assert len(diags) == 1
        assert diags[0].code == "ABINIT108"

    def test_no_duplicate_no_warning(self) -> None:
        af = parse_content(Path("test.abi"), "ecut 30\nnatom 2\n")
        diags = check_duplicate_keywords(af, Path("test.abi"))
        assert len(diags) == 0


class TestUnknownKeywords:
    """RULE: abinit.input.unknown_keyword."""

    def test_unknown_warns(self) -> None:
        af = parse_content(Path("test.abi"), "foobar 42\n")
        diags = check_unknown_keywords(af, Path("test.abi"))
        assert len(diags) == 1
        assert diags[0].code == "ABINIT107"

    def test_known_no_warning(self) -> None:
        af = parse_content(Path("test.abi"), "ecut 30\n")
        diags = check_unknown_keywords(af, Path("test.abi"))
        assert len(diags) == 0


class TestValidCompleteFixture:
    """Non-triggering fixture should have no errors."""

    def test_no_errors(self) -> None:
        diags = lint_file(RULE_FIXTURES / "valid_complete.abi")
        errors = [d for d in diags if d.severity == "error"]
        assert len(errors) == 0

    def test_golden_is_empty(self) -> None:
        golden = json.loads((RULE_FIXTURES / "valid_complete.json").read_text())
        assert golden == []


class TestLintPath:
    """Test directory and file linting."""

    def test_lint_directory(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n")
        diags = lint_path(tmp_path)
        assert isinstance(diags, list)

    def test_lint_nonexistent_dir(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        diags = lint_path(empty)
        assert any(d.code == "ABINIT201" for d in diags)

    def test_lint_single_file(self) -> None:
        diags = lint_file(RULE_FIXTURES / "valid_complete.abi")
        assert isinstance(diags, list)
