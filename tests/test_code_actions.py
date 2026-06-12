"""Tests for ABINIT code actions (issue #21)."""

from __future__ import annotations

from pathlib import Path

from abinit_lsp.code_actions import get_code_actions


class TestCodeActions:
    """Code actions for ABINIT diagnostics."""

    def test_missing_ecut_produces_add_action(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("natom 1\ntypat 1\nznucl 1\nxred 0 0 0\n")
        actions = get_code_actions(f)
        titles = [a.title for a in actions]
        assert any("Add missing" in t and "ecut" in t for t in titles)

    def test_invalid_type_produces_fix_action(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 2.5\n")
        actions = get_code_actions(f)
        titles = [a.title for a in actions]
        assert any("Fix" in t and "value type" in t for t in titles)

    def test_duplicate_produces_remove_action(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\necut 20\nnatom 1\n")
        actions = get_code_actions(f)
        titles = [a.title for a in actions]
        assert any("Remove duplicate" in t for t in titles)

    def test_valid_file_no_actions(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("ecut 30\nnatom 1\nntypat 1\ntypat 1\nznucl 14\nxred 0 0 0\ntoldfe 1.0e-8\n")
        actions = get_code_actions(f)
        assert len(actions) == 0

    def test_action_has_json_serialization(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("natom 1\n")
        actions = get_code_actions(f)
        if actions:
            j = actions[0].to_json()
            assert "title" in j
            assert "kind" in j
            assert "edits" in j

    def test_action_includes_diagnostic_reference(self, tmp_path: Path) -> None:
        f = tmp_path / "test.abi"
        f.write_text("natom 1\n")
        actions = get_code_actions(f)
        if actions:
            assert len(actions[0].diagnostics) > 0
