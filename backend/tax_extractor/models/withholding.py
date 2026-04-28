from pydantic import BaseModel, Field


class WithholdingTaxes(BaseModel):
    tax_on_salary: float = Field(default=0.0, description="Tax already deducted from salary by employer")
    tax_on_bank_profit: float = Field(default=0.0, description="Withholding tax deducted on bank profit")
    tax_on_dividends: float = Field(default=0.0, description="Withholding tax on dividend income")
    tax_on_property: float = Field(default=0.0, description="Advance tax paid on property transactions")
    tax_on_vehicle: float = Field(default=0.0, description="Withholding tax on vehicle registration/token")
    advance_tax_paid: float = Field(default=0.0, description="Quarterly advance tax installments paid")
    other_withholding: float = Field(default=0.0, description="Any other withholding tax collected")
