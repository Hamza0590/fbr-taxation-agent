from .models import TaxSlab, TaxTable, TaxYearRates


def compute_slab_tax(amount: int, table: TaxTable) -> dict:
    """
    Given a taxable income amount and a slab-based TaxTable, find the
    applicable slab and compute tax.

    Tax formula per slab:
        tax = slab.fixed_tax + (slab.rate_percent / 100) * (amount - slab.min_amount)
    """
    if amount < 0:
        raise ValueError("Amount cannot be negative")

    applicable_slab: TaxSlab | None = None
    for slab in table.slabs:
        upper = slab.max_amount if slab.max_amount is not None else float("inf")
        # First slab (min_amount=0): amount in [0, max_amount]
        # Other slabs: amount in (min_amount, max_amount] — threshold is exclusive lower bound
        if slab.min_amount == 0:
            if amount <= upper:
                applicable_slab = slab
                break
        else:
            if slab.min_amount < amount <= upper:
                applicable_slab = slab
                break

    if applicable_slab is None:
        raise ValueError(f"No applicable slab found for amount {amount} in table '{table.description}'")

    excess = max(0, amount - applicable_slab.min_amount)
    tax_on_excess = (applicable_slab.rate_percent / 100.0) * excess
    total_tax = applicable_slab.fixed_tax + tax_on_excess
    effective_rate = (total_tax / amount * 100.0) if amount > 0 else 0.0

    return {
        "taxable_amount": amount,
        "applicable_slab": applicable_slab,
        "slab_description": table.description,
        "fixed_tax": applicable_slab.fixed_tax,
        "tax_on_excess": round(tax_on_excess, 2),
        "total_tax": round(total_tax, 2),
        "effective_rate": round(effective_rate, 4),
    }


def lookup_capital_gains_rate(
    gain_type: str,
    holding_period_years: float,
    filer_status: str,
    rates: TaxYearRates,
    property_sub_type: str = "plots",
) -> float:
    """
    Return the applicable capital gains tax rate percentage.

    Args:
        gain_type: "securities" | "property"
        holding_period_years: e.g. 0.5, 1.5, 3.0
        filer_status: "filer" | "non_filer"
        rates: TaxYearRates for the applicable tax year
        property_sub_type: "plots" | "constructed" | "flats" (only for property)

    Returns:
        Rate as a float percentage, e.g. 15.0
    """
    if gain_type == "securities":
        rate_list = rates.capital_gains_securities
    elif gain_type == "property":
        if property_sub_type == "constructed":
            rate_list = rates.capital_gains_property_constructed
        elif property_sub_type == "flats":
            rate_list = rates.capital_gains_property_flats
        else:
            rate_list = rates.capital_gains_property_plots
    else:
        raise ValueError(f"Unknown gain_type: '{gain_type}'. Use 'securities' or 'property'.")

    _CONDITION_MAP: dict[str, tuple[float, float | None]] = {
        "holding_period_up_to_1_year":   (0.0,  1.0),
        "holding_period_1_to_2_years":   (1.0,  2.0),
        "holding_period_2_to_3_years":   (2.0,  3.0),
        "holding_period_3_to_4_years":   (3.0,  4.0),
        "holding_period_4_to_5_years":   (4.0,  5.0),
        "holding_period_5_to_6_years":   (5.0,  6.0),
        "holding_period_over_6_years":   (6.0,  None),
        "holding_period_over_4_years":   (4.0,  None),
        "holding_period_over_2_years":   (2.0,  None),
        "future_commodity_contracts_pme": (0.0,  None),
    }

    for flat_rate in rate_list:
        if flat_rate.condition == "future_commodity_contracts_pme":
            continue  # skip — handled separately
        bounds = _CONDITION_MAP.get(flat_rate.condition)
        if bounds is None:
            continue
        lower, upper = bounds
        if upper is None:
            if holding_period_years > lower:
                base_rate = flat_rate.rate_percent
                if filer_status == "non_filer":
                    nfr = flat_rate.non_filer_rate
                    return max(base_rate, nfr) if nfr is not None else max(base_rate, 15.0)
                return base_rate
        else:
            if lower < holding_period_years <= upper or (lower == 0 and holding_period_years <= upper):
                base_rate = flat_rate.rate_percent
                if filer_status == "non_filer":
                    nfr = flat_rate.non_filer_rate
                    return max(base_rate, nfr) if nfr is not None else max(base_rate, 15.0)
                return base_rate

    # Fallback — top slab
    return rate_list[-1].rate_percent


def lookup_withholding_rate(
    section: str,
    filer_status: str,
    rates: TaxYearRates,
) -> dict:
    """Return { rate, is_final } for a withholding section."""
    for wh in rates.withholding_rates:
        if wh.section == section:
            rate = wh.filer_rate if filer_status == "filer" else wh.non_filer_rate
            return {
                "section": wh.section,
                "description": wh.description,
                "rate": rate,
                "is_final": wh.is_final,
            }
    raise ValueError(f"Withholding section '{section}' not found in rate table for {rates.tax_year}.")


def compute_minimum_tax(turnover: int, rates: TaxYearRates, category: str = "general") -> float:
    """
    Section 113 minimum tax on turnover.

    Args:
        turnover: Annual turnover in PKR
        rates: TaxYearRates for the applicable year
        category: "general" | "sui_gas" | "distributors"

    Returns:
        Minimum tax amount in PKR
    """
    rate_map = {
        "general":     rates.minimum_tax_rate_general,
        "sui_gas":     rates.minimum_tax_rate_sui_gas_airlines_poultry,
        "distributors": rates.minimum_tax_rate_distributors_pharma,
    }
    rate_pct = rate_map.get(category, rates.minimum_tax_rate_general)
    return round(turnover * rate_pct / 100.0, 2)
