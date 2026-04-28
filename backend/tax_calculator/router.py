from fastapi import APIRouter, HTTPException
from ..tax_interpreter.models import TaxComputationPlan
from .calculator import calculate_tax
from .models import TaxCalculationResult

router = APIRouter(prefix="/api/v1/calculate", tags=["Tax Calculator"])


@router.post("/", response_model=TaxCalculationResult)
async def calculate(plan: TaxComputationPlan):
    """
    Debug endpoint: directly test tax calculation with a TaxComputationPlan.
    In production this is called by the pipeline orchestrator, not directly.
    """
    try:
        return calculate_tax(plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
