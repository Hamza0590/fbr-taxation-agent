from pydantic import BaseModel, Field
from typing import Optional, Literal
from .taxpayer import TaxpayerData
from .clarification import ClarificationQuestion


class ExtractionResponse(BaseModel):
    status: Literal["complete", "needs_clarification"] = Field(
        description="'complete' = extraction successful, use extracted_data. 'needs_clarification' = ask the user these questions first."
    )
    extracted_data: Optional[TaxpayerData] = Field(
        default=None,
        description="Populated when status is 'complete'. Contains all extracted tax information."
    )
    questions: Optional[list[ClarificationQuestion]] = Field(
        default=None,
        description="Populated when status is 'needs_clarification'. Questions to ask the user."
    )
    partial_data: Optional[TaxpayerData] = Field(
        default=None,
        description="When status is 'needs_clarification', this contains whatever WAS extractable so far. Used to avoid re-extracting on the next turn."
    )
    message: str = Field(
        description="A natural language message from the assistant to display alongside the result or questions. Conversational, not robotic."
    )
