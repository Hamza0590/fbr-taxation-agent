from pydantic import BaseModel


class ImageExtractionResult(BaseModel):
    success: bool
    raw_text: str          # Plain-text financial summary extracted from the image; empty string if none found
    error: str | None      # Human-readable error if success=False
    model_used: str        # Which vision model was used (from settings)
