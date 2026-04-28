from pydantic import BaseModel, Field
from typing import Optional, Literal
from ..tax_extractor.models import TaxpayerData
from ..tax_extractor.models.clarification import ClarificationQuestion
from ..rule_retriever.models import RetrievedSection


class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    ntn_number: Optional[str] = None

class ProfileRequest(BaseModel):
    access_token: str
    
# backend/pipeline/models.py

class ProfileUpdate(BaseModel):
    # We will get the token from headers instead, so we only need the data here
    full_name: Optional[str] = None
    email: Optional[str] = None
    cnic: Optional[str] = None
    ntn: Optional[str] = None
    filer_status: Optional[str] = None
    residency_status: Optional[str] = None
    city: Optional[str] = None
    income: Optional[list] = None
    deductions: Optional[dict] = None
    preferences: Optional[dict] = None


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: Literal["user", "assistant"]
    content: str


class PipelineRequest(BaseModel):
    """What the frontend sends to the pipeline."""
    message: str
    conversation_history: Optional[list[ChatMessage]] = None
    session_id: Optional[str] = None
    profile_context: Optional[str] = None  # Formatted profile snapshot when "Use Profile" is on


# === Processing Trace Models (for the frontend canvas) ===

class ExtractionTrace(BaseModel):
    """
    Shows what the extractor understood from the user's message.
    Displayed in the canvas even during clarification turns.
    """
    status: Literal["complete", "partial", "failed"]

    # What was extracted — the structured fields with their values
    extracted_fields: dict  # flattened key-value pairs for display

    # What's missing — fields the system still needs
    missing_fields: list[str]

    # Assumptions made by the LLM
    assumptions: list[str]

    # Confidence indicator
    confidence: float  # 0.0 to 1.0
    confidence_label: str  # "High", "Medium", "Low" — for display


class SectionTrace(BaseModel):
    """
    One retrieved FBR section — rendered as a collapsible card in the canvas.
    """
    node_id: str
    title: str
    parent_title: Optional[str] = None
    relevance: str                  # Why this section matters for this user
    content_preview: str            # First 300 chars of actual content
    full_content: str               # Full section text
    line_range: str                 # "Lines 2554-2854"
    section_path: str               # "Chapter 3 > Part 2" — breadcrumb


class RetrievalTrace(BaseModel):
    """
    Shows which FBR document sections were retrieved and why.
    Displayed in the canvas after extraction is complete.
    """
    status: Literal["complete", "skipped", "failed"]

    # The query that was built from TaxpayerData
    query_summary: str

    # Which nodes the LLM selected and why
    selected_sections: list[SectionTrace]

    # How many passes were used
    passes_used: int

    # LLM's reasoning — displayed as a quote in the canvas
    reasoning: str

    # If retrieval failed, why
    error_message: Optional[str] = None


class ProcessingStep(BaseModel):
    """
    A single step in the processing pipeline.
    The canvas renders these as a vertical timeline/stepper.
    """
    step_number: int
    step_name: str
    status: Literal["completed", "in_progress", "pending", "failed", "skipped"]
    duration_ms: Optional[int] = None
    summary: Optional[str] = None


class IncomeClassificationTrace(BaseModel):
    """One income source classification from the LLM interpreter."""
    source_description: str
    head: str
    tax_regime: str
    annual_amount: int
    applicable_section: str
    applicable_schedule: str
    reasoning: str


class InterpretationTrace(BaseModel):
    """
    Formatted version of TaxComputationPlan for frontend display.
    Appears in the canvas after retrieval, before calculation.
    """
    status: Literal["complete", "failed"]

    # Income classifications
    income_classifications: list[IncomeClassificationTrace]

    # Exemptions/deductions/credits (formatted as label: value strings)
    exemptions: list[dict]      # {clause, description, applies, reasoning}
    deductions: list[dict]      # {type, allowed, claimed_amount, cap_rule}
    tax_credits: list[dict]     # {type, eligible, reasoning}

    # Withholding treatment
    withholding: list[dict]     # {source, section, amount, regime}

    # Special flags
    minimum_tax_applicable: bool
    super_tax_applicable: bool

    # LLM summary
    overall_reasoning: str
    caveats: list[str]
    referenced_sections: list[str]

    error_message: Optional[str] = None


class IncomeBreakdownTrace(BaseModel):
    """One income source row for the calculation canvas table."""
    head: str
    source_description: str
    gross_income: int
    tax_regime: str
    applicable_schedule: str
    computed_tax: float
    rate_percent: Optional[float] = None
    withholding_is_final: bool


class CalculationTrace(BaseModel):
    """
    Frontend-friendly version of TaxCalculationResult.
    Displayed in the canvas after interpretation is complete.
    """
    status: Literal["complete", "failed"]

    # ── Income & deductions ──
    total_gross_income: int
    exempt_income: int
    total_taxable_income: int
    total_deductions: int
    taxable_income_after_deductions: int

    # ── Tax liability ──
    tax_on_normal_income: float
    tax_on_separate_income: float
    gross_tax_liability: float
    total_tax_credits: float
    tax_after_credits: float
    minimum_tax_applicable: bool
    minimum_tax_amount: Optional[float] = None
    super_tax_applicable: bool
    super_tax_amount: Optional[float] = None
    total_tax_liability: float

    # ── Withholding & net result ──
    total_adjustable_withholding: float
    total_final_withholding: float
    net_tax_payable: float
    refund_due: float
    is_refund: bool
    effective_tax_rate: float

    # ── Detail lists ──
    income_breakdowns: list[IncomeBreakdownTrace]
    deductions_applied: list[dict]
    tax_credits_applied: list[dict]
    withholding_adjustments: list[dict]
    computation_notes: list[str]
    caveats: list[str]

    summary_text: str
    error_message: Optional[str] = None


class CanvasData(BaseModel):
    """
    Everything the frontend canvas needs to render the right panel.
    """
    steps: list[ProcessingStep]
    extraction: Optional[ExtractionTrace] = None
    retrieval: Optional[RetrievalTrace] = None
    interpretation: Optional[InterpretationTrace] = None
    calculation: Optional[CalculationTrace] = None
    raw_taxpayer_data: Optional[dict] = None


class PipelineResponse(BaseModel):
    """What the pipeline returns to the frontend."""
    stage: Literal[
        "clarification_needed",
        "extraction_complete",
    ]

    assistant_message: str
    questions: Optional[list[ClarificationQuestion]] = None

    canvas: CanvasData

    taxpayer_data: Optional[TaxpayerData] = None
    retrieved_sections: Optional[list[RetrievedSection]] = None

    session_id: Optional[str] = None
    turn_number: int = 1
