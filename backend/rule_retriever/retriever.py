from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from litellm import acompletion

from .config import get_settings
from .content_fetcher import get_content_fetcher
from .models import RetrievedSection, RetrievalResult
from .prompts.tree_reasoning import CROSS_REF_PROMPT, TREE_REASONING_PROMPT
from .query_builder import build_retrieval_query
from .tree_index import get_tree_index

if TYPE_CHECKING:
    from ..tax_extractor.models import TaxpayerData

logger = logging.getLogger("rule_retriever.retriever")


class RetrievalError(Exception):
    """Raised when the retrieval process fails."""


# ── Heuristic fallback node IDs (keyed by income field name) ─────────────────
_INCOME_FALLBACK: dict[str, list[str]] = {
    "salary_income":     ["0005", "0066"],  # salary head + individual rates
    "rental_income":     ["0006", "0014"],  # property head + exemptions
    "business_income":   ["0008", "0009"],  # business divisions
    "capital_gains":     ["0012", "0066"],  # capital gains + rates
    "freelance_income":  ["0013", "0014"],  # other sources + exemptions
    "other_income":      ["0013", "0014"],
    "agricultural_income": ["0014"],
}


def _heuristic_node_ids(taxpayer_data: TaxpayerData) -> list[str]:
    """Return a minimal set of node IDs based on which income fields are populated."""
    ids: list[str] = []
    for field, nodes in _INCOME_FALLBACK.items():
        if getattr(taxpayer_data, field, None) is not None:
            ids.extend(nodes)
    # Always add exemptions + individual rate Division
    ids.extend(["0014", "0066"])
    # Deduplicate preserving order
    seen: set[str] = set()
    return [x for x in ids if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_llm_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = _strip_json_fences(raw)
        return json.loads(cleaned)


async def _call_llm(prompt: str, settings) -> str:
    response = await acompletion(
        model=settings.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        api_key=settings.llm_api_key or None,
    )
    return response.choices[0].message.content or ""


def _build_section(node_id: str, tree_index, content_fetcher) -> RetrievedSection | None:
    try:
        node = tree_index.get_node(node_id)
    except KeyError:
        logger.warning("Invalid node_id from LLM (skipped): %s", node_id)
        return None

    start, end = tree_index.get_line_range(node_id)
    content = content_fetcher.fetch(start, end)
    parent = tree_index.get_parent(node_id)
    depth = tree_index.get_depth(node_id)

    return RetrievedSection(
        node_id=node_id,
        title=node.title,
        content=content,
        summary=node.summary or node.prefix_summary or "",
        line_start=start,
        line_end=end,
        depth=depth,
        parent_title=parent.title if parent else None,
    )


def _find_section_refs_in_content(content: str) -> set[str]:
    """Extract section numbers mentioned in the content (e.g. '149', '100A')."""
    return set(re.findall(r"\b[Ss]ection\s+(\d+[A-Z]?)", content))


def _node_ids_covering_section(section_num: str, tree_index) -> list[str]:
    """Find node IDs whose content defines this section number (via line range heuristic)."""
    # We can't do a full text search here without fetching every node.
    # Use the node_map titles and parent structure as a rough guide.
    # Return empty — the Pass 2 LLM call handles this properly.
    return []


async def retrieve_relevant_sections(taxpayer_data: "TaxpayerData") -> RetrievalResult:
    """
    Main entry point: TaxpayerData → tree reasoning → fetch → RetrievalResult.
    """
    settings = get_settings()
    tree_index = get_tree_index()
    content_fetcher = get_content_fetcher()

    query = build_retrieval_query(taxpayer_data)
    logger.info("Retrieval query built (%d chars)", len(query))
    logger.debug("Query:\n%s", query)

    tree_str = tree_index.get_tree_for_prompt()

    # ── Pass 1: Initial tree reasoning ───────────────────────────────────────
    prompt = TREE_REASONING_PROMPT.format(
        max_nodes=settings.max_nodes,
        tree_structure=tree_str,
        retrieval_query=query,
    )

    reasoning = ""
    selected_ids: list[str] = []

    try:
        raw = await _call_llm(prompt, settings)
        logger.debug("Pass 1 LLM response: %s", raw)
        parsed = _parse_llm_json(raw)
        selected_ids = [str(nid) for nid in parsed.get("node_ids", [])]
        reasoning = parsed.get("reasoning", "")
        logger.info("Pass 1 selected %d nodes: %s", len(selected_ids), selected_ids)
        print(f"\n[RETRIEVER] Pass 1 Reasoning: {reasoning}")
        print(f"[RETRIEVER] Pass 1 Selected Nodes: {selected_ids}")
    except Exception as exc:
        logger.error("Pass 1 LLM/JSON failure: %s — using heuristic fallback", exc)
        selected_ids = _heuristic_node_ids(taxpayer_data)
        reasoning = "Heuristic fallback used due to LLM error."

    # Enforce max_nodes limit
    if len(selected_ids) > settings.max_nodes:
        logger.warning("LLM returned %d nodes; truncating to %d", len(selected_ids), settings.max_nodes)
        selected_ids = selected_ids[: settings.max_nodes]

    # Build sections from Pass 1
    sections: list[RetrievedSection] = []
    valid_ids: list[str] = []
    for nid in selected_ids:
        sec = _build_section(nid, tree_index, content_fetcher)
        if sec:
            sections.append(sec)
            valid_ids.append(nid)

    passes_used = 1

    # ── Pass 2: Cross-reference check ────────────────────────────────────────
    if settings.max_passes >= 2 and sections:
        all_content = "\n".join(s.content for s in sections)
        referenced_nums = _find_section_refs_in_content(all_content)

        # Determine which section numbers are NOT yet covered by fetched nodes
        # We consider a section covered if it appears in a node's line range
        # Simplified: if any valid_id's line range contains lines where that section is defined
        # For speed, we'll use the content we already have
        already_in_content: set[str] = set()
        for s in sections:
            already_in_content |= _find_section_refs_in_content(s.content)
        # Actually all referenced_nums are already "found" in content - we need to
        # check if their DEFINITIONS are fetched (i.e., the containing node is fetched)
        # Simpler heuristic: any num referenced that starts a line in fetched content
        defined_in_fetched: set[str] = set()
        for s in sections:
            for m in re.finditer(r"^(\d+[A-Z]?)\.\s+[A-Za-z]", s.content, re.MULTILINE):
                defined_in_fetched.add(m.group(1))

        missing = referenced_nums - defined_in_fetched
        # Limit to 3 most interesting missing refs (exclude very common ones)
        missing_filtered = [n for n in sorted(missing) if n not in ("1", "2", "3")][:3]

        if missing_filtered:
            logger.info("Pass 2: %d uncovered cross-references: %s", len(missing_filtered), missing_filtered)
            cross_prompt = CROSS_REF_PROMPT.format(
                missing_sections=", ".join(f"Section {n}" for n in missing_filtered),
                tree_structure=tree_str,
            )
            try:
                raw2 = await _call_llm(cross_prompt, settings)
                logger.debug("Pass 2 LLM response: %s", raw2)
                parsed2 = _parse_llm_json(raw2)
                extra_ids = [str(nid) for nid in parsed2.get("node_ids", [])]
                # Only add IDs not already fetched, within remaining max_nodes budget
                remaining = max(0, settings.max_nodes - len(valid_ids))
                new_ids = [nid for nid in extra_ids if nid not in valid_ids][:min(3, remaining)]
                for nid in new_ids:
                    sec = _build_section(nid, tree_index, content_fetcher)
                    if sec:
                        sections.append(sec)
                        valid_ids.append(nid)
                        logger.info("Pass 2 added node: %s (%s)", nid, sec.title)
                passes_used = 2
            except Exception as exc:
                logger.warning("Pass 2 LLM/JSON failure (non-fatal): %s", exc)
        else:
            logger.info("Pass 2: no uncovered cross-references — skipping second LLM call")

    return RetrievalResult(
        sections=sections,
        node_ids_selected=valid_ids,
        reasoning=reasoning,
        passes_used=passes_used,
        query_used=query,
    )
