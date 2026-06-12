"""Tests for ABINIT agent API (issues #5, #8, #11, #21, #23)."""

from __future__ import annotations

import json
from pathlib import Path

from abinit_lsp.agent_api import (
    check_and_serialize,
    describe_domain_language,
    explain_rule,
    get_code_actions_json,
    get_hover,
    openqc_smoke,
    parse_abinit_log,
    parse_abinit_log_content,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestDescribeDomainLanguage:
    """Issue #5, #8: Domain language description."""

    def test_returns_dict(self) -> None:
        result = describe_domain_language()
        assert isinstance(result, dict)

    def test_has_required_fields(self) -> None:
        result = describe_domain_language()
        assert result["domain"] == "abinit"
        assert result["software"] == "abinit"
        assert "file_extensions" in result
        assert ".abi" in result["file_extensions"]
        assert "syntax" in result
        assert "keywords" in result
        assert "rules" in result

    def test_keyword_counts(self) -> None:
        result = describe_domain_language()
        assert result["keywords"]["total"] > 0
        assert result["keywords"]["documented"] > 0


class TestGetHover:
    """Issue #23: Hover documentation API."""

    def test_known_keyword(self) -> None:
        result = get_hover("ecut")
        assert result["found"] is True
        assert result["documentation"] is not None
        assert (
            "cutoff" in result["documentation"].lower()
            or "energy" in result["documentation"].lower()
        )

    def test_unknown_keyword(self) -> None:
        result = get_hover("zzzzznotreal")
        assert result["found"] is False
        assert result["documentation"] is None

    def test_case_insensitive(self) -> None:
        lower = get_hover("ecut")
        upper = get_hover("ECUT")
        assert lower["documentation"] == upper["documentation"]

    def test_dataset_keyword(self) -> None:
        result = get_hover("ecut1")
        assert result["found"] is True


class TestCheckAndSerialize:
    """Issues #5, #11: Parser-backed diagnostics with rich JSON output."""

    def test_returns_rich_payload(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 1\ntypat 1\nznucl 1\nxred 0 0 0\n")
        payload = check_and_serialize(f)
        assert "diagnostic_engine" in payload
        assert "diagnostics" in payload
        assert "ok" in payload
        assert "software" in payload
        assert payload["software"] == "abinit"

    def test_error_file_not_ok(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.abi"
        f.write_text("foobar 42\n")
        payload = check_and_serialize(f)
        assert payload["ok"] is False or len(payload["diagnostics"]) > 0

    def test_json_serializable(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 1\n")
        payload = check_and_serialize(f)
        text = json.dumps(payload, indent=2, sort_keys=True)
        parsed = json.loads(text)
        assert parsed["software"] == "abinit"


class TestGetCodeActionsJson:
    """Issue #21: Code actions JSON API."""

    def test_returns_list(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("natom 1\n")
        actions = get_code_actions_json(f)
        assert isinstance(actions, list)

    def test_action_structure(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("natom 1\n")
        actions = get_code_actions_json(f)
        if actions:
            assert "title" in actions[0]
            assert "kind" in actions[0]


class TestParseAbinitLog:
    """Issues #13, #20: Log parsing API."""

    def test_parse_file(self) -> None:
        log_path = FIXTURES / "logs" / "scf_not_converged.out"
        if log_path.exists():
            result = parse_abinit_log(log_path)
            assert isinstance(result, list)
            if result:
                assert "code" in result[0]

    def test_parse_content(self) -> None:
        content = "SCF cycle did not converge within nstep iterations\n"
        result = parse_abinit_log_content(content)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_clean_log_no_diagnostics(self) -> None:
        content = "Calculation completed successfully.\n"
        result = parse_abinit_log_content(content)
        assert result == []


class TestOpenqcSmoke:
    """Issue #7: OpenQC smoke test."""

    def test_returns_capability_status(self) -> None:
        result = openqc_smoke()
        assert result["software"] == "abinit"
        assert result["version"] == "0.1.0"
        caps = result["capabilities"]
        assert caps["lint"] is True
        assert caps["hover"] is True
        assert caps["code_actions"] is True
        assert caps["log_parser"] is True
        assert caps["agent_json"] is True

    def test_reports_rule_count(self) -> None:
        result = openqc_smoke()
        assert result["rules"]["total"] >= 8
        assert len(result["rules"]["ids"]) >= 8

    def test_reports_keyword_count(self) -> None:
        result = openqc_smoke()
        assert result["keywords"]["total"] > 0


class TestExplainRule:
    """Issue #11: Rule explanation API."""

    def test_known_rule(self) -> None:
        result = explain_rule("abinit.input.missing_ecut")
        assert result is not None
        assert result["rule_id"] == "abinit.input.missing_ecut"
        assert result["code"] == "ABINIT101"

    def test_unknown_rule(self) -> None:
        result = explain_rule("nonexistent.rule")
        assert result is None

    def test_all_rules_explainable(self) -> None:
        from abinit_lsp.lint import RULE_MANIFEST

        for rule in RULE_MANIFEST:
            result = explain_rule(rule.rule_id)
            assert result is not None, f"Missing explanation for {rule.rule_id}"
