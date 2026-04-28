from pydantic_settings import BaseSettings
from functools import lru_cache


class TaxRulesConfig(BaseSettings):
    DEFAULT_TAX_YEAR: str = "2025-2026"

    model_config = {
        "env_prefix": "TAX_RULES_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_tax_rules_config() -> TaxRulesConfig:
    return TaxRulesConfig()
