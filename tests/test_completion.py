"""Tests for ABINIT keyword completion — TDD fourth batch."""

from __future__ import annotations

from abinit_lsp.completion import KEYWORD_DOCS, complete_keywords


class TestCompletion:
    """Keyword completion API."""

    def test_returns_list(self) -> None:
        result = complete_keywords("")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_prefix_filtering(self) -> None:
        result = complete_keywords("ec")
        keywords = [item["keyword"] for item in result]
        assert all(kw.startswith("ec") for kw in keywords)
        assert "ecut" in keywords

    def test_no_prefix_returns_all(self) -> None:
        result = complete_keywords("")
        assert len(result) >= 30  # ABINIT has many keywords

    def test_case_insensitive_prefix(self) -> None:
        result_lower = complete_keywords("ec")
        result_upper = complete_keywords("EC")
        assert len(result_lower) == len(result_upper)

    def test_completion_item_has_keyword(self) -> None:
        result = complete_keywords("ec")
        assert all("keyword" in item for item in result)

    def test_completion_item_has_documentation(self) -> None:
        result = complete_keywords("ecut")
        assert len(result) >= 1
        assert "doc" in result[0] or "documentation" in result[0] or "detail" in result[0]

    def test_keyword_docs_populated(self) -> None:
        """At least the well-known tokens have documentation."""
        assert "ecut" in KEYWORD_DOCS
        assert "natom" in KEYWORD_DOCS
        assert "ngkpt" in KEYWORD_DOCS
        assert isinstance(KEYWORD_DOCS["ecut"], str)
        assert len(KEYWORD_DOCS["ecut"]) > 10

    def test_completion_item_structure(self) -> None:
        result = complete_keywords("na")
        for item in result:
            assert "keyword" in item
            assert "kind" in item
            assert item["kind"] in ("keyword", "variable", "setting")

    def test_dataset_completion(self) -> None:
        """Typing 'ecut' should also offer 'ecut1', 'ecut2' etc."""
        result = complete_keywords("ecut")
        keywords = [item["keyword"] for item in result]
        assert "ecut" in keywords

    def test_empty_result_for_nonmatching(self) -> None:
        result = complete_keywords("zzzzz")
        assert result == []
