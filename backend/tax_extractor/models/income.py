from pydantic import BaseModel, Field
from typing import Optional, Literal


class SalaryIncome(BaseModel):
    basic_salary_annual: float = Field(description="Annual basic salary in the specified currency")
    allowances: float = Field(default=0.0, description="Total allowances: house rent, medical, conveyance, etc.")
    bonuses: float = Field(default=0.0, description="Annual bonuses received")
    employer_pension_contribution: float = Field(default=0.0, description="Employer's contribution to pension/provident fund")
    tax_already_deducted: float = Field(default=0.0, description="Tax already withheld by employer from salary")


class BusinessIncome(BaseModel):
    gross_revenue: float = Field(description="Total gross revenue/sales")
    total_expenses: float = Field(default=0.0, description="Total allowable business expenses")
    net_profit: float = Field(description="Net profit (revenue minus expenses)")
    business_type: Literal["sole_proprietor", "partnership_share"] = Field(description="Type of business ownership")
    is_sme: bool = Field(default=False, description="Whether the business qualifies as SME under FBR criteria")


class RentalIncome(BaseModel):
    gross_rent_annual: float = Field(description="Total annual rental income")
    property_type: Literal["residential", "commercial"] = Field(description="Type of rented property")
    allowable_deductions: float = Field(default=0.0, description="Deductions: repairs, insurance, property tax paid")


class CapitalGains(BaseModel):
    gain_from_securities: float = Field(default=0.0, description="Capital gain from stocks/securities")
    holding_period_securities: Optional[Literal["less_than_1yr", "1_to_2yr", "2_to_4yr", "above_4yr"]] = Field(default=None)
    gain_from_property: float = Field(default=0.0, description="Capital gain from property sale")
    holding_period_property: Optional[Literal["less_than_1yr", "1_to_2yr", "2_to_4yr", "above_4yr"]] = Field(default=None)


class FreelanceIncome(BaseModel):
    annual_income: float = Field(description="Total annual freelance/remote income")
    income_currency: Literal["PKR", "USD", "EUR", "GBP", "AED", "CAD", "AUD"] = Field(description="Currency in which freelance income is received")
    platform: Optional[str] = Field(default=None, description="Platform used: Upwork, Fiverr, Toptal, direct clients, etc.")
    is_it_export: bool = Field(default=False, description="Whether income qualifies as IT/software export under FBR")
    has_pseb_registration: bool = Field(default=False, description="Whether registered with Pakistan Software Export Board")


class OtherIncome(BaseModel):
    bank_profit: float = Field(default=0.0, description="Profit on savings accounts, fixed deposits, certificates")
    dividends: float = Field(default=0.0, description="Dividend income from shares")
    prize_winnings: float = Field(default=0.0, description="Income from prizes, lotteries, quizzes")


class AgriculturalIncome(BaseModel):
    amount: float = Field(description="Annual agricultural income — exempt from federal tax but affects slab placement")
