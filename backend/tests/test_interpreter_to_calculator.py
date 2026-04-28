"""
Test 2c: Interpreter → Calculator data flow.
Run from project root: python backend/tests/test_interpreter_to_calculator.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.tax_interpreter.models import (
    TaxComputationPlan, IncomeClassification, IncomeHead, TaxRegime,
    DeductionDecision, ExemptionDecision, TaxCreditDecision, WithholdingClassification,
)
from backend.tax_calculator.calculator import calculate_tax


def test_interpreter_to_calculator():
    plan = TaxComputationPlan(
        tax_year="2025-2026",
        filer_status="filer",
        residency_status="resident",
        taxpayer_category="individual",
        income_classifications=[
            IncomeClassification(
                source_description="Monthly salary from ABC Software Company",
                head=IncomeHead.SALARY,
                applicable_section="Section 12",
                annual_amount=2400000,
                tax_regime=TaxRegime.NORMAL,
                applicable_schedule="Division I — Salary",
                reasoning="Regular employment salary falls under Section 12, taxed via Division I of First Schedule.",
            )
        ],
        exemptions=[],
        deductions=[
            DeductionDecision(
                section="Section 60",
                type="zakat",
                claimed_amount=50000,
                allowed=True,
                allowed_amount=50000,
                cap_rule=None,
                reasoning="Compulsory zakat deducted under Section 60 is fully allowable.",
            )
        ],
        tax_credits=[],
        withholding_classifications=[
            WithholdingClassification(
                source="Salary withholding by employer",
                section="149",
                amount=180000,
                regime=TaxRegime.NORMAL,
                reasoning="Salary withholding under Section 149 is adjustable against final tax liability.",
            )
        ],
        minimum_tax_applicable=False,
        minimum_tax_turnover=None,
        super_tax_applicable=False,
        overall_reasoning=(
            "Simple salaried individual with one income source. "
            "Zakat deduction is fully allowed. "
            "Employer withholding is adjustable."
        ),
        referenced_sections=["Section 12", "Section 60", "Section 149", "Division I"],
        caveats=[],
    )

    print("=== INPUT PLAN ===")
    print(f"Income sources: {len(plan.income_classifications)}")
    print(f"Deductions: {len(plan.deductions)}")
    print(f"Withholdings: {len(plan.withholding_classifications)}")

    result = calculate_tax(plan)

    print("\n=== CALCULATION RESULT ===")
    print(f"Total gross income:          Rs. {result.total_gross_income:>12,}")
    print(f"Exempt income:               Rs. {result.exempt_income:>12,}")
    print(f"Total taxable income:        Rs. {result.total_taxable_income:>12,}")
    print(f"Total deductions:            Rs. {result.total_deductions:>12,}")
    print(f"Taxable after deductions:    Rs. {result.taxable_income_after_deductions:>12,}")
    print(f"Tax on normal income:        Rs. {result.tax_on_normal_income:>12,.2f}")
    print(f"Gross tax liability:         Rs. {result.gross_tax_liability:>12,.2f}")
    print(f"Total adjustable WHT:        Rs. {result.total_adjustable_withholding:>12,.2f}")
    print(f"Net payable:                 Rs. {result.net_tax_payable:>12,.2f}")
    print(f"Refund due:                  Rs. {result.refund_due:>12,.2f}")
    print(f"Is refund:                   {result.is_refund}")
    print(f"Effective rate:              {result.effective_tax_rate}%")
    print(f"\nSummary: {result.summary_text}")
    print(f"\nComputation notes ({len(result.computation_notes)}):")
    for note in result.computation_notes:
        print(f"  {note}")

    # Sanity checks
    assert result.total_gross_income == 2400000, f"Gross income mismatch: {result.total_gross_income}"
    assert result.total_deductions == 50000, f"Deductions mismatch: {result.total_deductions}"
    assert result.taxable_income_after_deductions == 2350000, (
        f"Taxable after deductions mismatch: {result.taxable_income_after_deductions}"
    )
    assert result.tax_on_normal_income > 0, "Tax on 2.35M income must be > 0"
    assert result.total_adjustable_withholding == 180000.0, (
        f"Withholding mismatch: {result.total_adjustable_withholding}"
    )

    # Verify slab math for 2,350,000 income:
    # Falls in slab 2,200,000 – 3,200,000: Rs.116,000 + 23% of (2,350,000 – 2,200,000)
    # = 116,000 + 23% * 150,000 = 116,000 + 34,500 = 150,500
    expected_tax = 116_000 + 0.23 * (2_350_000 - 2_200_000)
    assert abs(result.tax_on_normal_income - expected_tax) < 1.0, (
        f"Slab math wrong: expected Rs.{expected_tax:,.2f}, got Rs.{result.tax_on_normal_income:,.2f}"
    )
    print(f"\nSlab math verified: Rs. {result.tax_on_normal_income:,.2f} (expected Rs. {expected_tax:,.2f}) ✅")

    print("\n✅ Interpreter → Calculator: DATA FLOWS CORRECTLY")


if __name__ == "__main__":
    test_interpreter_to_calculator()
