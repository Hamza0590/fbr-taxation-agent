"""
python -m backend.tax_rules

Runs example lookups to verify the rate tables are correct.
"""
from .rates import get_rates
from .lookup import compute_slab_tax, lookup_capital_gains_rate, compute_minimum_tax


def fmt(amount: float) -> str:
    return f"PKR {amount:,.2f}"


def main():
    rates = get_rates("2025-2026")

    print("=" * 60)
    print("Tax Rules Module — 2025-2026 Verification")
    print("=" * 60)

    # ── Example 1: Salary income of 2,400,000 ────────────────────
    print("\n[1] Salary income: PKR 2,400,000 (salary > 75% of taxable income)")
    result = compute_slab_tax(2_400_000, rates.salary_slabs)
    print(f"    Fixed tax:     {fmt(result['fixed_tax'])}")
    print(f"    Tax on excess: {fmt(result['tax_on_excess'])}")
    print(f"    Total tax:     {fmt(result['total_tax'])}")
    print(f"    Effective rate:{result['effective_rate']:.2f}%")

    # ── Example 2: Business income of 5,000,000 ──────────────────
    print("\n[2] Business (non-salaried individual) income: PKR 5,000,000")
    result = compute_slab_tax(5_000_000, rates.business_individual_slabs)
    print(f"    Fixed tax:     {fmt(result['fixed_tax'])}")
    print(f"    Tax on excess: {fmt(result['tax_on_excess'])}")
    print(f"    Total tax:     {fmt(result['total_tax'])}")
    print(f"    Effective rate:{result['effective_rate']:.2f}%")

    # ── Example 3: Capital gains on securities held 6 months ──────
    print("\n[3] Capital gains — securities held 6 months (filer)")
    rate = lookup_capital_gains_rate("securities", 0.5, "filer", rates)
    print(f"    Applicable rate: {rate}%")

    print("\n[4] Capital gains — securities held 6 months (non-filer)")
    rate = lookup_capital_gains_rate("securities", 0.5, "non_filer", rates)
    print(f"    Applicable rate: {rate}%")

    # ── Example 4: Capital gains on property (open plot, 2 years) ─
    print("\n[5] Capital gains — open plot held 2 years (filer)")
    rate = lookup_capital_gains_rate("property", 2.0, "filer", rates, "plots")
    print(f"    Applicable rate: {rate}%")

    # ── Example 5: Minimum tax on turnover ───────────────────────
    print("\n[6] Minimum tax (Section 113) — turnover PKR 10,000,000 (general)")
    min_tax = compute_minimum_tax(10_000_000, rates, "general")
    print(f"    Minimum tax: {fmt(min_tax)} (rate: {rates.minimum_tax_rate_general}%)")

    # ── Example 6: Company tax ────────────────────────────────────
    print("\n[7] Company rates for Tax Year 2025-2026")
    print(f"    General company:  {rates.business_company_rate}%")
    print(f"    Small company:    {rates.business_company_rate_small}%")
    print(f"    Banking company:  {rates.business_company_rate_banking}%")

    print("\n" + "=" * 60)
    print("All lookups completed successfully.")


if __name__ == "__main__":
    main()
