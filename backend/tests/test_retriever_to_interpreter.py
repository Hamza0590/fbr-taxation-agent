"""
Test 2b: Retriever → Interpreter data flow.
Run from project root: python backend/tests/test_retriever_to_interpreter.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.tax_extractor.models.taxpayer import TaxpayerData
from backend.tax_extractor.models.income import SalaryIncome
from backend.rule_retriever.models import RetrievalResult, RetrievedSection
from backend.tax_interpreter.interpreter import interpret_tax_situation


async def test_retriever_to_interpreter():
    taxpayer_data = TaxpayerData(
        tax_year="2025-2026",
        taxpayer_type="individual",
        residency_status="resident",
        filer_status="filer",
        age_above_60=False,
        disability_status=False,
        salary_income=SalaryIncome(
            basic_salary_annual=2400000.0,
            tax_already_deducted=180000.0,
        ),
        confidence_score=0.95,
        assumptions_made=[],
    )

    retrieval_result = RetrievalResult(
        sections=[
            RetrievedSection(
                node_id="0005",
                title="Chapter 3 — Salary Income (Section 12)",
                content=(
                    "12. Salary.—(1) Any salary received by or accruing to a person in a tax year, "
                    "other than salary that is exempt from tax under this Ordinance, shall be chargeable "
                    "to tax in that year under the head 'Salary'."
                ),
                summary="Defines salary income and its chargeability under the Income Tax Ordinance.",
                line_start=1200,
                line_end=1280,
                depth=2,
                parent_title="Chapter 3",
            ),
            RetrievedSection(
                node_id="0066",
                title="First Schedule — Division I — Salary Slabs (Para 2)",
                content=(
                    "Where the taxable income exceeds Rs.600,000 but does not exceed Rs.1,200,000, "
                    "the rate of tax is 1% of the amount exceeding Rs.600,000. "
                    "Where the taxable income exceeds Rs.1,200,000 but does not exceed Rs.2,200,000, "
                    "the rate of tax is Rs.6,000 plus 11% of the amount exceeding Rs.1,200,000."
                ),
                summary="Salary income tax rate slabs for individuals, Division I, Finance Act 2025.",
                line_start=19324,
                line_end=19343,
                depth=3,
                parent_title="Chapter 13 — First Schedule",
            ),
        ],
        node_ids_selected=["0005", "0066"],
        reasoning="Retrieved salary income head definition and applicable rate slab for a salaried individual.",
        passes_used=1,
        query_used="Salary income computation rules for individual resident filer",
    )

    print("=== INPUT TO INTERPRETER ===")
    print(f"TaxpayerData: salary_income.basic_salary_annual = {taxpayer_data.salary_income.basic_salary_annual:,.0f}")
    print(f"RetrievalResult sections: {len(retrieval_result.sections)}")

    print("\n=== CALLING INTERPRETER ===")
    plan = await interpret_tax_situation(taxpayer_data, retrieval_result)

    print("\n=== INTERPRETATION RESULT ===")
    print(f"TaxComputationPlan type: {type(plan).__name__}")
    print(f"tax_year: {plan.tax_year}")
    print(f"filer_status: {plan.filer_status}")
    print(f"Income classifications: {len(plan.income_classifications)}")
    for ic in plan.income_classifications:
        print(f"  - {ic.source_description}: head={ic.head.value}, regime={ic.tax_regime.value}, schedule={ic.applicable_schedule}")
    print(f"Deductions: {len(plan.deductions)}")
    print(f"Withholding: {len(plan.withholding_classifications)}")
    print(f"Overall reasoning: {plan.overall_reasoning[:200]}...")
    print(f"Caveats: {plan.caveats}")

    assert len(plan.income_classifications) >= 1, "Must have at least 1 income classification"
    assert plan.tax_year == "2025-2026", f"Expected 2025-2026, got {plan.tax_year}"

    print("\n✅ Retriever → Interpreter: DATA FLOWS CORRECTLY")


if __name__ == "__main__":
    asyncio.run(test_retriever_to_interpreter())
