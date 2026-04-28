from pydantic import BaseModel


class TaxSlab(BaseModel):
    """Single row in a bracket-based tax table."""
    min_amount: int
    max_amount: int | None
    fixed_tax: int
    rate_percent: float


class TaxTable(BaseModel):
    """A complete bracket-based tax table (e.g., salary slabs)."""
    description: str
    tax_year: str
    slabs: list[TaxSlab]


class FlatRate(BaseModel):
    """A simple flat rate for capital gains or similar."""
    condition: str
    rate_percent: float
    filer_rate: float | None = None
    non_filer_rate: float | None = None


class WithholdingRate(BaseModel):
    """Withholding tax rate entry."""
    section: str
    description: str
    filer_rate: float
    non_filer_rate: float
    is_final: bool


class TaxYearRates(BaseModel):
    """All rates for a single tax year — master container."""
    tax_year: str

    # Income tax slabs
    salary_slabs: TaxTable               # Division I (1A/2): salary > 75% of taxable income
    business_individual_slabs: TaxTable  # Division I (1): non-salaried individuals
    business_aop_slabs: TaxTable | None  # AOPs — same as individual from FA2024+
    business_company_rate: float         # Flat rate for general companies (Division II)
    business_company_rate_small: float   # Small company rate
    business_company_rate_banking: float # Banking company rate

    # Capital gains (Division VII)
    capital_gains_securities: list[FlatRate]   # By holding period
    capital_gains_property_plots: list[FlatRate]
    capital_gains_property_constructed: list[FlatRate]
    capital_gains_property_flats: list[FlatRate]

    # Dividend / profit on debt (Divisions III, IIIA)
    dividend_rate_general: float     # Division III — general dividend rate
    dividend_rate_ipp: float         # Division III — IPP pass-through rate
    profit_on_debt_rate_bank: float  # Division IIIA — bank/FI accounts
    profit_on_debt_rate_other: float # Division IIIA — other cases

    # Withholding (Part III, First Schedule)
    withholding_rates: list[WithholdingRate]

    # Minimum tax (Division IX)
    minimum_tax_rate_general: float
    minimum_tax_rate_sui_gas_airlines_poultry: float
    minimum_tax_rate_distributors_pharma: float

    # Super tax (Division IIB — Section 4C, for incomes > Rs.150 million)
    super_tax_slabs: TaxTable | None
