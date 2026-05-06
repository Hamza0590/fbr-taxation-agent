from pydantic_settings import BaseSettings
from functools import lru_cache


class ImageExtractorSettings(BaseSettings):
    llm_model: str = "openai/gpt-4o"
    llm_api_key: str = ""
    llm_temperature: float = 0.0
    llm_max_tokens: int = 1500
    max_file_size_mb: int = 10

    model_config = {
        "env_prefix": "IMAGE_EXTRACTOR_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> ImageExtractorSettings:
    return ImageExtractorSettings()
