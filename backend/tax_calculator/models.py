from pydantic import BaseModel
from typing import Optional


class IncomeHeadBreakdown(BaseModel):
    head: str
    source_description: str
    gross_income: int
    applicable_schedule: str
    tax_regime: str

    applicable_slab_min: Optional[int] = None
    applicable_slab_max: Optional[int] = None
    fixed_tax: Optional[int] = None
    rate_percent: Optional[float] = None
    tax_on_excess: Optional[float] = None
    computed_tax: float

    withholding_is_final: bool


class ExemptionApplied(BaseModel):
    clause: str
    description: str
    exempt_amount: int


class DeductionApplied(BaseModel):
    section: str
    type: str
    claimed_amount: int
    allowed_amount: int
    cap_rule: Optional[str] = None


class TaxCreditApplied(BaseModel):
    section: str
    type: str
    credit_amount: float


class WithholdingAdjustment(BaseModel):
    source: str
    section: str
    amount: int
    treatment: str  # "adjusted" | "final"


class TaxCalculationResult(BaseModel):
    """
    Complete, final tax calculation output.
    End product of the Tax Sathi pipeline.
    """
    tax_year: str
    filer_status: str
    taxpayer_category: str

    # ── Income summary ──
    income_breakdowns: list[IncomeHeadBreakdown]
    total_gross_income: int
    exempt_income: int
    total_taxable_income: int

    # ── Deductions ──
    deductions_applied: list[DeductionApplied]
    total_deductions: int
    taxable_income_after_deductions: int

    # ── Tax liability ──
    tax_on_normal_income: float
    tax_on_separate_income: float
    gross_tax_liability: float

    # ── Tax credits ──
    tax_credits_applied: list[TaxCreditApplied]
    total_tax_credits: float
    tax_after_credits: float

    # ── Minimum tax (Section 113) ──
    minimum_tax_applicable: bool
    minimum_tax_amount: Optional[float] = None

    # ── Super tax ──
    super_tax_applicable: bool
    super_tax_amount: Optional[float] = None

    # ── Final liability ──
    total_tax_liability: float

    # ── Withholding adjustments ──
    withholding_adjustments: list[WithholdingAdjustment]
    total_adjustable_withholding: float
    total_final_withholding: float

    # ── Net result ──
    net_tax_payable: float
    refund_due: float
    is_refund: bool

    # ── Meta ──
    effective_tax_rate: float
    computation_notes: list[str]
    caveats_from_interpreter: list[str]

    # ── Summary (human-readable) ──
    summary_text: str
