"""Tests for TreeIndex loading, indexing, and query formatting."""
import pytest
from rule_retriever.tree_index import TreeIndex


@pytest.fixture(scope="module")
def tree():
    return TreeIndex()


class TestTreeLoading:
    def test_root_title(self, tree):
        assert "Income Tax Ordinance" in tree.root.title

    def test_total_node_count(self, tree):
        # The FBR tree has 88 nodes (0000–0087)
        assert tree.total_nodes == 88

    def test_node_map_populated(self, tree):
        assert len(tree.node_map) == 88

    def test_all_nodes_have_ids(self, tree):
        for nid, node in tree.node_map.items():
            assert node.node_id == nid


class TestLineRanges:
    def test_every_node_has_range(self, tree):
        # Root gets its range lazily; trigger it
        tree._ensure_root_range()
        for nid in tree.node_map:
            start, end = tree.get_line_range(nid)
            assert start <= end, f"Node {nid}: start={start} > end={end}"

    def test_start_less_than_end(self, tree):
        for nid in list(tree.node_map.keys()):
            start, end = tree.get_line_range(nid)
            assert start < end or start == end, f"Node {nid} has invalid range"

    def test_sibling_ranges_non_overlapping(self, tree):
        """For each parent, children's line ranges must not overlap."""
        def check_children(node):
            children = node.nodes
            for i in range(len(children) - 1):
                _, end_a = tree.get_line_range(children[i].node_id)
                start_b, _ = tree.get_line_range(children[i + 1].node_id)
                assert end_a < start_b, (
                    f"Overlap between {children[i].node_id} (ends {end_a}) "
                    f"and {children[i+1].node_id} (starts {start_b})"
                )
            for child in children:
                check_children(child)
        check_children(tree.root)

    def test_child_range_within_parent(self, tree):
        """Every child's range must be within the parent's range."""
        tree._ensure_root_range()
        for nid, node in tree.node_map.items():
            parent = tree.get_parent(nid)
            if parent is None:
                continue  # root has no parent
            p_start, p_end = tree.get_line_range(parent.node_id)
            c_start, c_end = tree.get_line_range(nid)
            assert c_start >= p_start, f"{nid} starts before parent {parent.node_id}"
            assert c_end <= p_end, f"{nid} ends after parent {parent.node_id}"


class TestNodeAccess:
    def test_get_known_node(self, tree):
        node = tree.get_node("0001")
        assert "Chapter 1" in node.title or "CHAPTER" in node.title.upper()

    def test_get_salary_node(self, tree):
        node = tree.get_node("0005")
        assert "SALARY" in node.title.upper()

    def test_get_invalid_node_raises(self, tree):
        with pytest.raises(KeyError):
            tree.get_node("9999")

    def test_get_parent_of_chapter(self, tree):
        parent = tree.get_parent("0001")
        assert parent is not None
        assert parent.node_id == "0000"

    def test_get_parent_of_root_is_none(self, tree):
        assert tree.get_parent("0000") is None

    def test_depth_of_root(self, tree):
        assert tree.get_depth("0000") == 0

    def test_depth_of_chapter(self, tree):
        assert tree.get_depth("0001") == 1

    def test_depth_of_division(self, tree):
        # Division 1 of Chapter 3 Part 4 = node 0008
        assert tree.get_depth("0008") == 3


class TestTreeForPrompt:
    def test_returns_string(self, tree):
        result = tree.get_tree_for_prompt()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_node_ids_in_brackets(self, tree):
        result = tree.get_tree_for_prompt()
        assert "[0000]" in result
        assert "[0001]" in result
        assert "[0005]" in result

    def test_hierarchy_via_indentation(self, tree):
        lines = tree.get_tree_for_prompt().splitlines()
        root_line = next(l for l in lines if "[0000]" in l)
        chapter_line = next(l for l in lines if "[0001]" in l)
        # Chapter should be indented more than root
        root_indent = len(root_line) - len(root_line.lstrip())
        chapter_indent = len(chapter_line) - len(chapter_line.lstrip())
        assert chapter_indent > root_indent

    def test_all_node_ids_present(self, tree):
        result = tree.get_tree_for_prompt()
        for nid in tree.node_map:
            assert f"[{nid}]" in result, f"Node {nid} missing from prompt tree"
