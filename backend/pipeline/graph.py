from langgraph.graph import StateGraph, END

from .state import TaxSathiState
from .nodes import (
    router_node,
    extraction_node,
    retrieval_node,
    interpretation_node,
    calculation_node,
    fbr_qa_node,
    followup_node,
    general_node,
    response_node,
)


# ── Conditional edge functions ─────────────────────────────────────────────────

def route_by_intent(state: TaxSathiState) -> str:
    intent = state.get("intent", "general_greeting")
    if intent == "tax_calculation":
        return "extraction"
    elif intent == "fbr_policy_qa":
        return "fbr_qa"
    elif intent == "follow_up":
        return "followup"
    else:  # general_greeting, out_of_scope
        return "general"


def route_after_extraction(state: TaxSathiState) -> str:
    """Continue to retrieval, or return clarification questions to user."""
    if state.get("extraction_status") == "needs_clarification":
        return "response"
    return "retrieval"


def route_after_followup(state: TaxSathiState) -> str:
    """If clarification was pending, re-run extraction; otherwise format response."""
    if state.get("extraction_status") == "needs_clarification":
        return "extraction"
    return "response"


# ── Build the graph ────────────────────────────────────────────────────────────

workflow = StateGraph(TaxSathiState)

workflow.add_node("router", router_node)
workflow.add_node("extraction", extraction_node)
workflow.add_node("retrieval", retrieval_node)
workflow.add_node("interpretation", interpretation_node)
workflow.add_node("calculation", calculation_node)
workflow.add_node("fbr_qa", fbr_qa_node)
workflow.add_node("followup", followup_node)
workflow.add_node("general", general_node)
workflow.add_node("response", response_node)

workflow.set_entry_point("router")

workflow.add_conditional_edges("router", route_by_intent, {
    "extraction": "extraction",
    "fbr_qa": "fbr_qa",
    "followup": "followup",
    "general": "general",
})
workflow.add_conditional_edges("extraction", route_after_extraction, {
    "response": "response",
    "retrieval": "retrieval",
})
workflow.add_edge("retrieval", "interpretation")
workflow.add_edge("interpretation", "calculation")
workflow.add_edge("calculation", "response")
workflow.add_edge("fbr_qa", "response")
workflow.add_conditional_edges("followup", route_after_followup, {
    "extraction": "extraction",
    "response": "response",
})
workflow.add_edge("general", "response")
workflow.add_edge("response", END)

tax_sathi_graph = workflow.compile()
