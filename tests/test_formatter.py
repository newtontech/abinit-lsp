"""Tests for ABINIT formatting — TDD third batch."""

from __future__ import annotations

from pathlib import Path

from abinit_lsp.analyzer import format_text

FIXTURES = Path(__file__).parent / "fixtures"


class TestFormatterBasics:
    """Core formatting behaviors."""

    def test_idempotent_on_valid_file(self) -> None:
        content = (FIXTURES / "si_scf.abi").read_text()
        first = format_text(content)
        second = format_text(first)
        assert second == first

    def test_idempotent_on_minimal(self) -> None:
        content = (FIXTURES / "minimal.abi").read_text()
        first = format_text(content)
        second = format_text(first)
        assert second == first

    def test_trailing_newline(self) -> None:
        result = format_text("ecut 30.0\n")
        assert result.endswith("\n")

    def test_strips_trailing_whitespace(self) -> None:
        result = format_text("ecut 30.0   \n")
        assert "ecut" in result
        # No trailing spaces on content lines
        for line in result.splitlines():
            if line.strip():
                assert line == line.rstrip(), f"Trailing whitespace: {line!r}"

    def test_preserves_comments(self) -> None:
        result = format_text("# My comment\necut 30.0\n")
        assert "# My comment" in result

    def test_preserves_blank_lines(self) -> None:
        result = format_text("ecut 30.0\n\nnatom 1\n")
        lines = result.splitlines()
        assert "" in lines  # blank line preserved

    def test_aligns_equals_values(self) -> None:
        result = format_text("ecut=30.0\nnatom=2\n")
        lines = result.strip().splitlines()
        # Both should be aligned
        eq_positions = [line.index("=") for line in lines if "=" in line]
        if len(eq_positions) > 1:
            assert len(set(eq_positions)) == 1, "Equals signs should be aligned"

    def test_aligns_keyword_values(self) -> None:
        result = format_text("ecut 30.0\nnatom 2\n")
        lines = [ln for ln in result.strip().splitlines() if ln.strip()]
        # Keywords should be left-padded to same width
        if len(lines) >= 2:
            parts0 = lines[0].split()
            parts1 = lines[1].split()
            # The keyword columns should be aligned
            assert lines[0].index(parts0[0]) == lines[1].index(parts1[0])

    def test_empty_input(self) -> None:
        result = format_text("")
        assert result == "\n"

    def test_only_comments(self) -> None:
        result = format_text("# comment\n")
        assert "# comment" in result
        assert result.endswith("\n")

    def test_multiline_entry_preserved(self) -> None:
        content = "rprim\n  0.0 0.5 0.5\n  0.5 0.0 0.5\n  0.5 0.5 0.0\n"
        result = format_text(content)
        assert "rprim" in result
        assert "0.0" in result


class TestFormatterCLI:
    """CLI formatting tests."""

    def test_fmt_write(self, tmp_path: Path) -> None:

        from abinit_lsp.cli import fmt_main

        f = tmp_path / "test.abi"
        f.write_text("ecut  30.0\nnatom   2\n")
        rc = fmt_main(["-w", str(f)])
        assert rc == 0
        content = f.read_text()
        assert content.strip()  # Not empty

    def test_fmt_stdout(self, tmp_path: Path) -> None:
        import io
        from unittest.mock import patch

        from abinit_lsp.cli import fmt_main

        f = tmp_path / "test.abi"
        f.write_text("ecut 30.0\nnatom 2\n")
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            rc = fmt_main([str(f)])
        assert rc == 0
        assert "ecut" in out.getvalue()
