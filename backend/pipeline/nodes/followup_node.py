import json
import logging

from litellm import acompletion

from ..state import TaxSathiState
from ..prompts.fbr_qa_prompt import FOLLOWUP_SYSTEM_PROMPT
from ...config import get_backend_settings

logger = logging.getLogger("pipeline.followup_node")


async def followup_node(state: TaxSathiState) -> dict:
    extraction_status = state.get("extraction_status", "not_started")
    calculation_result = state.get("calculation_result")
    user_message = state.get("user_message", "")
    conversation_history = state.get("conversation_history") or []

    # Case 1: User is answering a clarification question → re-run extraction
    if extraction_status == "needs_clarification":
        clarification_turn = state.get("clarification_turn", 0)
        logger.info("follow_up: clarification answer detected — routing to extraction (turn %d)", clarification_turn + 1)
        return {
            "clarification_turn": clarification_turn + 1,
            "current_node": "followup",
        }

    # Case 2: User is asking about a completed calculation result
    if calculation_result:
        logger.info("follow_up: post-calculation follow-up question")
        cfg = get_backend_settings()
        api_key = cfg.llm_api_key or None

        # Build context: summarise the calculation + top retrieved sections
        try:
            calc_summary = json.dumps(
                {k: v for k, v in calculation_result.items()
                 if k in (
                     "total_gross_income", "total_tax_liability", "net_tax_payable",
                     "is_refund", "refund_due", "effective_tax_rate", "summary_text",
                     "income_breakdowns", "caveats",
                 )},
                indent=2,
            )
        except Exception:
            calc_summary = str(calculation_result)

        retrieval_result = state.get("retrieval_result")
        sections_context = ""
        if retrieval_result and retrieval_result.get("sections"):
            top_sections = retrieval_result["sections"][:3]
            sections_context = "\n\n".join(
                f"[{s.get('title', '')}]\n{s.get('content', '')[:600]}"
                for s in top_sections
            )

        user_content = (
            f"Tax Calculation Result:\n{calc_summary}\n\n"
            + (f"Relevant FBR Sections:\n{sections_context}\n\n" if sections_context else "")
            + f"User Follow-Up Question: {user_message}"
        )

        messages: list[dict] = [{"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT}]
        for m in conversation_history[-6:]:
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_content})

        try:
            response = await acompletion(
                model=cfg.followup_llm_model,
                messages=messages,
                temperature=cfg.followup_llm_temperature,
                max_tokens=cfg.followup_llm_max_tokens,
                api_key=api_key,
            )
            answer = response.choices[0].message.content or "I couldn't generate an answer to your follow-up question."
        except Exception as exc:
            logger.exception("Follow-up LLM failed")
            answer = "I had trouble processing your follow-up question. Please try again."

        return {
            "assistant_message": answer,
            "qa_answer": answer,
            "response_stage": "qa_response",
            "current_node": "followup",
        }

    # Case 3: Unclear context — generic fallback
    logger.warning("follow_up: unclear context (no clarification pending, no calculation result)")
    return {
        "assistant_message": (
            "I'm not sure what you're referring to. "
            "Could you describe your tax situation or ask a specific FBR question?"
        ),
        "response_stage": "general_response",
        "current_node": "followup",
    }
