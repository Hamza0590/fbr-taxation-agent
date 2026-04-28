import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from .models import PipelineRequest, PipelineResponse
from .graph import tax_sathi_graph
from ..auth.utils import get_current_user, TokenData
from ..database import supabase

logger = logging.getLogger("pipeline")
router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline"])


def _build_initial_state(request: PipelineRequest) -> dict:
    """Convert a PipelineRequest into the initial TaxSathiState dict."""
    history = []
    if request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    return {
        "user_message": request.message,
        "conversation_history": history,
        "session_id": request.session_id,
        "profile_context": request.profile_context,
        # Router defaults (will be overwritten by router_node)
        "intent": "general_greeting",
        "router_reasoning": "",
        # Extraction defaults
        "taxpayer_data": None,
        "extraction_status": "not_started",
        "clarification_questions": [],
        "clarification_turn": 0,
        # Pipeline results
        "retrieval_result": None,
        "interpretation_result": None,
        "calculation_result": None,
        # Canvas traces
        "extraction_trace": None,
        "retrieval_trace": None,
        "interpretation_trace": None,
        "calculation_trace": None,
        # FBR Q&A
        "retrieved_sections_for_qa": [],
        "qa_answer": None,
        # Output
        "assistant_message": "",
        "response_stage": "general_response",
        "turn_number": 1,
        "final_response": None,
        # Debug
        "error": None,
        "current_node": "router",
    }


@router.post("/chat", response_model=PipelineResponse)
async def chat(
    request: PipelineRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Main chat endpoint — runs the LangGraph pipeline."""
    try:
        initial_state = _build_initial_state(request)
        final_state = await tax_sathi_graph.ainvoke(initial_state)

        final_response_dict = final_state.get("final_response")
        if not final_response_dict:
            raise ValueError("Graph completed without producing a final_response")

        result = PipelineResponse.model_validate(final_response_dict)
    except Exception:
        logger.exception("Pipeline failed")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request. Please try again.",
        )

    # Persist messages — best-effort, never fails the request
    if request.session_id:
        try:
            existing = (
                supabase.table("messages")
                .select("id")
                .eq("session_id", request.session_id)
                .limit(1)
                .execute()
            )
            is_first = len(existing.data) == 0

            supabase.table("messages").insert({
                "session_id": request.session_id,
                "role": "user",
                "content": request.message,
                "canvas_data": None,
            }).execute()

            canvas_dict = result.canvas.model_dump() if result.canvas else None
            supabase.table("messages").insert({
                "session_id": request.session_id,
                "role": "assistant",
                "content": result.assistant_message,
                "canvas_data": canvas_dict,
            }).execute()

            if is_first:
                title = request.message[:50].strip()
                supabase.table("sessions").update({"title": title}).eq("id", request.session_id).execute()
            else:
                now = datetime.now(timezone.utc).isoformat()
                supabase.table("sessions").update({"updated_at": now}).eq("id", request.session_id).execute()

        except Exception as db_err:
            logger.warning(f"Failed to persist messages: {db_err}")

    return result
