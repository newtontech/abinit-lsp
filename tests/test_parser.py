"""Tests for the ABINIT parser — TDD first batch.

These tests define the expected parser API and will initially fail.
"""

from __future__ import annotations

from pathlib import Path

from abinit_lsp.parser import AbinitFile, parse, parse_content

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseValidFiles:
    """Parse well-formed ABINIT files into structured representations."""

    def test_parse_minimal_returns_abinitfile(self) -> None:
        af = parse_content(Path("minimal.abi"), (FIXTURES / "minimal.abi").read_text())
        assert isinstance(af, AbinitFile)
        assert af.path.name == "minimal.abi"

    def test_parse_minimal_entries(self) -> None:
        content = (FIXTURES / "minimal.abi").read_text()
        af = parse_content(Path("minimal.abi"), content)
        tokens = [e.keyword for e in af.entries]
        assert "ecut" in tokens
        assert "natom" in tokens
        assert "xred" in tokens

    def test_parse_preserves_line_numbers(self) -> None:
        content = (FIXTURES / "minimal.abi").read_text()
        af = parse_content(Path("minimal.abi"), content)
        # ecut is on the first meaningful line
        ecut = next(e for e in af.entries if e.keyword == "ecut")
        assert ecut.line == 1

    def test_parse_scf_fixture(self) -> None:
        content = (FIXTURES / "si_scf.abi").read_text()
        af = parse_content(Path("si_scf.abi"), content)
        tokens = {e.keyword for e in af.entries}
        assert "ecut" in tokens
        assert "natom" in tokens
        assert "ngkpt" in tokens
        assert "rprim" in tokens

    def test_parse_multidataset(self) -> None:
        content = (FIXTURES / "multidataset.abi").read_text()
        af = parse_content(Path("multidataset.abi"), content)
        tokens = {e.keyword for e in af.entries}
        assert "ndtset" in tokens
        assert "ecut1" in tokens
        assert "ecut2" in tokens
        assert "optcell2" in tokens

    def test_parse_skips_comments(self) -> None:
        content = "# this is a comment\necut 30.0\n"
        af = parse_content(Path("test.abi"), content)
        assert len(af.entries) == 1
        assert af.entries[0].keyword == "ecut"

    def test_parse_skips_blank_lines(self) -> None:
        content = "\n\necut 30.0\n\nnatom 1\n\n"
        af = parse_content(Path("test.abi"), content)
        assert len(af.entries) == 2

    def test_parse_entry_has_values(self) -> None:
        content = "ecut 30.0\n"
        af = parse_content(Path("test.abi"), content)
        assert af.entries[0].values == ["30.0"]

    def test_parse_multiline_entry(self) -> None:
        """rprim is a 3x3 matrix that spans multiple lines."""
        content = "rprim\n  0.0 0.5 0.5\n  0.5 0.0 0.5\n  0.5 0.5 0.0\n"
        af = parse_content(Path("test.abi"), content)
        rprim = af.entries[0]
        assert rprim.keyword == "rprim"
        assert len(rprim.values) == 9

    def test_parse_inline_matrix(self) -> None:
        """rprim can also be on one line."""
        content = "rprim 0.0 0.5 0.5 0.5 0.0 0.5 0.5 0.5 0.0\n"
        af = parse_content(Path("test.abi"), content)
        assert len(af.entries[0].values) == 9

    def test_parse_star_notation(self) -> None:
        """3*10.26 means three copies of 10.26."""
        content = "acell 3*10.26\n"
        af = parse_content(Path("test.abi"), content)
        assert af.entries[0].values == ["3*10.26"]

    def test_parse_keyword_equals_value(self) -> None:
        """Some ABINIT inputs use key=value syntax."""
        content = "ecut = 30.0\n"
        af = parse_content(Path("test.abi"), content)
        assert af.entries[0].keyword == "ecut"
        assert af.entries[0].values == ["30.0"]

    def test_parse_comment_styles(self) -> None:
        """ABINIT supports # and ! comment styles."""
        content = "# hash comment\n! bang comment\necut 30.0\n"
        af = parse_content(Path("test.abi"), content)
        assert len(af.entries) == 1

    def test_parse_semicolon_comment(self) -> None:
        content = "; semicolon comment\necut 30.0\n"
        af = parse_content(Path("test.abi"), content)
        assert len(af.entries) == 1

    def test_parse_file_path(self) -> None:
        af = parse(FIXTURES / "minimal.abi")
        assert isinstance(af, AbinitFile)
        assert len(af.entries) > 0

    def test_parse_collects_comments(self) -> None:
        content = "# Header comment\necut 30.0\n# Inline comment\nnatom 1\n"
        af = parse_content(Path("test.abi"), content)
        # Comments are tracked in the file
        assert len(af.comments) >= 2


class TestParseEdgeCases:
    """Edge cases and error handling."""

    def test_empty_file_produces_empty_entries(self) -> None:
        af = parse_content(Path("empty.abi"), "")
        assert af.entries == []

    def test_only_comments(self) -> None:
        af = parse_content(Path("comments.abi"), "# just a comment\n! another\n")
        assert af.entries == []

    def test_dataset_keyword_stripping(self) -> None:
        """ecut1 -> base keyword 'ecut' with dataset index 1."""
        content = "ecut1 20.0\necut2 30.0\n"
        af = parse_content(Path("test.abi"), content)
        assert af.entries[0].keyword == "ecut1"
        assert af.entries[0].base_keyword == "ecut"
        assert af.entries[0].dataset == 1
        assert af.entries[1].dataset == 2

    def test_keyword_case_insensitive(self) -> None:
        """ABINIT keywords are case-insensitive; we normalize to lower."""
        content = "ECUT 30.0\nEcut 20.0\n"
        af = parse_content(Path("test.abi"), content)
        assert all(e.keyword == "ecut" for e in af.entries)


class TestParseUtilities:
    """Utility functions on parsed data."""

    def test_keywords_set(self) -> None:
        content = "ecut 30.0\nnatom 2\n"
        af = parse_content(Path("test.abi"), content)
        assert af.keywords() == {"ecut", "natom"}

    def test_has_keyword(self) -> None:
        content = "ecut 30.0\nnatom 2\n"
        af = parse_content(Path("test.abi"), content)
        assert af.has_keyword("ecut")
        assert not af.has_keyword("optcell")

    def test_get_entries_for(self) -> None:
        content = "ecut 30.0\nnatom 2\necut 20.0\n"
        af = parse_content(Path("test.abi"), content)
        assert len(af.get_entries_for("ecut")) == 2

    def test_dataset_count(self) -> None:
        content = "ndtset 2\necut1 20.0\necut2 30.0\n"
        af = parse_content(Path("test.abi"), content)
        ndtset = af.get_entries_for("ndtset")
        assert len(ndtset) == 1
        assert ndtset[0].values == ["2"]
