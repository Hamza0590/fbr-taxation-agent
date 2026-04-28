from .rates import get_rates, RATE_REGISTRY
from .lookup import compute_slab_tax, lookup_capital_gains_rate, lookup_withholding_rate, compute_minimum_tax
from .models import TaxSlab, TaxTable, FlatRate, WithholdingRate, TaxYearRates

__all__ = [
    "get_rates",
    "RATE_REGISTRY",
    "compute_slab_tax",
    "lookup_capital_gains_rate",
    "lookup_withholding_rate",
    "compute_minimum_tax",
    "TaxSlab",
    "TaxTable",
    "FlatRate",
    "WithholdingRate",
    "TaxYearRates",
]
