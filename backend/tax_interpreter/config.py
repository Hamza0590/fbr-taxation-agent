from pydantic_settings import BaseSettings
from functools import lru_cache


class TaxInterpreterConfig(BaseSettings):
    # Configure in .env under TAX_INTERPRETER_* prefix
    LLM_MODEL: str = "groq/llama-3.3-70b-versatile"
    LLM_API_KEY: str = ""
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4000
    DEFAULT_TAX_YEAR: str = "2025-2026"
    MAX_SECTION_CHARS: int = 1800

    model_config = {
        "env_prefix": "TAX_INTERPRETER_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_interpreter_config() -> TaxInterpreterConfig:
    return TaxInterpreterConfig()
