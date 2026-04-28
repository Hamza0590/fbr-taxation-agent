from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..tax_extractor.models.taxpayer import TaxpayerData
from ..rule_retriever.models import RetrievalResult
from .interpreter import interpret_tax_situation
from .models import TaxComputationPlan

router = APIRouter(prefix="/api/v1/interpret", tags=["Tax Interpreter"])


class InterpretRequest(BaseModel):
    taxpayer_data: TaxpayerData
    retrieval_result: RetrievalResult
    tax_year: str | None = None


@router.post("/", response_model=TaxComputationPlan)
async def interpret(request: InterpretRequest):
    """
    Debug endpoint: directly test the LLM interpretation step.
    In production this is called internally by the pipeline orchestrator.
    """
    try:
        plan = await interpret_tax_situation(
            request.taxpayer_data,
            request.retrieval_result,
            request.tax_year,
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interpretation failed: {e}")
