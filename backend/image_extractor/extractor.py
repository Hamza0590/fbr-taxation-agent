import logging
from litellm import acompletion
from .models import ImageExtractionResult
from .prompts import IMAGE_EXTRACTION_PROMPT
from .config import get_settings

logger = logging.getLogger(__name__)


async def extract_from_image(image_base64: str, media_type: str) -> ImageExtractionResult:
    settings = get_settings()
    try:
        response = await acompletion(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": IMAGE_EXTRACTION_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{media_type};base64,{image_base64}"},
                        },
                        {"type": "text", "text": "Extract all financial information from this document."},
                    ],
                },
            ],
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            api_key=settings.llm_api_key or None,
        )
        response_text = (response.choices[0].message.content or "").strip()
        if response_text == "NO_FINANCIAL_DATA":
            return ImageExtractionResult(success=True, raw_text="", error=None, model_used=settings.llm_model)
        if response_text == "IMAGE_UNREADABLE":
            return ImageExtractionResult(
                success=False,
                raw_text="",
                error="Image is unreadable or too blurry to process.",
                model_used=settings.llm_model,
            )
        return ImageExtractionResult(success=True, raw_text=response_text, error=None, model_used=settings.llm_model)
    except Exception as exc:
        logger.error("Image extraction LLM call failed: %s", exc)
        return ImageExtractionResult(success=False, raw_text="", error=str(exc), model_used=settings.llm_model)
