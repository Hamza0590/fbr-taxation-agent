from pydantic import BaseModel, Field


class Deductions(BaseModel):
    zakat_paid: float = Field(default=0.0, description="Zakat deducted or paid during the year")
    donations: float = Field(default=0.0, description="Donations to approved non-profit institutions")
    pension_fund_contribution: float = Field(default=0.0, description="Voluntary pension scheme contribution")
    education_expenses: float = Field(default=0.0, description="Tuition fees paid for children")
    health_insurance_premium: float = Field(default=0.0, description="Health insurance premium paid")
    investment_in_shares: float = Field(default=0.0, description="Investment in new shares eligible for tax credit")
    mortgage_interest: float = Field(default=0.0, description="Interest paid on housing loan")
