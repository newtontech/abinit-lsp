"""Tests for ABINIT hover documentation — TDD fifth batch."""

from __future__ import annotations

from abinit_lsp.hover import get_hover_docs


class TestHover:
    """Hover documentation API."""

    def test_known_keyword_returns_docs(self) -> None:
        result = get_hover_docs("ecut")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 10

    def test_unknown_keyword_returns_none(self) -> None:
        result = get_hover_docs("zzzzznotreal")
        assert result is None

    def test_ecut_docs_mention_cutoff(self) -> None:
        result = get_hover_docs("ecut")
        assert result is not None
        lower = result.lower()
        assert "cutoff" in lower or "energy" in lower or "plane-wave" in lower

    def test_natom_docs(self) -> None:
        result = get_hover_docs("natom")
        assert result is not None
        assert "atom" in result.lower() or "number" in result.lower()

    def test_dataset_keyword_base(self) -> None:
        """Hover on 'ecut1' should return ecut docs."""
        result = get_hover_docs("ecut1")
        assert result is not None
        assert "cutoff" in result.lower() or "energy" in result.lower()

    def test_case_insensitive(self) -> None:
        lower = get_hover_docs("ecut")
        upper = get_hover_docs("ECUT")
        assert lower == upper

    def test_all_known_tokens_have_docs(self) -> None:
        from abinit_lsp.analyzer import KNOWN_TOKENS

        for token in KNOWN_TOKENS:
            result = get_hover_docs(token)
            assert result is not None, f"Missing hover docs for token: {token}"
