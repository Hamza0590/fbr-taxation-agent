import logging

from litellm import acompletion

from ..state import TaxSathiState
from ...config import get_backend_settings

logger = logging.getLogger("pipeline.general_node")

_GENERAL_SYSTEM_PROMPT = """You are Tax Sathi, a friendly Pakistani income tax assistant.

If the user greets you or asks what you can do:
- Greet them warmly
- Briefly explain that you can: (1) calculate Pakistani income tax, (2) answer questions about FBR rules and sections, (3) explain how specific tax provisions apply
- Invite them to share their tax situation or ask a question
- Keep it to 2–3 sentences

If the user asks something out of scope (unrelated to Pakistani taxes or FBR):
- Politely acknowledge their message
- Explain you specialise in Pakistani income tax questions
- Invite them to ask a tax-related question instead
- Keep it to 2 sentences

Always respond in the same language the user used (English or Urdu)."""


async def general_node(state: TaxSathiState) -> dict:
    cfg = get_backend_settings()
    user_message = state.get("user_message", "")
    intent = state.get("intent", "general_greeting")
    conversation_history = state.get("conversation_history") or []

    messages: list[dict] = [{"role": "system", "content": _GENERAL_SYSTEM_PROMPT}]
    for m in conversation_history[-4:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        response = await acompletion(
            model=cfg.general_llm_model,
            messages=messages,
            temperature=cfg.general_llm_temperature,
            max_tokens=cfg.general_llm_max_tokens,
            api_key=cfg.llm_api_key or None,
        )
        reply = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("General node LLM failed")
        if intent == "out_of_scope":
            reply = (
                "I'm Tax Sathi, your Pakistani tax assistant! "
                "I specialise in income tax calculations and FBR rules. "
                "Feel free to ask me a tax-related question."
            )
        else:
            reply = (
                "Hello! I'm Tax Sathi. I can help you calculate your Pakistani income tax, "
                "answer questions about FBR rules, and explain how specific sections apply to you. "
                "What would you like to know?"
            )

    return {
        "assistant_message": reply,
        "response_stage": "general_response",
        "current_node": "general",
    }
