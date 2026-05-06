import base64
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from .models import ImageExtractionResult
from .extractor import extract_from_image
from .config import get_settings
from ..auth.utils import get_current_user, TokenData

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/image-extractor", tags=["image-extractor"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


@router.post("/extract", response_model=ImageExtractionResult)
async def extract_image(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
) -> ImageExtractionResult:
    settings = get_settings()
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Unsupported file type. Please upload a JPEG, PNG, or WebP image.")
    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large. Maximum size is {settings.max_file_size_mb}MB.")
    image_base64 = base64.b64encode(content).decode("utf-8")
    return await extract_from_image(image_base64, file.content_type)
