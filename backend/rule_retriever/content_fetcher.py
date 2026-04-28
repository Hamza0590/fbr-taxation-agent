import logging
from functools import lru_cache
from pathlib import Path

from .config import get_settings

logger = logging.getLogger("rule_retriever.content_fetcher")


class ContentFetcher:
    def __init__(self, markdown_path: str | None = None):
        settings = get_settings()
        path = markdown_path or settings.markdown_path
        self._lines = self._load_file(path)
        logger.info("Markdown loaded: %d lines", len(self._lines))

    def _load_file(self, path: str) -> list[str]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(
                f"FBR markdown not found at: {p.resolve()}\n"
                "Set RULE_RETRIEVER_MARKDOWN_PATH in .env to the correct path."
            )
        with p.open(encoding="utf-8") as f:
            return f.readlines()

    def fetch(self, start_line: int, end_line: int) -> str:
        """Extract content between start_line and end_line (1-indexed, inclusive)."""
        start_idx = max(0, start_line - 1)
        end_idx = min(len(self._lines), end_line)
        return "".join(self._lines[start_idx:end_idx]).strip()

    def fetch_node(self, node_id: str, tree_index) -> str:
        """Convenience: fetch content for a node given its tree_index entry."""
        start, end = tree_index.get_line_range(node_id)
        return self.fetch(start, end)

    @property
    def total_lines(self) -> int:
        return len(self._lines)


@lru_cache(maxsize=1)
def get_content_fetcher() -> ContentFetcher:
    """Singleton — loads the markdown file once and reuses it."""
    return ContentFetcher()
