"""
Trace-builder helpers: convert domain model outputs into canvas-friendly
trace objects for the frontend.
"""
from ..tax_extractor.models.response import ExtractionResponse
from ..tax_interpreter.models import TaxComputationPlan
from ..tax_calculator.models import TaxCalculationResult
from .models import (
    ExtractionTrace,
    InterpretationTrace, IncomeClassificationTrace,
    CalculationTrace, IncomeBreakdownTrace,
)


def build_interpretation_trace(plan: TaxComputationPlan) -> InterpretationTrace:
    income_traces = [
        IncomeClassificationTrace(
            source_description=ic.source_description,
            head=ic.head.value,
            tax_regime=ic.tax_regime.value,
            annual_amount=ic.annual_amount,
            applicable_section=ic.applicable_section,
            applicable_schedule=ic.applicable_schedule,
            reasoning=ic.reasoning,
        )
        for ic in plan.income_classifications
    ]
    exemptions = [
        {
            "clause": e.clause,
            "description": e.description,
            "applies": e.applies,
            "exempt_amount": e.exempt_amount,
            "reasoning": e.reasoning,
        }
        for e in plan.exemptions
    ]
    deductions = [
        {
            "type": d.type,
            "section": d.section,
            "allowed": d.allowed,
            "claimed_amount": d.claimed_amount,
            "allowed_amount": d.allowed_amount,
            "cap_rule": d.cap_rule,
            "reasoning": d.reasoning,
        }
        for d in plan.deductions
    ]
    tax_credits = [
        {
            "type": tc.type,
            "section": tc.section,
            "eligible": tc.eligible,
            "credit_amount": tc.credit_amount,
            "reasoning": tc.reasoning,
        }
        for tc in plan.tax_credits
    ]
    withholding = [
        {
            "source": wc.source,
            "section": wc.section,
            "amount": wc.amount,
            "regime": wc.regime.value,
            "reasoning": wc.reasoning,
        }
        for wc in plan.withholding_classifications
    ]
    return InterpretationTrace(
        status="complete",
        income_classifications=income_traces,
        exemptions=exemptions,
        deductions=deductions,
        tax_credits=tax_credits,
        withholding=withholding,
        minimum_tax_applicable=plan.minimum_tax_applicable,
        super_tax_applicable=plan.super_tax_applicable,
        overall_reasoning=plan.overall_reasoning,
        caveats=plan.caveats,
        referenced_sections=plan.referenced_sections,
    )


def build_calculation_trace(result: TaxCalculationResult) -> CalculationTrace:
    income_rows = [
        IncomeBreakdownTrace(
            head=b.head,
            source_description=b.source_description,
            gross_income=b.gross_income,
            tax_regime=b.tax_regime,
            applicable_schedule=b.applicable_schedule,
            computed_tax=b.computed_tax,
            rate_percent=b.rate_percent,
            withholding_is_final=b.withholding_is_final,
        )
        for b in result.income_breakdowns
    ]
    deductions = [
        {
            "section": d.section,
            "type": d.type,
            "claimed_amount": d.claimed_amount,
            "allowed_amount": d.allowed_amount,
            "cap_rule": d.cap_rule,
        }
        for d in result.deductions_applied
    ]
    credits = [
        {"section": c.section, "type": c.type, "credit_amount": c.credit_amount}
        for c in result.tax_credits_applied
    ]
    withholding = [
        {
            "source": w.source,
            "section": w.section,
            "amount": w.amount,
            "treatment": w.treatment,
        }
        for w in result.withholding_adjustments
    ]
    return CalculationTrace(
        status="complete",
        total_gross_income=result.total_gross_income,
        exempt_income=result.exempt_income,
        total_taxable_income=result.total_taxable_income,
        total_deductions=result.total_deductions,
        taxable_income_after_deductions=result.taxable_income_after_deductions,
        tax_on_normal_income=result.tax_on_normal_income,
        tax_on_separate_income=result.tax_on_separate_income,
        gross_tax_liability=result.gross_tax_liability,
        total_tax_credits=result.total_tax_credits,
        tax_after_credits=result.tax_after_credits,
        minimum_tax_applicable=result.minimum_tax_applicable,
        minimum_tax_amount=result.minimum_tax_amount,
        super_tax_applicable=result.super_tax_applicable,
        super_tax_amount=result.super_tax_amount,
        total_tax_liability=result.total_tax_liability,
        total_adjustable_withholding=result.total_adjustable_withholding,
        total_final_withholding=result.total_final_withholding,
        net_tax_payable=result.net_tax_payable,
        refund_due=result.refund_due,
        is_refund=result.is_refund,
        effective_tax_rate=result.effective_tax_rate,
        income_breakdowns=income_rows,
        deductions_applied=deductions,
        tax_credits_applied=credits,
        withholding_adjustments=withholding,
        computation_notes=result.computation_notes,
        caveats=result.caveats_from_interpreter,
        summary_text=result.summary_text,
    )


def build_extraction_trace(extraction_result: ExtractionResponse) -> ExtractionTrace:
    data = extraction_result.extracted_data or extraction_result.partial_data
    status = "complete" if extraction_result.status == "complete" else "partial"

    if data is None:
        return ExtractionTrace(
            status="partial",
            extracted_fields={},
            missing_fields=["All fields — no information extracted yet"],
            assumptions=[],
            confidence=0.0,
            confidence_label="No Data",
        )

    extracted_fields: dict = {}

    extracted_fields["Tax Year"] = data.tax_year
    extracted_fields["Taxpayer Type"] = data.taxpayer_type.replace("_", " ").title()
    extracted_fields["Residency"] = data.residency_status.replace("_", " ").title()
    if data.filer_status:
        extracted_fields["Filer Status"] = data.filer_status.replace("_", " ").title()
    if data.age_above_60:
        extracted_fields["Senior Citizen"] = "Yes (50% reduction eligible)"
    if data.disability_status:
        extracted_fields["Disability Status"] = "Yes (reduction eligible)"

    if data.salary_income:
        s = data.salary_income
        extracted_fields["Salary (Annual)"] = f"PKR {s.basic_salary_annual:,.0f}"
        if s.allowances and s.allowances > 0:
            extracted_fields["Allowances"] = f"PKR {s.allowances:,.0f}"
        if s.bonuses and s.bonuses > 0:
            extracted_fields["Bonuses"] = f"PKR {s.bonuses:,.0f}"
        if s.tax_already_deducted and s.tax_already_deducted > 0:
            extracted_fields["Tax Withheld (Salary)"] = f"PKR {s.tax_already_deducted:,.0f}"

    if data.business_income:
        b = data.business_income
        extracted_fields["Business Revenue"] = f"PKR {b.gross_revenue:,.0f}"
        extracted_fields["Business Net Profit"] = f"PKR {b.net_profit:,.0f}"
        extracted_fields["Business Type"] = b.business_type.replace("_", " ").title()

    if data.rental_income:
        r = data.rental_income
        extracted_fields["Rental Income (Annual)"] = f"PKR {r.gross_rent_annual:,.0f}"
        extracted_fields["Property Type"] = r.property_type.title()

    if data.capital_gains:
        cg = data.capital_gains
        if cg.gain_from_securities and cg.gain_from_securities > 0:
            extracted_fields["Capital Gain (Securities)"] = f"PKR {cg.gain_from_securities:,.0f}"
        if cg.gain_from_property and cg.gain_from_property > 0:
            extracted_fields["Capital Gain (Property)"] = f"PKR {cg.gain_from_property:,.0f}"

    if data.freelance_income:
        fi = data.freelance_income
        extracted_fields["Freelance Income"] = f"PKR {fi.annual_income:,.0f}"
        if fi.platform:
            extracted_fields["Platform"] = fi.platform
        if fi.is_it_export:
            extracted_fields["IT Export"] = "Yes (potential exemption)"

    if data.other_income:
        o = data.other_income
        if o.bank_profit and o.bank_profit > 0:
            extracted_fields["Bank Profit"] = f"PKR {o.bank_profit:,.0f}"
        if o.dividends and o.dividends > 0:
            extracted_fields["Dividends"] = f"PKR {o.dividends:,.0f}"

    if data.agricultural_income:
        extracted_fields["Agricultural Income"] = f"PKR {data.agricultural_income.amount:,.0f}"

    if data.deductions:
        d = data.deductions
        deduction_items = []
        if d.zakat_paid and d.zakat_paid > 0:
            deduction_items.append(f"Zakat: PKR {d.zakat_paid:,.0f}")
        if d.donations and d.donations > 0:
            deduction_items.append(f"Donations: PKR {d.donations:,.0f}")
        if d.pension_fund_contribution and d.pension_fund_contribution > 0:
            deduction_items.append(f"Pension: PKR {d.pension_fund_contribution:,.0f}")
        if deduction_items:
            extracted_fields["Deductions"] = ", ".join(deduction_items)

    missing: list[str] = []
    if extraction_result.questions:
        for q in extraction_result.questions:
            missing.append(q.field_name.replace("_", " ").title())

    confidence = data.confidence_score
    if confidence >= 0.8:
        label = "High"
    elif confidence >= 0.5:
        label = "Medium"
    else:
        label = "Low"

    return ExtractionTrace(
        status=status,
        extracted_fields=extracted_fields,
        missing_fields=missing,
        assumptions=data.assumptions_made,
        confidence=confidence,
        confidence_label=label,
    )
