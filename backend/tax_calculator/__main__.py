"""
Standalone test runner for the tax calculator module.
Usage: python -m backend.tax_calculator
"""
from .calculator import calculate_tax
from ..tax_interpreter.models import (
    TaxComputationPlan,
    IncomeClassification,
    DeductionDecision,
    TaxCreditDecision,
    ExemptionDecision,
    WithholdingClassification,
    IncomeHead,
    TaxRegime,
)


# ─── Test helpers ─────────────────────────────────────────────────────────────

def _print_result(label: str, plan: TaxComputationPlan) -> None:
    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")

    # Input summary
    print("\n── INPUT SUMMARY ──")
    for ic in plan.income_classifications:
        print(f"  [{ic.tax_regime.value.upper()}] {ic.source_description}: Rs. {ic.annual_amount:,} ({ic.applicable_schedule})")
    for d in plan.deductions:
        if d.allowed:
            cap = f" [{d.cap_rule}]" if d.cap_rule else ""
            print(f"  [DEDUCTION] u/s {d.section} {d.type}: Rs. {d.claimed_amount:,}{cap}")
    for wh in plan.withholding_classifications:
        print(f"  [WITHHOLDING] {wh.source}: Rs. {wh.amount:,} ({wh.regime.value})")

    result = calculate_tax(plan)

    # Computation notes
    print("\n── COMPUTATION NOTES ──")
    for note in result.computation_notes:
        print(f"  {note}")

    # Key numbers
    print("\n── RESULT ──")
    print(f"  Total Gross Income:           Rs. {result.total_gross_income:>12,}")
    print(f"  Exempt Income:                Rs. {result.exempt_income:>12,}")
    print(f"  Taxable Income:               Rs. {result.total_taxable_income:>12,}")
    print(f"  Total Deductions:             Rs. {result.total_deductions:>12,}")
    print(f"  Taxable After Deductions:     Rs. {result.taxable_income_after_deductions:>12,}")
    print(f"  Tax on Normal Income:         Rs. {result.tax_on_normal_income:>12,.2f}")
    print(f"  Tax on Separate Income:       Rs. {result.tax_on_separate_income:>12,.2f}")
    print(f"  Gross Tax Liability:          Rs. {result.gross_tax_liability:>12,.2f}")
    if result.total_tax_credits:
        print(f"  Tax Credits:                  Rs. {result.total_tax_credits:>12,.2f}")
    if result.minimum_tax_amount:
        print(f"  Minimum Tax (s.113):          Rs. {result.minimum_tax_amount:>12,.2f}")
    if result.super_tax_amount:
        print(f"  Super Tax (s.4C):             Rs. {result.super_tax_amount:>12,.2f}")
    print(f"  Total Tax Liability:          Rs. {result.total_tax_liability:>12,.2f}")
    print(f"  Adjustable Withholding:       Rs. {result.total_adjustable_withholding:>12,.2f}")
    if result.is_refund:
        print(f"  ** REFUND DUE:                Rs. {result.refund_due:>12,.2f} **")
    else:
        print(f"  ** NET TAX PAYABLE:           Rs. {result.net_tax_payable:>12,.2f} **")
    print(f"  Effective Tax Rate:           {result.effective_tax_rate:>11.2f}%")

    # Summary
    print(f"\n── SUMMARY ──\n  {result.summary_text}")

    if result.caveats_from_interpreter:
        print("\n── CAVEATS ──")
        for c in result.caveats_from_interpreter:
            print(f"  ⚠  {c}")


# ─── Test 1: Simple salaried individual ──────────────────────────────────────

plan1 = TaxComputationPlan(
    tax_year="2025-2026",
    filer_status="filer",
    residency_status="resident",
    taxpayer_category="salaried_individual",
    income_classifications=[
        IncomeClassification(
            source_description="Salary from ABC Corp",
            head=IncomeHead.SALARY,
            applicable_section="Section 12",
            annual_amount=2_400_000,
            tax_regime=TaxRegime.NORMAL,
            applicable_schedule="Division I (1A/2) — Salary Income",
            reasoning="Employment income taxable under salary head.",
        )
    ],
    exemptions=[],
    deductions=[],
    tax_credits=[],
    withholding_classifications=[
        WithholdingClassification(
            source="ABC Corp (employer)",
            section="149",
            amount=180_000,
            regime=TaxRegime.NORMAL,
            reasoning="Employer withholds tax on salary; adjustable against final liability.",
        )
    ],
    minimum_tax_applicable=False,
    super_tax_applicable=False,
    overall_reasoning="Simple salaried individual with no other income.",
    referenced_sections=["Section 12", "Division I First Schedule"],
    caveats=[],
)

# ─── Test 2: Salaried + Business income ──────────────────────────────────────

plan2 = TaxComputationPlan(
    tax_year="2025-2026",
    filer_status="filer",
    residency_status="resident",
    taxpayer_category="individual",
    income_classifications=[
        IncomeClassification(
            source_description="Salary from XYZ Ltd",
            head=IncomeHead.SALARY,
            applicable_section="Section 12",
            annual_amount=1_800_000,
            tax_regime=TaxRegime.NORMAL,
            applicable_schedule="Division I (1A/2) — Salary Income",
            reasoning="Employment income under salary head.",
        ),
        IncomeClassification(
            source_description="Freelance software services",
            head=IncomeHead.BUSINESS,
            applicable_section="Section 18",
            annual_amount=1_200_000,
            tax_regime=TaxRegime.NORMAL,
            applicable_schedule="Division II — Business Income",
            reasoning="Freelance IT services constitute business income.",
        ),
    ],
    exemptions=[],
    deductions=[
        DeductionDecision(
            section="60",
            type="zakat",
            claimed_amount=50_000,
            allowed=True,
            allowed_amount=50_000,
            cap_rule=None,
            reasoning="Zakat paid is deductible u/s 60.",
        )
    ],
    tax_credits=[],
    withholding_classifications=[
        WithholdingClassification(
            source="XYZ Ltd (employer)",
            section="149",
            amount=120_000,
            regime=TaxRegime.NORMAL,
            reasoning="Salary withholding — adjustable.",
        ),
        WithholdingClassification(
            source="Bank profit",
            section="151",
            amount=15_000,
            regime=TaxRegime.FINAL,
            reasoning="Profit on debt withholding u/s 151 is final for filers.",
        ),
    ],
    minimum_tax_applicable=False,
    super_tax_applicable=False,
    overall_reasoning="Salaried employee with side freelance business.",
    referenced_sections=["Section 12", "Section 18", "Section 60", "Division I", "Division II"],
    caveats=["Freelance income requires separate computation under business head."],
)

# ─── Test 3: Multiple income sources with exemptions ─────────────────────────

plan3 = TaxComputationPlan(
    tax_year="2025-2026",
    filer_status="filer",
    residency_status="resident",
    taxpayer_category="individual",
    income_classifications=[
        IncomeClassification(
            source_description="Salary from DEF Bank",
            head=IncomeHead.SALARY,
            applicable_section="Section 12",
            annual_amount=3_600_000,
            tax_regime=TaxRegime.NORMAL,
            applicable_schedule="Division I (1A/2) — Salary Income",
            reasoning="Banking sector salary under salary head.",
        ),
        IncomeClassification(
            source_description="Rental income from commercial property",
            head=IncomeHead.PROPERTY,
            applicable_section="Section 15",
            annual_amount=600_000,
            tax_regime=TaxRegime.NORMAL,
            applicable_schedule="Division VI — Property Income",
            reasoning="Commercial rental income taxable under property head.",
        ),
        IncomeClassification(
            source_description="Capital gain on listed securities (held < 1 year)",
            head=IncomeHead.CAPITAL_GAINS,
            applicable_section="Section 37A",
            annual_amount=200_000,
            tax_regime=TaxRegime.SEPARATE,
            applicable_schedule="Division VII — Capital Gains on Securities",
            reasoning="Short-term capital gain on securities taxed separately. Held less than 1 year — highest rate applies.",
        ),
        IncomeClassification(
            source_description="Agricultural income",
            head=IncomeHead.OTHER_SOURCES,
            applicable_section="Section 41",
            annual_amount=500_000,
            tax_regime=TaxRegime.EXEMPT,
            applicable_schedule="Second Schedule — Exempt Income",
            reasoning="Agricultural income is exempt from federal income tax under Section 41.",
        ),
    ],
    exemptions=[
        ExemptionDecision(
            clause="Section 41 / Second Schedule",
            description="Agricultural income is exempt from federal income tax.",
            applies=True,
            exempt_amount=500_000,
            reasoning="Confirmed exempt under federal law; subject only to provincial agricultural income tax.",
        )
    ],
    deductions=[
        DeductionDecision(
            section="61",
            type="donation",
            claimed_amount=200_000,
            allowed=True,
            allowed_amount=200_000,
            cap_rule="Capped at 30% of taxable income",
            reasoning="Donation to approved NPO u/s 61 — allowed subject to 30% of taxable income cap.",
        )
    ],
    tax_credits=[],
    withholding_classifications=[
        WithholdingClassification(
            source="DEF Bank (employer salary)",
            section="149",
            amount=300_000,
            regime=TaxRegime.NORMAL,
            reasoning="Employer salary withholding — adjustable.",
        ),
        WithholdingClassification(
            source="Property tax at source",
            section="155",
            amount=30_000,
            regime=TaxRegime.NORMAL,
            reasoning="Section 155 withholding on rental income is adjustable for filers.",
        ),
    ],
    minimum_tax_applicable=False,
    super_tax_applicable=False,
    overall_reasoning=(
        "High-income individual with salary, rental, capital gains, and exempt agricultural income. "
        "Donation deduction capped at 30% of taxable income."
    ),
    referenced_sections=["Section 12", "Section 15", "Section 37A", "Section 41", "Section 61", "Division I", "Division VII"],
    caveats=[
        "Property income schedule not in current rate table — taxed at 0 (verify with updated rates).",
        "Agricultural income exempt federally; verify provincial agricultural tax separately.",
    ],
)


# ─── Run all tests ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _print_result("TEST 1 — Simple salaried individual (Rs. 2.4M salary)", plan1)
    _print_result("TEST 2 — Salaried + Business income with Zakat deduction", plan2)
    _print_result("TEST 3 — Multiple sources: salary + rental + capital gains + agricultural (exempt)", plan3)
    print(f"\n{'='*70}")
    print("  All tests complete.")
    print(f"{'='*70}\n")
