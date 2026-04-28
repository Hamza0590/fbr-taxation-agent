import json
import logging
import re

from litellm import acompletion

from ..state import TaxSathiState
from ..prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from ...config import get_backend_settings

logger = logging.getLogger("pipeline.router_node")

_VALID_INTENTS = {
    "tax_calculation", "fbr_policy_qa",
    "follow_up", "general_greeting", "out_of_scope",
}


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def router_node(state: TaxSathiState) -> dict:
    cfg = get_backend_settings()
    api_key = cfg.llm_api_key or None

    user_message = state.get("user_message", "")
    extraction_status = state.get("extraction_status", "not_started")
    calculation_result = state.get("calculation_result")

    context_lines = [f"User message: {user_message}"]
    if extraction_status == "needs_clarification":
        context_lines.append(
            "Context: The assistant just asked a clarification question. "
            "The user may be answering it."
        )
    if calculation_result:
        context_lines.append(
            "Context: A full tax calculation was just completed. "
            "The user may be asking a follow-up about the result."
        )

    try:
        response = await acompletion(
            model=cfg.router_llm_model,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": "\n".join(context_lines)},
            ],
            temperature=cfg.router_llm_temperature,
            max_tokens=cfg.router_llm_max_tokens,
            api_key=api_key,
        )
        raw = response.choices[0].message.content or ""
        parsed = json.loads(_strip_fences(raw))
        intent = parsed.get("intent", "general_greeting")
        reasoning = parsed.get("reasoning", "")

        if intent not in _VALID_INTENTS:
            logger.warning("Router returned unknown intent %r — falling back", intent)
            intent = "general_greeting"
            reasoning = "Unknown intent from LLM, fell back to general_greeting"

    except Exception as exc:
        logger.error("Router LLM (%s) failed: %s — defaulting to tax_calculation", cfg.router_llm_model, exc)
        intent = "tax_calculation"
        reasoning = f"Router error ({exc}), defaulting to tax_calculation"

    logger.info("intent=%s | %s", intent, reasoning)
    return {
        "intent": intent,
        "router_reasoning": reasoning,
        "current_node": "router",
    }
