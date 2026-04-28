import logging
from typing import Optional

from ..state import TaxSathiState
from ..models import (
    PipelineResponse, CanvasData, ProcessingStep,
    ExtractionTrace, RetrievalTrace, SectionTrace,
    InterpretationTrace, CalculationTrace,
)
from ...tax_extractor.models import TaxpayerData
from ...tax_extractor.models.clarification import ClarificationQuestion
from ...rule_retriever.models import RetrievedSection

logger = logging.getLogger("pipeline.response_node")


def _step(n: int, name: str, status: str, summary: Optional[str] = None) -> ProcessingStep:
    return ProcessingStep(step_number=n, step_name=name, status=status, duration_ms=None, summary=summary)


def _build_tax_calc_steps(state: TaxSathiState, response_stage: str) -> list[ProcessingStep]:
    extraction_trace = state.get("extraction_trace") or {}
    retrieval_trace = state.get("retrieval_trace") or {}
    interpretation_trace = state.get("interpretation_trace") or {}
    calculation_trace = state.get("calculation_trace") or {}
    user_message = state.get("user_message", "")

    steps: list[ProcessingStep] = [
        _step(1, "Understanding your query", "completed",
              f"Received: \"{user_message[:80]}{'...' if len(user_message) > 80 else ''}\""),
    ]

    # Step 2: Extraction
    ext_status = extraction_trace.get("status", "partial")
    if ext_status == "failed":
        steps.append(_step(2, "Extracting tax information", "failed",
                           "Failed to extract tax information from your message"))
    elif response_stage == "clarification_needed":
        n_extracted = len(extraction_trace.get("extracted_fields", {}))
        n_missing = len(extraction_trace.get("missing_fields", []))
        steps.append(_step(2, "Extracting tax information", "completed",
                           f"Extracted {n_extracted} field(s) — {n_missing} more needed"))
    else:
        n_extracted = len(extraction_trace.get("extracted_fields", {}))
        label = extraction_trace.get("confidence_label", "").lower()
        steps.append(_step(2, "Extracting tax information", "completed",
                           f"Successfully extracted {n_extracted} field(s) with {label} confidence"))

    if response_stage == "clarification_needed":
        steps.append(_step(3, "Finding relevant FBR sections", "pending"))
        return steps

    # Step 3: Retrieval
    ret_status = retrieval_trace.get("status", "skipped")
    if ret_status == "complete":
        n_sections = len(retrieval_trace.get("selected_sections", []))
        steps.append(_step(3, "Finding relevant FBR sections", "completed",
                           f"Found {n_sections} relevant section(s) from the Income Tax Ordinance"))
    elif ret_status == "failed":
        steps.append(_step(3, "Finding relevant FBR sections", "failed",
                           retrieval_trace.get("error_message", "Could not retrieve FBR sections")))
    else:
        steps.append(_step(3, "Finding relevant FBR sections", "skipped"))

    if not retrieval_trace or ret_status != "complete":
        return steps

    # Step 4: Interpretation
    int_status = interpretation_trace.get("status", "")
    if int_status == "complete":
        n_income = len(interpretation_trace.get("income_classifications", []))
        n_deductions = len([d for d in interpretation_trace.get("deductions", []) if d.get("allowed")])
        steps.append(_step(4, "Interpreting tax rules", "completed",
                           f"Classified {n_income} income source(s); {n_deductions} deduction(s) allowed"))
    elif int_status == "failed":
        steps.append(_step(4, "Interpreting tax rules", "failed",
                           interpretation_trace.get("error_message", "Interpretation failed")))
    else:
        return steps

    if int_status != "complete":
        return steps

    # Step 5: Calculation
    calc_status = calculation_trace.get("status", "")
    if calc_status == "complete":
        net = calculation_trace.get("net_tax_payable", 0)
        is_refund = calculation_trace.get("is_refund", False)
        total = calculation_trace.get("total_tax_liability", 0)
        net_str = f"Refund due: Rs. {calculation_trace.get('refund_due', 0):,.0f}" if is_refund else f"Net payable: Rs. {net:,.0f}"
        steps.append(_step(5, "Computing tax", "completed",
                           f"Total liability Rs. {total:,.0f} | {net_str}"))
    elif calc_status == "failed":
        steps.append(_step(5, "Computing tax", "failed",
                           calculation_trace.get("error_message", "Calculation failed")))

    return steps


def _build_qa_steps(state: TaxSathiState) -> list[ProcessingStep]:
    user_message = state.get("user_message", "")
    retrieval_trace = state.get("retrieval_trace") or {}
    n_sections = len(retrieval_trace.get("selected_sections", []))
    return [
        _step(1, "Understanding your query", "completed",
              f"Received: \"{user_message[:80]}{'...' if len(user_message) > 80 else ''}\""),
        _step(2, "Retrieving FBR sections", "completed" if n_sections > 0 else "failed",
              f"Retrieved {n_sections} relevant FBR section(s)" if n_sections else "No sections found"),
    ]


def _build_general_steps(state: TaxSathiState) -> list[ProcessingStep]:
    user_message = state.get("user_message", "")
    return [
        _step(1, "Understanding your query", "completed",
              f"Received: \"{user_message[:80]}{'...' if len(user_message) > 80 else ''}\""),
    ]


async def response_node(state: TaxSathiState) -> dict:
    response_stage = state.get("response_stage", "general_response")
    assistant_message = state.get("assistant_message", "")
    session_id = state.get("session_id")
    turn_number = state.get("turn_number", 1)

    # ── Clarification needed ────────────────────────────────────────────────────
    if response_stage == "clarification_needed":
        steps = _build_tax_calc_steps(state, response_stage)

        extraction_trace = None
        if state.get("extraction_trace"):
            try:
                extraction_trace = ExtractionTrace.model_validate(state["extraction_trace"])
            except Exception:
                pass

        canvas = CanvasData(steps=steps, extraction=extraction_trace)

        questions: Optional[list[ClarificationQuestion]] = None
        if state.get("clarification_questions"):
            try:
                questions = [
                    ClarificationQuestion.model_validate(q)
                    for q in state["clarification_questions"]
                ]
            except Exception:
                pass

        pipeline_response = PipelineResponse(
            stage="clarification_needed",
            assistant_message=assistant_message,
            questions=questions,
            canvas=canvas,
            session_id=session_id,
            turn_number=turn_number,
        )

    # ── Full tax calculation complete ───────────────────────────────────────────
    elif response_stage == "extraction_complete":
        steps = _build_tax_calc_steps(state, response_stage)

        extraction_trace = None
        if state.get("extraction_trace"):
            try:
                extraction_trace = ExtractionTrace.model_validate(state["extraction_trace"])
            except Exception:
                pass

        retrieval_trace = None
        if state.get("retrieval_trace"):
            try:
                rt = state["retrieval_trace"]
                section_traces = [SectionTrace.model_validate(s) for s in rt.get("selected_sections", [])]
                retrieval_trace = RetrievalTrace(
                    status=rt["status"],
                    query_summary=rt.get("query_summary", ""),
                    selected_sections=section_traces,
                    passes_used=rt.get("passes_used", 1),
                    reasoning=rt.get("reasoning", ""),
                    error_message=rt.get("error_message"),
                )
            except Exception:
                pass

        interpretation_trace = None
        if state.get("interpretation_trace"):
            try:
                interpretation_trace = InterpretationTrace.model_validate(state["interpretation_trace"])
            except Exception:
                pass

        calculation_trace = None
        if state.get("calculation_trace"):
            try:
                calculation_trace = CalculationTrace.model_validate(state["calculation_trace"])
            except Exception:
                pass

        canvas = CanvasData(
            steps=steps,
            extraction=extraction_trace,
            retrieval=retrieval_trace,
            interpretation=interpretation_trace,
            calculation=calculation_trace,
            raw_taxpayer_data=state.get("taxpayer_data"),
        )

        taxpayer_data = None
        if state.get("taxpayer_data"):
            try:
                taxpayer_data = TaxpayerData.model_validate(state["taxpayer_data"])
            except Exception:
                pass

        retrieved_sections = None
        retrieval_result = state.get("retrieval_result")
        if retrieval_result and retrieval_result.get("sections"):
            try:
                retrieved_sections = [
                    RetrievedSection.model_validate(s)
                    for s in retrieval_result["sections"]
                ]
            except Exception:
                pass

        pipeline_response = PipelineResponse(
            stage="extraction_complete",
            assistant_message=assistant_message,
            questions=None,
            canvas=canvas,
            taxpayer_data=taxpayer_data,
            retrieved_sections=retrieved_sections,
            session_id=session_id,
            turn_number=turn_number,
        )

    # ── FBR Q&A or follow-up answer ─────────────────────────────────────────────
    elif response_stage == "qa_response":
        steps = _build_qa_steps(state)

        retrieval_trace = None
        if state.get("retrieval_trace"):
            try:
                rt = state["retrieval_trace"]
                section_traces = [SectionTrace.model_validate(s) for s in rt.get("selected_sections", [])]
                retrieval_trace = RetrievalTrace(
                    status=rt.get("status", "complete"),
                    query_summary=rt.get("query_summary", ""),
                    selected_sections=section_traces,
                    passes_used=rt.get("passes_used", 1),
                    reasoning=rt.get("reasoning", ""),
                )
            except Exception:
                pass

        canvas = CanvasData(steps=steps, retrieval=retrieval_trace)

        pipeline_response = PipelineResponse(
            stage="extraction_complete",
            assistant_message=assistant_message,
            questions=None,
            canvas=canvas,
            session_id=session_id,
            turn_number=turn_number,
        )

    # ── General greeting / out-of-scope ─────────────────────────────────────────
    else:
        steps = _build_general_steps(state)
        canvas = CanvasData(steps=steps)

        pipeline_response = PipelineResponse(
            stage="extraction_complete",
            assistant_message=assistant_message,
            questions=None,
            canvas=canvas,
            session_id=session_id,
            turn_number=turn_number,
        )

    return {
        "final_response": pipeline_response.model_dump(mode="json"),
        "current_node": "response",
    }
