import logging
import re

from ..state import TaxSathiState
from ...rule_retriever.retriever import retrieve_relevant_sections
from ...rule_retriever.models import RetrievedSection
from ...tax_extractor.models import TaxpayerData

logger = logging.getLogger("pipeline.retrieval_node")


def _infer_relevance(section: RetrievedSection, data: TaxpayerData) -> str:
    title_lower = section.title.lower()

    if "salary" in title_lower:
        if data.salary_income:
            return f"Contains rules for your salary income of PKR {data.salary_income.basic_salary_annual:,.0f}"
        return "Contains salary income computation rules"

    if "property" in title_lower:
        if data.rental_income:
            return f"Contains rules for your {data.rental_income.property_type} rental income"
        return "Contains property income computation rules"

    if "business" in title_lower:
        if data.business_income:
            return f"Contains rules for your {data.business_income.business_type.replace('_', ' ')} business income"
        return "Contains business income computation rules"

    if "capital gain" in title_lower:
        return "Contains capital gains tax rates based on your holding period"

    if "exemption" in title_lower or "concession" in title_lower:
        reasons = []
        if data.age_above_60:
            reasons.append("senior citizen 50% reduction")
        if data.freelance_income and data.freelance_income.is_it_export:
            reasons.append("IT export income exemption")
        if reasons:
            return f"Checking applicable exemptions: {', '.join(reasons)}"
        return "Checking if any exemptions or concessions apply to your situation"

    if "deduction" in title_lower:
        return "Contains rules for allowable deductions that reduce your taxable income"

    if "withholding" in title_lower or "advance tax" in title_lower:
        if data.filer_status == "non_filer":
            return "Non-filers face higher withholding rates — checking applicable rates"
        return "Contains withholding tax provisions relevant to your income sources"

    if "rate" in title_lower or "schedule" in title_lower or "division" in title_lower:
        return "Contains the tax rate table applicable to your income bracket"

    return "Contains provisions relevant to your tax situation"


async def retrieval_node(state: TaxSathiState) -> dict:
    taxpayer_data_dict = state.get("taxpayer_data")
    if not taxpayer_data_dict:
        logger.error("retrieval_node called with no taxpayer_data in state")
        return {
            "retrieval_trace": {
                "status": "failed",
                "query_summary": "",
                "selected_sections": [],
                "passes_used": 0,
                "reasoning": "",
                "error_message": "No taxpayer data available for retrieval",
            },
            "current_node": "retrieval",
        }

    taxpayer_data = TaxpayerData.model_validate(taxpayer_data_dict)

    try:
        retrieval_result = await retrieve_relevant_sections(taxpayer_data)
    except Exception as exc:
        logger.exception("retrieve_relevant_sections failed")
        return {
            "retrieval_trace": {
                "status": "failed",
                "query_summary": "",
                "selected_sections": [],
                "passes_used": 0,
                "reasoning": "",
                "error_message": str(exc),
            },
            "current_node": "retrieval",
        }

    section_traces = []
    for section in retrieval_result.sections:
        section_traces.append({
            "node_id": section.node_id,
            "title": section.title,
            "parent_title": section.parent_title,
            "relevance": _infer_relevance(section, taxpayer_data),
            "content_preview": (
                section.content[:300].strip() + "..."
                if len(section.content) > 300
                else section.content.strip()
            ),
            "full_content": section.content,
            "line_range": f"Lines {section.line_start}-{section.line_end}",
            "section_path": (
                f"{section.parent_title} > {section.title}"
                if section.parent_title
                else section.title
            ),
        })

    retrieval_trace = {
        "status": "complete",
        "query_summary": retrieval_result.query_used,
        "selected_sections": section_traces,
        "passes_used": retrieval_result.passes_used,
        "reasoning": retrieval_result.reasoning,
    }

    return {
        "retrieval_result": retrieval_result.model_dump(mode="json"),
        "retrieval_trace": retrieval_trace,
        "current_node": "retrieval",
    }
