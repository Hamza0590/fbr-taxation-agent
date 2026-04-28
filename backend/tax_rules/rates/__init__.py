from ..models import TaxYearRates
from .tax_year_2025_2026 import TAX_YEAR_2025_2026

RATE_REGISTRY: dict[str, TaxYearRates] = {
    "2025-2026": TAX_YEAR_2025_2026,
}


def get_rates(tax_year: str) -> TaxYearRates:
    if tax_year not in RATE_REGISTRY:
        raise ValueError(
            f"Tax rates not available for year '{tax_year}'. "
            f"Available: {list(RATE_REGISTRY.keys())}"
        )
    return RATE_REGISTRY[tax_year]
