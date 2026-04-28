import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .models import TreeNode
from .config import get_settings

logger = logging.getLogger("rule_retriever.tree_index")


class TreeIndex:
    def __init__(self, tree_index_path: str | None = None):
        settings = get_settings()
        path = tree_index_path or settings.tree_index_path
        self._line_count, self.root = self._load_tree(path)
        self.node_map: dict[str, TreeNode] = {}
        self.parent_map: dict[str, Optional[TreeNode]] = {}
        self.line_ranges: dict[str, tuple[int, int]] = {}
        self._build_indexes(self.root, parent=None)

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load_tree(self, path: str) -> tuple[int, TreeNode]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"PageIndex tree JSON not found at: {p.resolve()}\n"
                "Set RULE_RETRIEVER_TREE_INDEX_PATH in .env to the correct path."
            )
        with p.open(encoding="utf-8") as f:
            data = json.load(f)

        line_count: int = data.get("line_count", 0)
        structure = data.get("structure", [])
        if not structure:
            raise ValueError("PageIndex JSON has empty 'structure' array.")

        root_node = TreeNode.model_validate(structure[0])
        logger.info("Tree loaded: %d nodes, line_count=%d", self._count_nodes(root_node), line_count)
        return line_count, root_node

    @staticmethod
    def _count_nodes(node: TreeNode) -> int:
        return 1 + sum(TreeIndex._count_nodes(c) for c in node.nodes)

    # ── Index building ────────────────────────────────────────────────────────

    def _build_indexes(self, node: TreeNode, parent: Optional[TreeNode]) -> None:
        self.node_map[node.node_id] = node
        self.parent_map[node.node_id] = parent
        # Compute line ranges for children of this node
        self._compute_children_ranges(node)
        for child in node.nodes:
            self._build_indexes(child, node)

    def _compute_children_ranges(self, parent_node: TreeNode) -> None:
        children = parent_node.nodes
        if not children:
            return
        parent_end = self.line_ranges.get(parent_node.node_id, (1, self._line_count))[1]
        for i, child in enumerate(children):
            start = child.line_num
            if i + 1 < len(children):
                end = children[i + 1].line_num - 1
            else:
                end = parent_end
            self.line_ranges[child.node_id] = (start, end)

    def _ensure_root_range(self) -> None:
        if self.root.node_id not in self.line_ranges:
            self.line_ranges[self.root.node_id] = (self.root.line_num, self._line_count)

    # ── Public accessors ──────────────────────────────────────────────────────

    def get_node(self, node_id: str) -> TreeNode:
        if node_id not in self.node_map:
            raise KeyError(f"Node '{node_id}' not found in tree index.")
        return self.node_map[node_id]

    def get_line_range(self, node_id: str) -> tuple[int, int]:
        self._ensure_root_range()
        if node_id not in self.line_ranges:
            raise KeyError(f"Line range for node '{node_id}' not computed.")
        return self.line_ranges[node_id]

    def get_parent(self, node_id: str) -> Optional[TreeNode]:
        return self.parent_map.get(node_id)

    def get_depth(self, node_id: str) -> int:
        depth = 0
        current = self.parent_map.get(node_id)
        while current is not None:
            depth += 1
            current = self.parent_map.get(current.node_id)
        return depth

    def get_tree_for_prompt(self) -> str:
        self._ensure_root_range()
        lines: list[str] = []
        self._format_node(self.root, depth=0, lines=lines)
        return "\n".join(lines)

    def _format_node(self, node: TreeNode, depth: int, lines: list[str]) -> None:
        indent = "  " * depth
        summary_text = (node.summary or node.prefix_summary or "").replace("\n", " ").strip()
        summary_short = summary_text[:150] + "..." if len(summary_text) > 150 else summary_text
        if summary_short:
            lines.append(f"{indent}[{node.node_id}] {node.title} | {summary_short}")
        else:
            lines.append(f"{indent}[{node.node_id}] {node.title}")
        for child in node.nodes:
            self._format_node(child, depth + 1, lines)

    @property
    def total_nodes(self) -> int:
        return len(self.node_map)


@lru_cache(maxsize=1)
def get_tree_index() -> TreeIndex:
    """Singleton — loads the tree once and reuses it across requests."""
    return TreeIndex()
