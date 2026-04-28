"""Tests for ContentFetcher file loading and line extraction."""
import pytest
from rule_retriever.content_fetcher import ContentFetcher
from rule_retriever.tree_index import TreeIndex


@pytest.fixture(scope="module")
def fetcher():
    return ContentFetcher()


@pytest.fixture(scope="module")
def tree():
    return TreeIndex()


class TestFetcher:
    def test_file_loads(self, fetcher):
        assert fetcher.total_lines > 1000

    def test_fetch_first_lines_contain_ordinance(self, fetcher):
        content = fetcher.fetch(1, 10)
        assert "Income Tax Ordinance" in content or "INCOME TAX" in content.upper()

    def test_fetch_known_range(self, fetcher, tree):
        # Node 0001 is Chapter 1 — PRELIMINARY
        start, end = tree.get_line_range("0001")
        content = fetcher.fetch(start, end)
        assert len(content) > 50
        assert "PRELIMINARY" in content.upper() or "CHAPTER" in content.upper()

    def test_fetch_node_convenience(self, fetcher, tree):
        content = fetcher.fetch_node("0001", tree)
        assert len(content) > 50

    def test_fetch_salary_node(self, fetcher, tree):
        content = fetcher.fetch_node("0005", tree)
        assert "salary" in content.lower() or "SALARY" in content

    def test_fetch_exemptions_node(self, fetcher, tree):
        content = fetcher.fetch_node("0014", tree)
        assert "exempt" in content.lower()

    def test_fetch_individual_rates_node(self, fetcher, tree):
        content = fetcher.fetch_node("0066", tree)
        # Should contain tax rate table
        assert "%" in content or "rate" in content.lower()

    def test_boundary_beyond_file_does_not_crash(self, fetcher):
        content = fetcher.fetch(999_000, 999_999)
        assert isinstance(content, str)

    def test_fetch_returns_stripped_string(self, fetcher):
        content = fetcher.fetch(1, 5)
        assert content == content.strip()

    def test_line_range_start_equals_end(self, fetcher):
        # Single line fetch — should not crash
        content = fetcher.fetch(100, 100)
        assert isinstance(content, str)
