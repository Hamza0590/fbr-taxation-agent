import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from .extractor import extract_tax_data, ExtractionError
from .models import ExtractionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/extract", tags=["Tax Extraction"])


class ExtractionRequest(BaseModel):
    message: str
    conversation_history: Optional[list[dict]] = None
    session_id: Optional[str] = None


@router.post("", response_model=ExtractionResponse)
async def extract(request: ExtractionRequest) -> ExtractionResponse:
    try:
        return await extract_tax_data(request.message, request.conversation_history)
    except ExtractionError as exc:
        logger.error("ExtractionError: %s", exc)
        raise HTTPException(status_code=500, detail="Extraction service temporarily unavailable")
    except Exception as exc:
        logger.exception("Unexpected error in extraction endpoint: %s", exc)
        raise HTTPException(status_code=500, detail="Extraction service temporarily unavailable")
