import json
import logging
import re

from litellm import acompletion

from ..state import TaxSathiState
from ..prompts.fbr_qa_prompt import FBR_QA_SYSTEM_PROMPT
from ...rule_retriever.tree_index import get_tree_index
from ...rule_retriever.content_fetcher import get_content_fetcher
from ...rule_retriever.config import get_settings
from ...rule_retriever.prompts.tree_reasoning import TREE_REASONING_PROMPT

logger = logging.getLogger("pipeline.fbr_qa_node")


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def _call_llm(model: str, messages: list[dict], settings, max_tokens: int = 2000) -> str:
    response = await acompletion(
        model=model,
        messages=messages,
        temperature=settings.llm_temperature,
        max_tokens=max_tokens,
        api_key=settings.llm_api_key or None,
    )
    return response.choices[0].message.content or ""


def _build_section_trace(node_id: str, tree_index, content_fetcher) -> dict | None:
    try:
        node = tree_index.get_node(node_id)
    except KeyError:
        logger.warning("Invalid node_id from LLM (skipped): %s", node_id)
        return None

    start, end = tree_index.get_line_range(node_id)
    content = content_fetcher.fetch(start, end)
    parent = tree_index.get_parent(node_id)
    depth = tree_index.get_depth(node_id)
    title = node.title
    parent_title = parent.title if parent else None

    return {
        "node_id": node_id,
        "title": title,
        "parent_title": parent_title,
        "relevance": "Retrieved for FBR policy question",
        "content_preview": content[:300].strip() + "..." if len(content) > 300 else content.strip(),
        "full_content": content,
        "line_range": f"Lines {start}-{end}",
        "section_path": f"{parent_title} > {title}" if parent_title else title,
    }


async def fbr_qa_node(state: TaxSathiState) -> dict:
    settings = get_settings()
    tree_index = get_tree_index()
    content_fetcher = get_content_fetcher()
    user_message = state.get("user_message", "")
    conversation_history = state.get("conversation_history") or []

    # ── Step 1: Tree-index retrieval using the user's natural language question ─
    tree_str = tree_index.get_tree_for_prompt()
    prompt = TREE_REASONING_PROMPT.format(
        max_nodes=settings.max_nodes,
        tree_structure=tree_str,
        retrieval_query=user_message,
    )

    selected_ids: list[str] = []
    reasoning = ""
    try:
        raw = await _call_llm(
            settings.llm_model,
            [{"role": "user", "content": prompt}],
            settings,
        )
        parsed = json.loads(_strip_fences(raw))
        selected_ids = [str(nid) for nid in parsed.get("node_ids", [])]
        reasoning = parsed.get("reasoning", "")
        logger.info("FBR QA: Pass 1 selected %d nodes: %s", len(selected_ids), selected_ids)
    except Exception as exc:
        logger.error("FBR QA tree reasoning failed: %s", exc)
        selected_ids = ["0005", "0066"]  # minimal fallback
        reasoning = "Fallback selection due to LLM error"

    if len(selected_ids) > settings.max_nodes:
        selected_ids = selected_ids[: settings.max_nodes]

    section_traces: list[dict] = []
    valid_ids: list[str] = []
    for nid in selected_ids:
        st = _build_section_trace(nid, tree_index, content_fetcher)
        if st:
            section_traces.append(st)
            valid_ids.append(nid)

    # ── Step 2: Answer the question using retrieved sections ───────────────────
    if section_traces:
        sections_text = "\n\n---\n\n".join(
            f"[{st['title']}]\n{st['full_content']}"
            for st in section_traces
        )
        context_block = (
            f"FBR Document Sections Retrieved:\n\n{sections_text}\n\n"
            f"User Question: {user_message}"
        )
    else:
        context_block = (
            f"No relevant FBR sections could be retrieved.\n\n"
            f"User Question: {user_message}"
        )

    messages = [{"role": "system", "content": FBR_QA_SYSTEM_PROMPT}]
    for m in conversation_history[-6:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": context_block})

    try:
        answer_raw = await _call_llm(settings.llm_model, messages, settings, max_tokens=1000)
        qa_answer = answer_raw.strip() or "I couldn't generate an answer. Please try again."
    except Exception as exc:
        logger.exception("FBR QA answer generation failed")
        qa_answer = (
            "I encountered an error while answering your question. "
            "Please try again or rephrase your question."
        )

    retrieval_trace = {
        "status": "complete" if section_traces else "failed",
        "query_summary": user_message[:200],
        "selected_sections": section_traces,
        "passes_used": 1,
        "reasoning": reasoning,
    }

    return {
        "retrieved_sections_for_qa": section_traces,
        "qa_answer": qa_answer,
        "assistant_message": qa_answer,
        "retrieval_trace": retrieval_trace,
        "response_stage": "qa_response",
        "current_node": "fbr_qa",
    }
