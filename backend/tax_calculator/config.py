from pydantic_settings import BaseSettings


class TaxCalculatorConfig(BaseSettings):
    DEFAULT_TAX_YEAR: str = "2025-2026"

    model_config = {"env_prefix": "TAX_CALCULATOR_"}
