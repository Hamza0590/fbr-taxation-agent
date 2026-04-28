import logging

from ..state import TaxSathiState
from ..helpers import build_calculation_trace
from ...tax_calculator.calculator import calculate_tax
from ...tax_interpreter.models import TaxComputationPlan

logger = logging.getLogger("pipeline.calculation_node")


async def calculation_node(state: TaxSathiState) -> dict:
    interpretation_result_dict = state.get("interpretation_result")

    if not interpretation_result_dict:
        logger.error("calculation_node called with no interpretation_result in state")
        return {
            "calculation_trace": {
                "status": "failed",
                "total_gross_income": 0, "exempt_income": 0, "total_taxable_income": 0,
                "total_deductions": 0, "taxable_income_after_deductions": 0,
                "tax_on_normal_income": 0.0, "tax_on_separate_income": 0.0,
                "gross_tax_liability": 0.0, "total_tax_credits": 0.0, "tax_after_credits": 0.0,
                "minimum_tax_applicable": False, "super_tax_applicable": False,
                "total_tax_liability": 0.0, "total_adjustable_withholding": 0.0,
                "total_final_withholding": 0.0, "net_tax_payable": 0.0,
                "refund_due": 0.0, "is_refund": False, "effective_tax_rate": 0.0,
                "income_breakdowns": [], "deductions_applied": [], "tax_credits_applied": [],
                "withholding_adjustments": [], "computation_notes": [], "caveats": [],
                "summary_text": "",
                "error_message": "No interpretation result available",
            },
            "current_node": "calculation",
        }

    try:
        plan = TaxComputationPlan.model_validate(interpretation_result_dict)
        calc_result = calculate_tax(plan)
    except Exception as exc:
        logger.exception("calculate_tax failed")
        return {
            "calculation_trace": {
                "status": "failed",
                "total_gross_income": 0, "exempt_income": 0, "total_taxable_income": 0,
                "total_deductions": 0, "taxable_income_after_deductions": 0,
                "tax_on_normal_income": 0.0, "tax_on_separate_income": 0.0,
                "gross_tax_liability": 0.0, "total_tax_credits": 0.0, "tax_after_credits": 0.0,
                "minimum_tax_applicable": False, "super_tax_applicable": False,
                "total_tax_liability": 0.0, "total_adjustable_withholding": 0.0,
                "total_final_withholding": 0.0, "net_tax_payable": 0.0,
                "refund_due": 0.0, "is_refund": False, "effective_tax_rate": 0.0,
                "income_breakdowns": [], "deductions_applied": [], "tax_credits_applied": [],
                "withholding_adjustments": [], "computation_notes": [], "caveats": [],
                "summary_text": "",
                "error_message": str(exc),
            },
            "current_node": "calculation",
        }

    calculation_trace = build_calculation_trace(calc_result)

    return {
        "calculation_result": calc_result.model_dump(mode="json"),
        "calculation_trace": calculation_trace.model_dump(),
        "assistant_message": calc_result.summary_text,
        "response_stage": "extraction_complete",
        "current_node": "calculation",
    }
