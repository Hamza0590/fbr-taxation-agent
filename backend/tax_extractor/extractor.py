import json
import logging
import re
from litellm import acompletion
from .models import ExtractionResponse
from .models.clarification import ClarificationQuestion
from .prompts.system_prompt import SYSTEM_PROMPT
from .config import get_settings

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when the extraction process fails at the LLM level."""
    pass


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _fallback_response(reason: str) -> ExtractionResponse:
    return ExtractionResponse(
        status="needs_clarification",
        extracted_data=None,
        partial_data=None,
        questions=[
            ClarificationQuestion(
                field_name="user_input",
                question_text="I had trouble understanding your tax situation. Could you rephrase and include details like your income type, amount, and whether it's monthly or annual?",
                options=None,
                input_type="text",
                priority="required",
            )
        ],
        message="I wasn't able to parse your information clearly. Could you please describe your income situation again with a bit more detail?",
    )


async def extract_tax_data(
    user_message: str,
    conversation_history: list[dict] | None = None,
    image_context: str | None = None,
) -> ExtractionResponse:
    """
    Takes a user message (and optional conversation history for multi-turn),
    sends it to the LLM with the extraction system prompt,
    and returns a validated ExtractionResponse.
    """
    settings = get_settings()

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    if conversation_history:
        messages.extend(conversation_history)

    final_message = user_message
    if image_context:
        final_message = (
            f"{user_message}\n\n"
            f"[Document Image Context]\n"
            f"The user has uploaded a financial document. The following information was automatically extracted from the image. "
            f"Use this as additional input alongside the user's message:\n\n"
            f"{image_context}\n"
            f"[End Document Image Context]"
        )

    messages.append({"role": "user", "content": final_message})

    logger.info("Sending extraction request. User message: %s", user_message)

    try:
        response = await acompletion(
            model=settings.llm_model,
            messages=messages,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.llm_api_key or None,
        )
    except Exception as exc:
        logger.error("LLM call failed: %s", exc)
        raise ExtractionError(f"LLM call failed: {exc}") from exc

    raw_content: str = response.choices[0].message.content or ""
    logger.info("Raw LLM response: %s", raw_content)
    print(f"\n[EXTRACTOR] Raw LLM Response:\n{raw_content}\n")

    # Attempt JSON parse; strip markdown fences on first failure
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        cleaned = _strip_markdown_fences(raw_content)
        logger.warning("Initial JSON parse failed; retrying after stripping fences.")
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse failed after cleanup. Raw: %s", raw_content)
            return _fallback_response("JSON parse failed")

    # Validate against Pydantic model
    try:
        result = ExtractionResponse.model_validate(parsed)
    except Exception as exc:
        logger.error("Pydantic validation failed: %s. Parsed dict: %s", exc, parsed)
        return _fallback_response("Pydantic validation failed")

    logger.info("Extraction complete. Status: %s, Confidence: %s",
                result.status,
                result.extracted_data.confidence_score if result.extracted_data else "N/A")
    
    conf = result.extracted_data.confidence_score if result.extracted_data else "N/A"
    print(f"[EXTRACTOR] Extraction complete. Status: {result.status}, Confidence: {conf}")
    return result
