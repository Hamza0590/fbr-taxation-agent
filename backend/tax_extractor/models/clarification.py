from pydantic import BaseModel, Field
from typing import Optional, Literal


class ClarificationQuestion(BaseModel):
    field_name: str = Field(description="The model field this question is trying to populate, e.g. 'filer_status'")
    question_text: str = Field(description="Natural language question to display to the user")
    options: Optional[list[str]] = Field(
        default=None,
        description="If this is a multiple-choice question, the options. None means open-ended input expected."
    )
    input_type: Literal["choice", "number", "text"] = Field(
        description="What kind of UI input this question needs"
    )
    priority: Literal["required", "optional"] = Field(
        description="'required' = cannot calculate without this. 'optional' = can calculate but result will be less accurate"
    )
