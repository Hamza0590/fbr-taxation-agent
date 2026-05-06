import logging

from ..state import TaxSathiState
from ..helpers import build_extraction_trace
from ...tax_extractor.extractor import extract_tax_data
from ...config import get_backend_settings

logger = logging.getLogger("pipeline.extraction_node")


async def extraction_node(state: TaxSathiState) -> dict:
    user_message = state.get("user_message", "")
    conversation_history = state.get("conversation_history") or []
    profile_context = state.get("profile_context")

    # Prepend profile context so the extractor LLM sees known fields
    extraction_message = user_message
    if profile_context:
        extraction_message = (
            f"[User Profile Context — treat these as known facts, prefer message values if they differ]\n"
            f"{profile_context}\n\n"
            f"[User Message]\n{user_message}"
        )

    # Turn number from history
    turn = 1
    if conversation_history:
        turn = len([m for m in conversation_history if m.get("role") == "user"]) + 1

    settings = get_backend_settings()

    try:
        extraction_result = await extract_tax_data(
            user_message=extraction_message,
            conversation_history=conversation_history or None,
            image_context=state.get("image_context"),
        )
    except Exception as exc:
        logger.exception("extract_tax_data failed")
        return {
            "extraction_status": "needs_clarification",
            "extraction_trace": {
                "status": "failed",
                "extracted_fields": {},
                "missing_fields": [],
                "assumptions": [],
                "confidence": 0.0,
                "confidence_label": "Failed",
            },
            "clarification_questions": [],
            "assistant_message": (
                "I had trouble processing your message. "
                "Could you try rephrasing your tax situation?"
            ),
            "response_stage": "clarification_needed",
            "turn_number": turn,
            "error": str(exc),
            "current_node": "extraction",
        }

    extraction_trace = build_extraction_trace(extraction_result)
    trace_dict = extraction_trace.model_dump()

    # Force-complete if too many clarification turns and we have partial data
    if extraction_result.status == "needs_clarification" and turn >= settings.max_clarification_turns:
        if extraction_result.partial_data:
            logger.warning("Forcing extraction complete after %d turns (partial data used)", turn)
            extraction_result.status = "complete"
            extraction_result.extracted_data = extraction_result.partial_data
        else:
            questions_dicts = [q.model_dump() for q in (extraction_result.questions or [])]
            return {
                "extraction_status": "needs_clarification",
                "extraction_trace": trace_dict,
                "clarification_questions": questions_dicts,
                "assistant_message": (
                    extraction_result.message
                    + " (I need at least some basic information to help you.)"
                ),
                "response_stage": "clarification_needed",
                "turn_number": turn,
                "current_node": "extraction",
            }

    # Still needs clarification
    if extraction_result.status == "needs_clarification":
        questions_dicts = [q.model_dump() for q in (extraction_result.questions or [])]
        return {
            "extraction_status": "needs_clarification",
            "extraction_trace": trace_dict,
            "clarification_questions": questions_dicts,
            "assistant_message": extraction_result.message,
            "response_stage": "clarification_needed",
            "turn_number": turn,
            "current_node": "extraction",
        }

    # Extraction complete
    taxpayer_data = extraction_result.extracted_data
    return {
        "extraction_status": "complete",
        "taxpayer_data": taxpayer_data.model_dump(mode="json"),
        "extraction_trace": trace_dict,
        "clarification_questions": [],
        "turn_number": turn,
        "current_node": "extraction",
    }
