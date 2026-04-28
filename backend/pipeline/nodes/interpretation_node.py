import logging

from ..state import TaxSathiState
from ..helpers import build_interpretation_trace
from ...tax_interpreter.interpreter import interpret_tax_situation
from ...tax_extractor.models import TaxpayerData
from ...rule_retriever.models import RetrievalResult, RetrievedSection

logger = logging.getLogger("pipeline.interpretation_node")


async def interpretation_node(state: TaxSathiState) -> dict:
    taxpayer_data_dict = state.get("taxpayer_data")
    retrieval_result_dict = state.get("retrieval_result")

    if not taxpayer_data_dict or not retrieval_result_dict:
        logger.error("interpretation_node missing taxpayer_data or retrieval_result")
        return {
            "interpretation_trace": {
                "status": "failed",
                "income_classifications": [],
                "exemptions": [],
                "deductions": [],
                "tax_credits": [],
                "withholding": [],
                "minimum_tax_applicable": False,
                "super_tax_applicable": False,
                "overall_reasoning": "",
                "caveats": [],
                "referenced_sections": [],
                "error_message": "Missing input data",
            },
            "current_node": "interpretation",
        }

    taxpayer_data = TaxpayerData.model_validate(taxpayer_data_dict)
    retrieval_result = RetrievalResult.model_validate(retrieval_result_dict)

    try:
        plan = await interpret_tax_situation(taxpayer_data, retrieval_result)
    except Exception as exc:
        logger.exception("interpret_tax_situation failed")
        return {
            "interpretation_trace": {
                "status": "failed",
                "income_classifications": [],
                "exemptions": [],
                "deductions": [],
                "tax_credits": [],
                "withholding": [],
                "minimum_tax_applicable": False,
                "super_tax_applicable": False,
                "overall_reasoning": "",
                "caveats": [],
                "referenced_sections": [],
                "error_message": str(exc),
            },
            "current_node": "interpretation",
        }

    interpretation_trace = build_interpretation_trace(plan)

    return {
        "interpretation_result": plan.model_dump(mode="json"),
        "interpretation_trace": interpretation_trace.model_dump(),
        "current_node": "interpretation",
    }
