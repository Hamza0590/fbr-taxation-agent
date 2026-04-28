"""
python -m backend.tax_interpreter

Runs a sample interpretation to verify the module works end-to-end.
"""
import asyncio
import json

from ..tax_extractor.models.taxpayer import TaxpayerData
from ..tax_extractor.models.income import SalaryIncome
from ..tax_extractor.models.withholding import WithholdingTaxes
from ..rule_retriever.models import RetrievalResult, RetrievedSection
from .interpreter import interpret_tax_situation


SAMPLE_TAXPAYER = TaxpayerData(
    tax_year="2025-2026",
    taxpayer_type="individual",
    residency_status="resident",
    filer_status="filer",
    age_above_60=False,
    disability_status=False,
    salary_income=SalaryIncome(
        basic_salary_annual=2_400_000,
        allowances=240_000,
        bonuses=0,
        employer_pension_contribution=0,
        tax_already_deducted=45_000,
    ),
    withholding_taxes=WithholdingTaxes(
        tax_on_salary=45_000,
    ),
    confidence_score=0.95,
    assumptions_made=["Salary is the only income source"],
)

SAMPLE_RETRIEVAL = RetrievalResult(
    sections=[
        RetrievedSection(
            node_id="ch3-s12",
            title="Section 12 — Salary Income",
            content=(
                "12. Income from salary.—(1) Salary of a person for a tax year shall be "
                "chargeable to tax in Pakistan under the head 'Salary'.\n"
                "(2) Salary includes pay, wages, overtime pay, bonus, commissions, fees, "
                "gratuity or work condition supplements."
            ),
            summary="Defines what constitutes salary income under the head Salary.",
            line_start=2492,
            line_end=2520,
            depth=3,
            parent_title="Chapter 3 — Tax on Taxable Income",
        ),
        RetrievedSection(
            node_id="ch13-div1",
            title="Division I — Rates of Tax for Individuals (Salary)",
            content=(
                "Where the income of an individual chargeable under the head 'salary' "
                "exceeds seventy-five per cent of his taxable income, the rates of tax "
                "to be applied shall be:\n"
                "1. ≤600,000: 0%\n"
                "2. 600,001-1,200,000: 1% of amount exceeding 600,000\n"
                "3. 1,200,001-2,200,000: Rs.6,000 + 11% exceeding 1,200,000\n"
                "4. 2,200,001-3,200,000: Rs.116,000 + 23% exceeding 2,200,000\n"
                "5. 3,200,001-4,100,000: Rs.346,000 + 30% exceeding 3,200,000\n"
                "6. Above 4,100,000: Rs.616,000 + 35% exceeding 4,100,000"
            ),
            summary="Salary income tax slabs as per Finance Act 2025 (para 2, Division I).",
            line_start=19281,
            line_end=19343,
            depth=3,
            parent_title="Chapter 13 — First Schedule Part I",
        ),
        RetrievedSection(
            node_id="ch3-s149",
            title="Section 149 — Withholding on Salary",
            content=(
                "149. Salary.—(1) Every employer paying salary to an employee shall "
                "deduct tax from the salary at the rate specified in Division I of Part I "
                "of the First Schedule. The tax so deducted shall be treated as advance "
                "tax paid by the employee and is adjustable against the final tax liability."
            ),
            summary="Employer withholds salary tax; deduction is adjustable, not final.",
            line_start=12000,
            line_end=12020,
            depth=3,
            parent_title="Chapter 10 — Procedure",
        ),
    ],
    node_ids_selected=["ch3-s12", "ch13-div1", "ch3-s149"],
    reasoning="Taxpayer has salary income — retrieved salary charging section, rate table, and withholding provision.",
    passes_used=1,
    query_used="salary income tax computation salaried individual Pakistan 2025-2026",
)


async def main():
    print("=" * 60)
    print("Tax Interpreter Module — Sample Run")
    print("=" * 60)
    print("\nTaxpayer: Salaried individual, salary PKR 2,400,000/yr")
    print("Running interpretation...\n")

    plan = await interpret_tax_situation(SAMPLE_TAXPAYER, SAMPLE_RETRIEVAL)

    print(json.dumps(plan.model_dump(), indent=2, default=str))
    print("\n" + "=" * 60)
    print("Interpretation complete.")


if __name__ == "__main__":
    asyncio.run(main())
