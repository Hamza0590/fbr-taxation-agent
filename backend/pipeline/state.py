from typing import TypedDict, Literal, Optional


class TaxSathiState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────────
    user_message: str
    conversation_history: list[dict]
    session_id: Optional[str]
    profile_context: Optional[str]
    image_context: Optional[str]           # Plain-text financial summary from uploaded image, if any

    # ── Router ─────────────────────────────────────────────────────────────────
    intent: Literal[
        "tax_calculation", "fbr_policy_qa",
        "follow_up", "general_greeting", "out_of_scope"
    ]
    router_reasoning: str

    # ── Tax Calculation Pipeline ────────────────────────────────────────────────
    taxpayer_data: Optional[dict]           # TaxpayerData serialised as dict
    extraction_status: Literal["complete", "needs_clarification", "not_started"]
    clarification_questions: list[dict]     # ClarificationQuestion dicts
    clarification_turn: int

    retrieval_result: Optional[dict]        # RetrievalResult serialised as dict
    interpretation_result: Optional[dict]   # TaxComputationPlan serialised as dict
    calculation_result: Optional[dict]      # TaxCalculationResult serialised as dict

    # ── Canvas traces (built per-node, consumed by response_node) ──────────────
    extraction_trace: Optional[dict]        # ExtractionTrace.model_dump()
    retrieval_trace: Optional[dict]         # RetrievalTrace.model_dump()
    interpretation_trace: Optional[dict]    # InterpretationTrace.model_dump()
    calculation_trace: Optional[dict]       # CalculationTrace.model_dump()

    # ── FBR Q&A ────────────────────────────────────────────────────────────────
    retrieved_sections_for_qa: list[dict]   # SectionTrace dicts
    qa_answer: Optional[str]

    # ── Output ─────────────────────────────────────────────────────────────────
    assistant_message: str
    response_stage: Literal[
        "clarification_needed", "extraction_complete",
        "qa_response", "general_response"
    ]
    turn_number: int

    # ── Assembled final response (read by pipeline/router.py) ──────────────────
    final_response: Optional[dict]

    # ── Error Handling ─────────────────────────────────────────────────────────
    error: Optional[str]
    current_node: str
