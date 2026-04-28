import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..tax_extractor.models import TaxpayerData

from .models import RetrievalResult
from .retriever import RetrievalError, retrieve_relevant_sections

logger = logging.getLogger("rule_retriever.router")

router = APIRouter(prefix="/api/v1/retrieve", tags=["Rule Retrieval"])


class RetrievalRequest(BaseModel):
    taxpayer_data: TaxpayerData


@router.post("", response_model=RetrievalResult)
async def retrieve(request: RetrievalRequest) -> RetrievalResult:
    try:
        return await retrieve_relevant_sections(request.taxpayer_data)
    except (RetrievalError, FileNotFoundError) as exc:
        logger.error("Retrieval failed: %s", exc)
        raise HTTPException(status_code=500, detail="Retrieval service temporarily unavailable")
    except Exception as exc:
        logger.exception("Unexpected error in retrieval endpoint: %s", exc)
        raise HTTPException(status_code=500, detail="Retrieval service temporarily unavailable")
