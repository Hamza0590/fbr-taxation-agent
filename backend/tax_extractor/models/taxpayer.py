from pydantic import BaseModel, Field
from typing import Optional, Literal
from .income import (
    SalaryIncome, BusinessIncome, RentalIncome,
    CapitalGains, FreelanceIncome, OtherIncome, AgriculturalIncome
)
from .deductions import Deductions
from .withholding import WithholdingTaxes


class TaxpayerData(BaseModel):
    # === Taxpayer Identity & Status ===
    tax_year: str = Field(description="Tax year e.g. '2025-2026'")
    taxpayer_type: Literal["individual", "aop", "company"] = Field(description="Type of taxpayer")
    residency_status: Literal["resident", "non_resident"] = Field(description="Tax residency in Pakistan")
    filer_status: Optional[Literal["filer", "non_filer", "late_filer"]] = Field(default=None, description="FBR filing status — critically affects tax rates")
    age_above_60: bool = Field(default=False, description="Senior citizen status for 50% tax reduction eligibility")
    disability_status: bool = Field(default=False, description="Disabled person for tax reduction eligibility")

    # === Income Sources (all Optional — user may not have all) ===
    salary_income: Optional[SalaryIncome] = None
    business_income: Optional[BusinessIncome] = None
    rental_income: Optional[RentalIncome] = None
    capital_gains: Optional[CapitalGains] = None
    freelance_income: Optional[FreelanceIncome] = None
    other_income: Optional[OtherIncome] = None
    agricultural_income: Optional[AgriculturalIncome] = None

    # === Deductions & Already Paid ===
    deductions: Optional[Deductions] = None
    withholding_taxes: Optional[WithholdingTaxes] = None

    # === Metadata ===
    amounts_currency: Literal["PKR", "USD", "EUR", "GBP", "AED"] = Field(
        default="PKR",
        description="Primary currency of reported amounts"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0,
        description="LLM's self-assessed confidence in the extraction. 1.0 = fully certain, 0.0 = guessing"
    )
    assumptions_made: list[str] = Field(
        default_factory=list,
        description="List of assumptions the LLM made when information was not explicitly stated"
    )
