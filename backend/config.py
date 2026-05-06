from pydantic_settings import BaseSettings
from functools import lru_cache


class CORSSettings(BaseSettings):
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    model_config = {
        "env_prefix": "CORS_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_cors_settings() -> CORSSettings:
    return CORSSettings()


class BackendSettings(BaseSettings):
    # ── Pipeline behaviour ──────────────────────────────────────────────────────
    max_clarification_turns: int = 5
    log_level: str = "INFO"

    # ── App metadata ────────────────────────────────────────────────────────────
    app_name: str = "Tax Sathi"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Shared API key for all new pipeline nodes ───────────────────────────────
    # Set PIPELINE_LLM_API_KEY in .env; falls back to empty (litellm uses GROQ_API_KEY env var)
    llm_api_key: str = ""

    # ── [4] Router node (intent classifier) ────────────────────────────────────
    # Use the cheapest/fastest model — this runs on EVERY request
    router_llm_model: str = "groq/llama-3.1-8b-instant"
    router_llm_temperature: float = 0.0
    router_llm_max_tokens: int = 200

    # ── [5] General / out-of-scope node ────────────────────────────────────────
    general_llm_model: str = "groq/llama-3.1-8b-instant"
    general_llm_temperature: float = 0.5
    general_llm_max_tokens: int = 300

    # ── [6] Follow-up handler node ──────────────────────────────────────────────
    # Needs a stronger model — it reasons over calculation results + FBR sections
    followup_llm_model: str = "groq/llama-3.3-70b-versatile"
    followup_llm_temperature: float = 0.3
    followup_llm_max_tokens: int = 800

    model_config = {
        "env_prefix": "PIPELINE_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_backend_settings() -> BackendSettings:
    return BackendSettings()
