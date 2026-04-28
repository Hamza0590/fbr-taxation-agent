"""
Tax Calculator — pure arithmetic, zero LLM calls.
Consumes TaxComputationPlan from tax_interpreter and produces TaxCalculationResult.
All tax decisions are already made by the interpreter; this module only does math.
"""
import re
import logging
from typing import Optional

from ..tax_interpreter.models import TaxComputationPlan, IncomeClassification, TaxRegime, IncomeHead
from ..tax_rules.lookup import compute_slab_tax, lookup_capital_gains_rate, compute_minimum_tax
from ..tax_rules.rates import get_rates

from .models import (
    TaxCalculationResult,
    IncomeHeadBreakdown,
    DeductionApplied,
    TaxCreditApplied,
    WithholdingAdjustment,
    ExemptionApplied,
)

logger = logging.getLogger("tax_calculator")


# ─── Public entry point ───────────────────────────────────────────────────────

def calculate_tax(plan: TaxComputationPlan) -> TaxCalculationResult:
    """
    Execute the TaxComputationPlan using rate tables.
    Every legal decision has already been made by the interpreter.
    This function only does math.
    """
    try:
        rates = get_rates(plan.tax_year)
    except ValueError:
        rates = get_rates("2025-2026")
        logger.warning("Rates for '%s' not found — falling back to 2025-2026", plan.tax_year)

    notes: list[str] = []

    # ── STEP 1: Compute tax for each income head ──────────────────────────────
    income_breakdowns: list[IncomeHeadBreakdown] = []
    total_gross = 0
    total_exempt = 0
    tax_on_normal = 0.0
    tax_on_separate = 0.0

    for classification in plan.income_classifications:
        breakdown = _compute_income_head_tax(classification, rates, plan.filer_status, notes)
        income_breakdowns.append(breakdown)
        total_gross += classification.annual_amount

        if classification.tax_regime == TaxRegime.EXEMPT:
            total_exempt += classification.annual_amount
            notes.append(
                f"  '{classification.source_description}' is EXEMPT — {classification.reasoning}"
            )
        elif classification.tax_regime == TaxRegime.FINAL:
            notes.append(
                f"  '{classification.source_description}' is under FINAL TAX regime — "
                f"withholding of Rs. {classification.annual_amount:,} is the final tax, no slab lookup."
            )
        elif classification.tax_regime == TaxRegime.SEPARATE:
            tax_on_separate += breakdown.computed_tax
            rate_str = f"{breakdown.rate_percent}%" if breakdown.rate_percent is not None else "N/A"
            notes.append(
                f"  '{classification.source_description}' taxed SEPARATELY at {rate_str}: "
                f"Rs. {breakdown.computed_tax:,.2f}"
            )
        else:  # NORMAL
            tax_on_normal += breakdown.computed_tax
            notes.append(
                f"  '{classification.source_description}' under {breakdown.applicable_schedule}: "
                f"pre-deduction tax = Rs. {breakdown.computed_tax:,.2f}"
            )

    total_taxable = total_gross - total_exempt
    notes.append(
        f"STEP 1 SUMMARY — Gross income: Rs. {total_gross:,} | "
        f"Exempt: Rs. {total_exempt:,} | Taxable: Rs. {total_taxable:,}"
    )
    print(f"\n[CALCULATOR] Step 1: Gross Income: Rs. {total_gross:,}, Taxable: Rs. {total_taxable:,}")

    # ── STEP 2: Apply deductions ──────────────────────────────────────────────
    deductions_applied: list[DeductionApplied] = []
    total_deductions = 0

    for ded in plan.deductions:
        if not ded.allowed:
            notes.append(f"  Deduction u/s {ded.section} ({ded.type}): DISALLOWED — {ded.reasoning}")
            continue

        actual_allowed = _compute_deduction_cap(ded, total_taxable)
        deductions_applied.append(DeductionApplied(
            section=ded.section,
            type=ded.type,
            claimed_amount=ded.claimed_amount,
            allowed_amount=actual_allowed,
            cap_rule=ded.cap_rule,
        ))
        total_deductions += actual_allowed
        cap_note = f" (capped: {ded.cap_rule})" if ded.cap_rule and actual_allowed < ded.claimed_amount else ""
        notes.append(
            f"  Deduction u/s {ded.section} ({ded.type}): "
            f"claimed Rs. {ded.claimed_amount:,}, allowed Rs. {actual_allowed:,}{cap_note}"
        )

    taxable_after_deductions = max(0, total_taxable - total_deductions)
    notes.append(
        f"STEP 2 SUMMARY — Total deductions: Rs. {total_deductions:,} | "
        f"Taxable after deductions: Rs. {taxable_after_deductions:,}"
    )
    print(f"[CALCULATOR] Step 2: Total Deductions: Rs. {total_deductions:,}, Taxable after deductions: Rs. {taxable_after_deductions:,}")

    # ── STEP 3: Recompute normal income tax after deductions ──────────────────
    # Deductions reduce the normal-income taxable base.
    # Sum all NORMAL income, subtract deductions, re-lookup slab on combined amount.
    normal_income_total = sum(
        c.annual_amount
        for c in plan.income_classifications
        if c.tax_regime == TaxRegime.NORMAL
    )
    normal_taxable_after_deductions = max(0, normal_income_total - total_deductions)

    if plan.income_classifications and normal_income_total > 0:
        primary_normal = next(
            (c for c in plan.income_classifications if c.tax_regime == TaxRegime.NORMAL),
            None
        )
        if primary_normal is not None:
            table = _get_table_for_head_and_schedule(
                primary_normal.head.value,
                primary_normal.applicable_schedule,
                rates,
            )
            if table is not None and normal_taxable_after_deductions > 0:
                slab_result = compute_slab_tax(normal_taxable_after_deductions, table)
                tax_on_normal = slab_result["total_tax"]
                notes.append(
                    f"STEP 3 — Re-computed normal income tax after deductions: "
                    f"slab({slab_result['applicable_slab'].min_amount:,}–"
                    f"{slab_result['applicable_slab'].max_amount or '∞'}), "
                    f"fixed Rs. {slab_result['fixed_tax']:,} + "
                    f"{slab_result['applicable_slab'].rate_percent}% on excess "
                    f"Rs. {slab_result['tax_on_excess']:,.2f} = "
                    f"Rs. {tax_on_normal:,.2f}"
                )
            elif normal_taxable_after_deductions == 0:
                tax_on_normal = 0.0
                notes.append("STEP 3 — Normal taxable income is zero after deductions. Tax = Rs. 0.")
            else:
                notes.append(
                    f"STEP 3 — No rate table found for '{primary_normal.applicable_schedule}'. "
                    f"Normal tax remains Rs. {tax_on_normal:,.2f} (pre-deduction figure)."
                )

    # ── STEP 4: Gross tax liability ───────────────────────────────────────────
    gross_liability = round(tax_on_normal + tax_on_separate, 2)
    notes.append(
        f"STEP 4 — Gross tax liability: "
        f"Rs. {tax_on_normal:,.2f} (normal) + Rs. {tax_on_separate:,.2f} (separate) = "
        f"Rs. {gross_liability:,.2f}"
    )

    # ── STEP 5: Apply tax credits ─────────────────────────────────────────────
    credits_applied: list[TaxCreditApplied] = []
    total_credits = 0.0

    for credit in plan.tax_credits:
        if credit.eligible and credit.credit_amount:
            credits_applied.append(TaxCreditApplied(
                section=credit.section,
                type=credit.type,
                credit_amount=float(credit.credit_amount),
            ))
            total_credits += credit.credit_amount
            notes.append(
                f"  Tax credit u/s {credit.section} ({credit.type}): Rs. {credit.credit_amount:,}"
            )

    tax_after_credits = max(0.0, round(gross_liability - total_credits, 2))
    notes.append(
        f"STEP 5 — Tax after credits: "
        f"Rs. {gross_liability:,.2f} - Rs. {total_credits:,.2f} = Rs. {tax_after_credits:,.2f}"
    )

    # ── STEP 6: Minimum tax check (Section 113) ───────────────────────────────
    min_tax_amount: Optional[float] = None
    if plan.minimum_tax_applicable and plan.minimum_tax_turnover:
        min_tax_amount = compute_minimum_tax(plan.minimum_tax_turnover, rates)
        notes.append(
            f"STEP 6 — Minimum tax u/s 113 on turnover Rs. {plan.minimum_tax_turnover:,}: "
            f"Rs. {min_tax_amount:,.2f}"
        )

    # ── STEP 7: Super tax ─────────────────────────────────────────────────────
    super_tax_amount: Optional[float] = None
    if plan.super_tax_applicable and rates.super_tax_slabs is not None:
        super_result = compute_slab_tax(total_taxable, rates.super_tax_slabs)
        super_tax_amount = super_result["total_tax"]
        notes.append(
            f"STEP 7 — Super tax (s.4C) on Rs. {total_taxable:,}: Rs. {super_tax_amount:,.2f}"
        )

    # ── STEP 8: Final liability ───────────────────────────────────────────────
    applicable_tax = tax_after_credits
    if min_tax_amount is not None and min_tax_amount > applicable_tax:
        applicable_tax = min_tax_amount
        notes.append(
            f"STEP 8 — Minimum tax Rs. {min_tax_amount:,.2f} exceeds normal tax "
            f"Rs. {tax_after_credits:,.2f} → minimum tax applies."
        )
    else:
        notes.append(f"STEP 8 — Minimum tax does not apply (normal tax is higher or not applicable).")

    total_liability = round(applicable_tax + (super_tax_amount or 0.0), 2)
    notes.append(
        f"STEP 8 — Total tax liability: "
        f"Rs. {applicable_tax:,.2f} + Rs. {super_tax_amount or 0:.2f} (super tax) = "
        f"Rs. {total_liability:,.2f}"
    )

    # ── STEP 9: Withholding adjustments ──────────────────────────────────────
    adjustments: list[WithholdingAdjustment] = []
    total_adjustable = 0.0
    total_final = 0.0

    for wh in plan.withholding_classifications:
        if wh.regime == TaxRegime.FINAL:
            adjustments.append(WithholdingAdjustment(
                source=wh.source, section=wh.section, amount=wh.amount, treatment="final"
            ))
            total_final += wh.amount
            notes.append(
                f"  Withholding from '{wh.source}' (s.{wh.section}): "
                f"Rs. {wh.amount:,} — FINAL (already settled, informational only)"
            )
        else:  # NORMAL → adjustable
            adjustments.append(WithholdingAdjustment(
                source=wh.source, section=wh.section, amount=wh.amount, treatment="adjusted"
            ))
            total_adjustable += wh.amount
            notes.append(
                f"  Withholding from '{wh.source}' (s.{wh.section}): "
                f"Rs. {wh.amount:,} — ADJUSTABLE (subtracted from liability)"
            )

    notes.append(
        f"STEP 9 — Total adjustable withholding: Rs. {total_adjustable:,.2f} | "
        f"Total final withholding: Rs. {total_final:,.2f}"
    )

    # ── STEP 10: Net result ───────────────────────────────────────────────────
    net_payable = round(max(0.0, total_liability - total_adjustable), 2)
    refund = round(max(0.0, total_adjustable - total_liability), 2)
    is_refund = refund > 0

    if is_refund:
        notes.append(f"STEP 10 — REFUND DUE: Rs. {refund:,.2f}")
        print(f"[CALCULATOR] Step 10: REFUND DUE: Rs. {refund:,.2f}")
    else:
        notes.append(f"STEP 10 — NET TAX PAYABLE: Rs. {net_payable:,.2f}")
        print(f"[CALCULATOR] Step 10: NET TAX PAYABLE: Rs. {net_payable:,.2f}")

    # ── Effective rate ────────────────────────────────────────────────────────
    effective_rate = round((total_liability / total_gross * 100) if total_gross > 0 else 0.0, 2)

    # ── Exemptions applied ────────────────────────────────────────────────────
    # (stored in notes only; not a top-level field in TaxCalculationResult)
    for ex in plan.exemptions:
        if ex.applies:
            notes.append(
                f"  Exemption '{ex.clause}': Rs. {ex.exempt_amount or 0:,} exempt — {ex.description}"
            )

    # ── Summary text ──────────────────────────────────────────────────────────
    summary = _generate_summary_text(
        total_gross=total_gross,
        total_taxable=taxable_after_deductions,
        total_liability=total_liability,
        net_payable=net_payable,
        refund=refund,
        is_refund=is_refund,
        filer_status=plan.filer_status,
        tax_year=plan.tax_year,
    )

    return TaxCalculationResult(
        tax_year=plan.tax_year,
        filer_status=plan.filer_status,
        taxpayer_category=plan.taxpayer_category,
        income_breakdowns=income_breakdowns,
        total_gross_income=total_gross,
        exempt_income=total_exempt,
        total_taxable_income=total_taxable,
        deductions_applied=deductions_applied,
        total_deductions=total_deductions,
        taxable_income_after_deductions=taxable_after_deductions,
        tax_on_normal_income=round(tax_on_normal, 2),
        tax_on_separate_income=round(tax_on_separate, 2),
        gross_tax_liability=gross_liability,
        tax_credits_applied=credits_applied,
        total_tax_credits=round(total_credits, 2),
        tax_after_credits=tax_after_credits,
        minimum_tax_applicable=plan.minimum_tax_applicable,
        minimum_tax_amount=min_tax_amount,
        super_tax_applicable=plan.super_tax_applicable,
        super_tax_amount=super_tax_amount,
        total_tax_liability=total_liability,
        withholding_adjustments=adjustments,
        total_adjustable_withholding=round(total_adjustable, 2),
        total_final_withholding=round(total_final, 2),
        net_tax_payable=net_payable,
        refund_due=refund,
        is_refund=is_refund,
        effective_tax_rate=effective_rate,
        computation_notes=notes,
        caveats_from_interpreter=plan.caveats,
        summary_text=summary,
    )


# ─── Per-head tax computation ─────────────────────────────────────────────────

def _compute_income_head_tax(
    classification: IncomeClassification,
    rates,
    filer_status: str,
    notes: list[str],
) -> IncomeHeadBreakdown:
    head_val = classification.head.value

    if classification.tax_regime == TaxRegime.EXEMPT:
        return IncomeHeadBreakdown(
            head=head_val,
            source_description=classification.source_description,
            gross_income=classification.annual_amount,
            applicable_schedule=classification.applicable_schedule,
            tax_regime="exempt",
            computed_tax=0.0,
            withholding_is_final=False,
        )

    if classification.tax_regime == TaxRegime.FINAL:
        return IncomeHeadBreakdown(
            head=head_val,
            source_description=classification.source_description,
            gross_income=classification.annual_amount,
            applicable_schedule=classification.applicable_schedule,
            tax_regime="final",
            computed_tax=0.0,
            withholding_is_final=True,
        )

    if classification.tax_regime == TaxRegime.SEPARATE:
        if classification.head == IncomeHead.CAPITAL_GAINS:
            return _compute_capital_gains_tax(classification, rates, filer_status, notes)
        # Dividends / profit on debt — flat rate may be embedded in schedule or reasoning
        flat_rate = _extract_flat_rate_from_reasoning(classification.reasoning)
        computed = round(classification.annual_amount * flat_rate / 100.0, 2)
        notes.append(
            f"  '{classification.source_description}' (separate) at {flat_rate}%: Rs. {computed:,.2f}"
        )
        return IncomeHeadBreakdown(
            head=head_val,
            source_description=classification.source_description,
            gross_income=classification.annual_amount,
            applicable_schedule=classification.applicable_schedule,
            tax_regime="separate",
            fixed_tax=0,
            rate_percent=flat_rate,
            computed_tax=computed,
            withholding_is_final=False,
        )

    # NORMAL — slab-based computation
    table = _get_table_for_head_and_schedule(head_val, classification.applicable_schedule, rates)
    if table is None:
        notes.append(
            f"  WARNING: No rate table found for '{classification.applicable_schedule}' "
            f"(head: {head_val}). Tax set to 0 — verify schedule name."
        )
        return IncomeHeadBreakdown(
            head=head_val,
            source_description=classification.source_description,
            gross_income=classification.annual_amount,
            applicable_schedule=classification.applicable_schedule,
            tax_regime="normal",
            computed_tax=0.0,
            withholding_is_final=False,
        )

    slab_result = compute_slab_tax(classification.annual_amount, table)
    slab = slab_result["applicable_slab"]
    return IncomeHeadBreakdown(
        head=head_val,
        source_description=classification.source_description,
        gross_income=classification.annual_amount,
        applicable_schedule=classification.applicable_schedule,
        tax_regime="normal",
        applicable_slab_min=slab.min_amount,
        applicable_slab_max=slab.max_amount,
        fixed_tax=slab_result["fixed_tax"],
        rate_percent=slab.rate_percent,
        tax_on_excess=slab_result["tax_on_excess"],
        computed_tax=slab_result["total_tax"],
        withholding_is_final=False,
    )


def _compute_capital_gains_tax(
    classification: IncomeClassification,
    rates,
    filer_status: str,
    notes: list[str],
) -> IncomeHeadBreakdown:
    holding_years = _extract_holding_period_years(classification)
    schedule_lower = classification.applicable_schedule.lower()

    if "property" in schedule_lower:
        sub_type = "plots"
        if "constructed" in schedule_lower or "house" in schedule_lower:
            sub_type = "constructed"
        elif "flat" in schedule_lower or "apartment" in schedule_lower:
            sub_type = "flats"
        rate = lookup_capital_gains_rate("property", holding_years, filer_status, rates, sub_type)
    else:
        rate = lookup_capital_gains_rate("securities", holding_years, filer_status, rates)

    computed = round(classification.annual_amount * rate / 100.0, 2)
    notes.append(
        f"  Capital gains '{classification.source_description}': holding ~{holding_years:.1f}yr, "
        f"rate {rate}%, tax Rs. {computed:,.2f}"
    )
    return IncomeHeadBreakdown(
        head="capital_gains",
        source_description=classification.source_description,
        gross_income=classification.annual_amount,
        applicable_schedule=classification.applicable_schedule,
        tax_regime="separate",
        fixed_tax=0,
        rate_percent=rate,
        computed_tax=computed,
        withholding_is_final=False,
    )


# ─── Schedule → rate table mapping ───────────────────────────────────────────

def _get_table_for_head_and_schedule(head: str, schedule: str, rates):
    """
    Map income head + schedule string to the appropriate TaxTable.
    Head is the primary signal; schedule string is used as fallback disambiguation.
    """
    # Salary always uses Division I (1A/2) salary slabs
    if head == "salary":
        return rates.salary_slabs

    # Business individuals use Division I (1) / business_individual_slabs
    if head == "business":
        return rates.business_individual_slabs

    # Freelance income is typically treated as business income
    if head == "other_sources" and "business" in schedule.lower():
        return rates.business_individual_slabs

    # Fall back to schedule string matching
    s = schedule.lower().strip()
    if "salary" in s:
        return rates.salary_slabs
    if "division i" in s and "ii" not in s:
        # Could be salary or business — prefer salary for Division I without qualification
        return rates.salary_slabs
    if "division ii" in s and "iii" not in s:
        return rates.business_individual_slabs
    if "business" in s or "aop" in s:
        return rates.business_individual_slabs

    return None  # Unknown schedule — caller logs a warning


# ─── Deduction cap computation ────────────────────────────────────────────────

def _compute_deduction_cap(deduction, total_taxable: int) -> int:
    """
    Apply percentage-based cap if specified in cap_rule.
    E.g. cap_rule='Capped at 30% of taxable income' → cap = 30% * total_taxable.
    Returns min(allowed_amount, cap_amount) when a percentage cap applies.
    """
    if deduction.cap_rule and "%" in deduction.cap_rule:
        match = re.search(r"(\d+(?:\.\d+)?)%", deduction.cap_rule)
        if match:
            cap_pct = float(match.group(1))
            cap_amount = int(total_taxable * cap_pct / 100.0)
            return min(deduction.allowed_amount, cap_amount)
    return deduction.allowed_amount


# ─── Holding period extraction ────────────────────────────────────────────────

def _extract_holding_period_years(classification: IncomeClassification) -> float:
    """
    Try to infer capital gains holding period from reasoning / schedule text.
    Defaults to 0.5 years (< 1 year, highest rate bracket) if not found.
    """
    text = (classification.reasoning + " " + classification.applicable_schedule).lower()

    if "less than 1 year" in text or "< 1 year" in text or "under 1 year" in text or "up to 1 year" in text:
        return 0.5
    if "over 6 years" in text or "more than 6 years" in text or "> 6 years" in text:
        return 7.0

    # "X to Y years" range — use midpoint
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*year", text)
    if match:
        return (float(match.group(1)) + float(match.group(2))) / 2.0

    # Single "X years"
    match = re.search(r"(\d+(?:\.\d+)?)\s*year", text)
    if match:
        return float(match.group(1))

    return 0.5  # conservative default → highest tax rate


def _extract_flat_rate_from_reasoning(reasoning: str) -> float:
    """Extract a percentage rate from the interpreter's reasoning text. Defaults to 15%."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", reasoning)
    if match:
        return float(match.group(1))
    return 15.0


# ─── Summary text ─────────────────────────────────────────────────────────────

def _generate_summary_text(
    total_gross: int,
    total_taxable: int,
    total_liability: float,
    net_payable: float,
    refund: float,
    is_refund: bool,
    filer_status: str,
    tax_year: str,
) -> str:
    status = "filer" if filer_status == "filer" else "non-filer"
    parts = [
        f"For tax year {tax_year}, your total gross income is Rs. {total_gross:,}.",
        f"After applicable exemptions and deductions, your taxable income is Rs. {total_taxable:,}.",
        f"Your total tax liability as a {status} comes to Rs. {total_liability:,.0f}.",
    ]
    if is_refund:
        parts.append(
            f"After adjusting taxes already withheld at source, "
            f"you are due a REFUND of Rs. {refund:,.0f}."
        )
    elif net_payable > 0:
        parts.append(
            f"After adjusting taxes already withheld at source, "
            f"you need to pay Rs. {net_payable:,.0f} as remaining tax."
        )
    else:
        parts.append(
            "Your withholding taxes have fully covered your liability — "
            "no additional payment is needed."
        )
    return " ".join(parts)
