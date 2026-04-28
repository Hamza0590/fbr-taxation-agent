from pydantic import BaseModel
from enum import Enum
from typing import Optional


class IncomeHead(str, Enum):
    SALARY = "salary"
    BUSINESS = "business"
    PROPERTY = "property"
    CAPITAL_GAINS = "capital_gains"
    OTHER_SOURCES = "other_sources"


class TaxRegime(str, Enum):
    NORMAL = "normal"       # Computed via slabs; withholding is adjustable
    FINAL = "final"         # Withholding IS the final tax
    SEPARATE = "separate"   # Taxed separately at special rates (e.g. capital gains)
    EXEMPT = "exempt"       # Not taxable


class IncomeClassification(BaseModel):
    source_description: str
    head: IncomeHead
    applicable_section: str
    annual_amount: int
    tax_regime: TaxRegime
    applicable_schedule: str
    reasoning: str


class DeductionDecision(BaseModel):
    section: str
    type: str
    claimed_amount: int
    allowed: bool
    allowed_amount: int
    cap_rule: Optional[str] = None
    reasoning: str


class TaxCreditDecision(BaseModel):
    section: str
    type: str
    eligible: bool
    credit_amount: Optional[int] = None
    reasoning: str


class ExemptionDecision(BaseModel):
    clause: str
    description: str
    applies: bool
    exempt_amount: Optional[int] = None
    reasoning: str


class WithholdingClassification(BaseModel):
    source: str
    section: str
    amount: int
    regime: TaxRegime
    reasoning: str


class TaxComputationPlan(BaseModel):
    """
    Structured output produced by the LLM tax interpreter.
    Captures legal classification decisions — NOT computed amounts.
    The deterministic tax_calculator module consumes this to produce final tax.
    """
    tax_year: str
    filer_status: str
    residency_status: str
    taxpayer_category: str

    income_classifications: list[IncomeClassification]
    exemptions: list[ExemptionDecision]
    deductions: list[DeductionDecision]
    tax_credits: list[TaxCreditDecision]
    withholding_classifications: list[WithholdingClassification]

    minimum_tax_applicable: bool
    minimum_tax_turnover: Optional[int] = None
    super_tax_applicable: bool

    overall_reasoning: str
    referenced_sections: list[str]
    caveats: list[str]
