from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tax_extractor.models import TaxpayerData


def _fmt(amount: float) -> str:
    """Format a float amount with commas for readability."""
    return f"PKR {amount:,.0f}"


def build_retrieval_query(data: "TaxpayerData") -> str:
    """
    Convert structured TaxpayerData into a natural language retrieval query.
    The query tells the tree-reasoning LLM exactly what to look for.
    """
    lines: list[str] = []

    # ── Taxpayer profile ──────────────────────────────────────────────────────
    lines.append("Taxpayer Profile:")
    lines.append(f"- Type: {data.taxpayer_type.capitalize()}")
    lines.append(f"- Residency: {data.residency_status.replace('_', ' ').capitalize()}")

    filer_status_val = data.filer_status or "unknown"
    filer_label = filer_status_val.replace("_", " ").capitalize()
    if data.filer_status == "non_filer":
        filer_label += " (IMPORTANT: higher withholding rates apply)"
    elif data.filer_status == "late_filer":
        filer_label += " (late filer — surcharge may apply)"
    elif data.filer_status is None:
        filer_label += " (not specified — assuming filer)"
    lines.append(f"- Filer Status: {filer_label}")

    if data.age_above_60:
        lines.append("- Age: Above 60 (SENIOR CITIZEN — 50% tax reduction may apply)")
    else:
        lines.append("- Age Above 60: No")

    if data.disability_status:
        lines.append("- Disability Status: Yes (tax reduction may apply)")

    # ── Income sources ────────────────────────────────────────────────────────
    income_heads: list[str] = []
    lines.append("\nIncome Sources Present:")

    if data.salary_income:
        s = data.salary_income
        parts = [f"Annual basic salary {_fmt(s.basic_salary_annual)}"]
        if s.allowances:
            parts.append(f"allowances {_fmt(s.allowances)}")
        if s.bonuses:
            parts.append(f"bonuses {_fmt(s.bonuses)}")
        if s.tax_already_deducted:
            parts.append(f"tax already deducted {_fmt(s.tax_already_deducted)}")
        lines.append(f"- Salary Income: {', '.join(parts)}")
        income_heads.append("salary income")

    if data.business_income:
        b = data.business_income
        lines.append(
            f"- Business Income: Gross revenue {_fmt(b.gross_revenue)}, "
            f"net profit {_fmt(b.net_profit)}, type: {b.business_type.replace('_', ' ')}"
            + (" (SME)" if b.is_sme else "")
        )
        income_heads.append("business income")

    if data.rental_income:
        r = data.rental_income
        lines.append(
            f"- Rental Income: Annual gross rent {_fmt(r.gross_rent_annual)} "
            f"from {r.property_type} property"
        )
        income_heads.append("property/rental income")

    if data.capital_gains:
        cg = data.capital_gains
        parts = []
        if cg.gain_from_securities:
            period = cg.holding_period_securities or "unspecified period"
            parts.append(f"securities gain {_fmt(cg.gain_from_securities)} (held {period.replace('_', ' ')})")
        if cg.gain_from_property:
            period = cg.holding_period_property or "unspecified period"
            parts.append(f"property gain {_fmt(cg.gain_from_property)} (held {period.replace('_', ' ')})")
        if parts:
            lines.append(f"- Capital Gains: {', '.join(parts)}")
            income_heads.append("capital gains")

    if data.freelance_income:
        fi = data.freelance_income
        currency = fi.income_currency
        amount_str = f"{currency} {fi.annual_income:,.0f}"
        extras = []
        if fi.platform:
            extras.append(f"platform: {fi.platform}")
        if fi.is_it_export:
            extras.append("IT EXPORT INCOME — check IT export exemption provisions")
        if fi.has_pseb_registration:
            extras.append("PSEB registered")
        line = f"- Freelance Income: Annual {amount_str}"
        if extras:
            line += f" ({', '.join(extras)})"
        lines.append(line)
        income_heads.append("freelance/IT export income" if fi.is_it_export else "freelance income")

    if data.other_income:
        oi = data.other_income
        parts = []
        if oi.bank_profit:
            parts.append(f"bank profit {_fmt(oi.bank_profit)}")
        if oi.dividends:
            parts.append(f"dividends {_fmt(oi.dividends)}")
        if oi.prize_winnings:
            parts.append(f"prize winnings {_fmt(oi.prize_winnings)}")
        if parts:
            lines.append(f"- Other Income: {', '.join(parts)}")
            income_heads.append("other sources income")

    if data.agricultural_income:
        lines.append(f"- Agricultural Income: {_fmt(data.agricultural_income.amount)} (exempt from federal tax)")
        income_heads.append("agricultural income")

    if not income_heads:
        lines.append("- (No specific income sources provided)")

    # ── Deductions ────────────────────────────────────────────────────────────
    if data.deductions:
        d = data.deductions
        ded_parts = []
        if d.zakat_paid:
            ded_parts.append(f"Zakat {_fmt(d.zakat_paid)}")
        if d.donations:
            ded_parts.append(f"Donations {_fmt(d.donations)}")
        if d.pension_fund_contribution:
            ded_parts.append(f"Pension fund {_fmt(d.pension_fund_contribution)}")
        if d.education_expenses:
            ded_parts.append(f"Education expenses {_fmt(d.education_expenses)}")
        if d.health_insurance_premium:
            ded_parts.append(f"Health insurance {_fmt(d.health_insurance_premium)}")
        if d.investment_in_shares:
            ded_parts.append(f"Share investment {_fmt(d.investment_in_shares)}")
        if d.mortgage_interest:
            ded_parts.append(f"Mortgage interest {_fmt(d.mortgage_interest)}")
        if ded_parts:
            lines.append(f"\nDeductions Claimed:\n- {chr(10)+'- '.join(ded_parts)}")

    # ── Withholding taxes ─────────────────────────────────────────────────────
    if data.withholding_taxes:
        wt = data.withholding_taxes
        wt_parts = []
        if wt.tax_on_salary:
            wt_parts.append(f"Tax on salary {_fmt(wt.tax_on_salary)}")
        if wt.tax_on_bank_profit:
            wt_parts.append(f"Tax on bank profit {_fmt(wt.tax_on_bank_profit)}")
        if wt.tax_on_dividends:
            wt_parts.append(f"Tax on dividends {_fmt(wt.tax_on_dividends)}")
        if wt.tax_on_property:
            wt_parts.append(f"Advance tax on property {_fmt(wt.tax_on_property)}")
        if wt.advance_tax_paid:
            wt_parts.append(f"Advance tax paid {_fmt(wt.advance_tax_paid)}")
        if wt.other_withholding:
            wt_parts.append(f"Other withholding {_fmt(wt.other_withholding)}")
        if wt_parts:
            lines.append(f"\nWithholding Taxes Paid:\n- {chr(10)+'- '.join(wt_parts)}")

    # ── Taxpayer-type specific retrieval hints ────────────────────────────────
    taxpayer_type_val = str(data.taxpayer_type).lower() if data.taxpayer_type else "individual"
    if "aop" in taxpayer_type_val:
        lines.append(
            "\nAOP (Association of Persons) taxpayer — must retrieve: "
            "AOP Association of Persons Section 92 Section 93 Section 94 "
            "minimum tax Section 113 AOP turnover threshold PKR 100M "
            "Division I Non-Salaried AOP Slabs First Schedule."
        )
    elif "company" in taxpayer_type_val:
        lines.append(
            "\nCompany taxpayer — must retrieve: "
            "company corporate tax Section 113 Fourth Schedule "
            "corporate rate 29 percent small company 20 percent "
            "paid-up capital turnover threshold super tax Section 4C."
        )

    # ── Closing instruction ───────────────────────────────────────────────────
    heads_str = ", ".join(income_heads) if income_heads else "general income"
    lines.append(
        f"\nI need to find: rules for computing {heads_str}, "
        "applicable exemptions and concessions, tax credit provisions, "
        "and any special conditions for this taxpayer profile."
    )

    # ── Assumptions note ──────────────────────────────────────────────────────
    if data.assumptions_made:
        lines.append(
            "\nNote: the following were assumed and may need verification: "
            + "; ".join(data.assumptions_made)
        )

    return "\n".join(lines)
