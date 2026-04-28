from pydantic import BaseModel, Field
from typing import Optional


class TreeNode(BaseModel):
    """Represents a single node in the PageIndex tree."""
    title: str
    node_id: str
    line_num: int
    summary: Optional[str] = None
    prefix_summary: Optional[str] = None
    nodes: list["TreeNode"] = Field(default_factory=list)


class RetrievedSection(BaseModel):
    """A single section retrieved from the FBR document."""
    node_id: str
    title: str
    content: str
    summary: str
    line_start: int
    line_end: int
    depth: int
    parent_title: Optional[str] = None


class RetrievalResult(BaseModel):
    """Final output of the rule_retriever module."""
    sections: list[RetrievedSection]
    node_ids_selected: list[str]
    reasoning: str
    passes_used: int
    query_used: str
