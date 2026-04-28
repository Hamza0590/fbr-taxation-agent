from pydantic_settings import BaseSettings
from functools import lru_cache


class ExtractorSettings(BaseSettings):
    # Configure in .env under TAX_EXTRACTOR_* prefix
    llm_model: str = "groq/llama-3.3-70b-versatile"
    llm_api_key: str = ""
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2000
    default_tax_year: str = "2025-2026"

    model_config = {
        "env_prefix": "TAX_EXTRACTOR_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> ExtractorSettings:
    return ExtractorSettings()
