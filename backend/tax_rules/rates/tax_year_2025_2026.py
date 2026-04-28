"""
Tax rates for Tax Year 2025-2026 (Income Tax Ordinance 2001).
All numbers extracted from Chapter 13 (First Schedule) of fbr_combined.md.
Finance Act 2025 tables are used where substitutions occurred.
"""
from ..models import (
    TaxSlab, TaxTable, FlatRate, WithholdingRate, TaxYearRates
)

# ─── Division I (1A/2) — Salary Income ────────────────────────────────────────
# Applies when salary income exceeds 75% of total taxable income.
# Source: First Schedule Part I, para (2), substituted by Finance Act 2025.
# fbr_combined.md lines 19324–19343.
_salary_slabs = TaxTable(
    description="Division I — Salary Income (salary > 75% of taxable income)",
    tax_year="2025-2026",
    slabs=[
        # min_amount is the threshold (exclusive lower bound); excess = amount - min_amount
        TaxSlab(min_amount=0,         max_amount=600_000,   fixed_tax=0,       rate_percent=0.0),
        TaxSlab(min_amount=600_000,   max_amount=1_200_000, fixed_tax=0,       rate_percent=1.0),
        TaxSlab(min_amount=1_200_000, max_amount=2_200_000, fixed_tax=6_000,   rate_percent=11.0),
        TaxSlab(min_amount=2_200_000, max_amount=3_200_000, fixed_tax=116_000, rate_percent=23.0),
        TaxSlab(min_amount=3_200_000, max_amount=4_100_000, fixed_tax=346_000, rate_percent=30.0),
        TaxSlab(min_amount=4_100_000, max_amount=None,      fixed_tax=616_000, rate_percent=35.0),
    ],
)

# ─── Division I (1) — Non-Salaried Individual / AOP ───────────────────────────
# Applies to non-salaried individuals and AOPs.
# Source: First Schedule Part I, para (1), substituted by Finance Act 2025.
# fbr_combined.md lines 19237–19256.
# Proviso: for professional AOPs prohibited from incorporating, the 45% rate
# at S.No. 6 is reduced to 40% (fbr_combined.md line 19279).
_business_individual_slabs = TaxTable(
    description="Division I — Non-Salaried Individual & AOP Income",
    tax_year="2025-2026",
    slabs=[
        # min_amount is the threshold (exclusive lower bound); excess = amount - min_amount
        TaxSlab(min_amount=0,         max_amount=600_000,   fixed_tax=0,         rate_percent=0.0),
        TaxSlab(min_amount=600_000,   max_amount=1_200_000, fixed_tax=0,         rate_percent=15.0),
        TaxSlab(min_amount=1_200_000, max_amount=1_600_000, fixed_tax=90_000,    rate_percent=20.0),
        TaxSlab(min_amount=1_600_000, max_amount=3_200_000, fixed_tax=170_000,   rate_percent=30.0),
        TaxSlab(min_amount=3_200_000, max_amount=5_600_000, fixed_tax=650_000,   rate_percent=40.0),
        TaxSlab(min_amount=5_600_000, max_amount=None,      fixed_tax=1_610_000, rate_percent=45.0),
    ],
)

# ─── Division II — Company Rates ───────────────────────────────────────────────
# Source: First Schedule Part I, Division II, as amended by Finance Act 2025.
# fbr_combined.md lines 19475–19485.
# Tax Year 2025: Banking company 44%, Small company 20%, Other 29%.
_company_rate_general = 29.0
_company_rate_small = 20.0
_company_rate_banking = 44.0

# ─── Division VII — Capital Gains on Securities ────────────────────────────────
# Source: First Schedule Part I, Division VII, Finance Act 2025.
# fbr_combined.md lines 19984–20074.
# For securities acquired on or after 1 July 2022; filer rates.
# Non-filer rate = max(15%, applicable Division I rate) per the proviso.
_capital_gains_securities = [
    FlatRate(condition="holding_period_up_to_1_year",    filer_rate=15.0,  non_filer_rate=15.0, rate_percent=15.0),
    FlatRate(condition="holding_period_1_to_2_years",    filer_rate=12.5,  non_filer_rate=15.0, rate_percent=12.5),
    FlatRate(condition="holding_period_2_to_3_years",    filer_rate=10.0,  non_filer_rate=15.0, rate_percent=10.0),
    FlatRate(condition="holding_period_3_to_4_years",    filer_rate=7.5,   non_filer_rate=15.0, rate_percent=7.5),
    FlatRate(condition="holding_period_4_to_5_years",    filer_rate=5.0,   non_filer_rate=15.0, rate_percent=5.0),
    FlatRate(condition="holding_period_5_to_6_years",    filer_rate=2.5,   non_filer_rate=15.0, rate_percent=2.5),
    FlatRate(condition="holding_period_over_6_years",    filer_rate=0.0,   non_filer_rate=15.0, rate_percent=0.0),
    FlatRate(condition="future_commodity_contracts_pme", filer_rate=5.0,   non_filer_rate=5.0,  rate_percent=5.0),
]

# ─── Division VIII — Capital Gains on Immovable Property ──────────────────────
# Source: First Schedule Part I, Division VIII, Finance Act 2024.
# fbr_combined.md lines 20154–20201.
# For properties acquired on or before 30 June 2024.
_capital_gains_property_plots = [
    FlatRate(condition="holding_period_up_to_1_year",  rate_percent=15.0),
    FlatRate(condition="holding_period_1_to_2_years",  rate_percent=12.5),
    FlatRate(condition="holding_period_2_to_3_years",  rate_percent=10.0),
    FlatRate(condition="holding_period_3_to_4_years",  rate_percent=7.5),
    FlatRate(condition="holding_period_4_to_5_years",  rate_percent=5.0),
    FlatRate(condition="holding_period_5_to_6_years",  rate_percent=2.5),
    FlatRate(condition="holding_period_over_6_years",  rate_percent=0.0),
]

_capital_gains_property_constructed = [
    FlatRate(condition="holding_period_up_to_1_year",  rate_percent=15.0),
    FlatRate(condition="holding_period_1_to_2_years",  rate_percent=10.0),
    FlatRate(condition="holding_period_2_to_3_years",  rate_percent=7.5),
    FlatRate(condition="holding_period_3_to_4_years",  rate_percent=5.0),
    FlatRate(condition="holding_period_over_4_years",  rate_percent=0.0),
]

_capital_gains_property_flats = [
    FlatRate(condition="holding_period_up_to_1_year",  rate_percent=15.0),
    FlatRate(condition="holding_period_1_to_2_years",  rate_percent=7.5),
    FlatRate(condition="holding_period_over_2_years",  rate_percent=0.0),
]

# ─── Division IIB — Super Tax on High Earners (Section 4C) ────────────────────
# Source: fbr_combined.md lines 19555–19606. Tax Year 2026 and onwards column.
_super_tax_slabs = TaxTable(
    description="Division IIB — Super Tax (Section 4C), Tax Year 2026 and onwards",
    tax_year="2025-2026",
    slabs=[
        # Super tax is levied on the full income at the applicable rate (not marginal)
        TaxSlab(min_amount=0,           max_amount=150_000_000, fixed_tax=0, rate_percent=0.0),
        TaxSlab(min_amount=150_000_000, max_amount=200_000_000, fixed_tax=0, rate_percent=1.0),
        TaxSlab(min_amount=200_000_000, max_amount=250_000_000, fixed_tax=0, rate_percent=1.5),
        TaxSlab(min_amount=250_000_000, max_amount=300_000_000, fixed_tax=0, rate_percent=2.5),
        TaxSlab(min_amount=300_000_000, max_amount=350_000_000, fixed_tax=0, rate_percent=3.5),
        TaxSlab(min_amount=350_000_000, max_amount=400_000_000, fixed_tax=0, rate_percent=5.5),
        TaxSlab(min_amount=400_000_000, max_amount=500_000_000, fixed_tax=0, rate_percent=7.5),
        TaxSlab(min_amount=500_000_000, max_amount=None,        fixed_tax=0, rate_percent=10.0),
    ],
)

# ─── Part III — Key Withholding Tax Rates ──────────────────────────────────────
# Source: First Schedule Part III (fbr_combined.md, Part III sections).
# Only the most common sections are listed here. Full schedule in Part III.
_withholding_rates = [
    WithholdingRate(
        section="149",
        description="Salary — deducted by employer at applicable slab rate",
        filer_rate=0.0,     # Variable — computed from salary slabs
        non_filer_rate=0.0, # Variable — same
        is_final=False,     # Adjustable against final tax liability
    ),
    WithholdingRate(
        section="151",
        description="Profit on debt (bank accounts, government securities)",
        filer_rate=15.0,
        non_filer_rate=30.0,
        is_final=False,  # Adjustable for individuals via Section 7B
    ),
    WithholdingRate(
        section="153(1)(a)",
        description="Payments for goods — to companies and registered persons",
        filer_rate=1.0,
        non_filer_rate=2.0,
        is_final=False,
    ),
    WithholdingRate(
        section="153(1)(b)",
        description="Payments for services — to companies",
        filer_rate=8.0,
        non_filer_rate=14.0,
        is_final=False,
    ),
    WithholdingRate(
        section="153(1)(b)-sme",
        description="Payments for services — to SMEs",
        filer_rate=3.0,
        non_filer_rate=6.0,
        is_final=False,
    ),
    WithholdingRate(
        section="153(1)(c)",
        description="Payments on execution of contracts",
        filer_rate=7.0,
        non_filer_rate=12.0,
        is_final=False,
    ),
    WithholdingRate(
        section="155",
        description="Rental income — deducted at applicable slab rate",
        filer_rate=0.0,     # Variable — computed from rental slab
        non_filer_rate=0.0,
        is_final=False,
    ),
    WithholdingRate(
        section="231A",
        description="Cash withdrawal from bank exceeding threshold",
        filer_rate=0.6,
        non_filer_rate=1.2,
        is_final=False,
    ),
    WithholdingRate(
        section="236",
        description="Advance tax on sale/transfer of immovable property",
        filer_rate=1.0,
        non_filer_rate=2.0,
        is_final=False,
    ),
    WithholdingRate(
        section="5",
        description="Dividend income — general rate (Division III)",
        filer_rate=15.0,
        non_filer_rate=30.0,
        is_final=True,   # Dividend WHT is generally a final tax
    ),
    WithholdingRate(
        section="7B",
        description="Profit on debt — final tax for individuals (Division IIIA)",
        filer_rate=15.0,
        non_filer_rate=30.0,
        is_final=True,
    ),
]

# ─── Division IX — Minimum Tax (Section 113) ──────────────────────────────────
# Source: fbr_combined.md lines 20250–20310.
_minimum_tax_rate_general = 1.25        # All other cases
_minimum_tax_rate_sui_gas = 0.75        # Sui Gas Companies, PIA, poultry industry
_minimum_tax_rate_distributors = 0.25  # Distributors of pharma/FMCG, petroleum agents

# ─── Master TaxYearRates Object ────────────────────────────────────────────────
TAX_YEAR_2025_2026 = TaxYearRates(
    tax_year="2025-2026",

    salary_slabs=_salary_slabs,
    business_individual_slabs=_business_individual_slabs,
    business_aop_slabs=_business_individual_slabs,   # Shared from FA2024 onwards
    business_company_rate=_company_rate_general,
    business_company_rate_small=_company_rate_small,
    business_company_rate_banking=_company_rate_banking,

    capital_gains_securities=_capital_gains_securities,
    capital_gains_property_plots=_capital_gains_property_plots,
    capital_gains_property_constructed=_capital_gains_property_constructed,
    capital_gains_property_flats=_capital_gains_property_flats,

    dividend_rate_general=15.0,    # Division III (b) — general case
    dividend_rate_ipp=7.5,         # Division III (a) — IPP pass-through
    profit_on_debt_rate_bank=20.0, # Division IIIA (a) — bank/FI deposits
    profit_on_debt_rate_other=15.0, # Division IIIA (c) — other cases

    withholding_rates=_withholding_rates,

    minimum_tax_rate_general=_minimum_tax_rate_general,
    minimum_tax_rate_sui_gas_airlines_poultry=_minimum_tax_rate_sui_gas,
    minimum_tax_rate_distributors_pharma=_minimum_tax_rate_distributors,

    super_tax_slabs=_super_tax_slabs,
)
