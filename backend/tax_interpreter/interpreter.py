import json
import re
import logging
from litellm import acompletion

from ..tax_extractor.models.taxpayer import TaxpayerData
from ..rule_retriever.models import RetrievalResult, RetrievedSection
from .models import TaxComputationPlan
from .prompts.system_prompt import get_system_prompt
from .config import get_interpreter_config

logger = logging.getLogger("tax_interpreter")


async def interpret_tax_situation(
    taxpayer_data: TaxpayerData,
    retrieval_result: RetrievalResult,
    tax_year: str | None = None,
) -> TaxComputationPlan:
    """
    Takes structured taxpayer data + retrieved FBR sections,
    asks the LLM to make legal classification decisions,
    and returns a TaxComputationPlan.
    """
    config = get_interpreter_config()
    effective_tax_year = tax_year or config.DEFAULT_TAX_YEAR

    user_message = _build_user_message(taxpayer_data, retrieval_result, effective_tax_year, config.MAX_SECTION_CHARS)

    _sys_prompt = get_system_prompt()
    _sys_chars = len(_sys_prompt)
    _usr_chars = len(user_message)
    _total_chars = _sys_chars + _usr_chars
    # Rough token estimate: 1 token ~ 4 chars for English text
    _sys_tokens   = _sys_chars  // 4
    _usr_tokens   = _usr_chars  // 4
    _input_tokens = _total_chars // 4
    # Groq bills: input_tokens + max_tokens (output reservation) upfront
    _groq_billed  = _input_tokens + config.LLM_MAX_TOKENS

    print(f"\n{'='*60}")
    print(f"[INTERPRETER] INPUT SIZE BREAKDOWN")
    print(f"{'='*60}")
    print(f"  Model              : {config.LLM_MODEL}")
    print(f"  MAX_SECTION_CHARS  : {config.MAX_SECTION_CHARS} chars/section")
    print(f"  Sections in prompt : {len(retrieval_result.sections)}")
    print(f"{'─'*60}")
    print(f"  System prompt      : {_sys_chars:>7,} chars  (~{_sys_tokens:>5,} tokens)")
    print(f"  User message       : {_usr_chars:>7,} chars  (~{_usr_tokens:>5,} tokens)")
    print(f"  TOTAL INPUT        : {_total_chars:>7,} chars  (~{_input_tokens:>5,} tokens)")
    print(f"{'─'*60}")
    print(f"  max_tokens (output reservation)  : +{config.LLM_MAX_TOKENS:>5,} tokens")
    print(f"  GROQ BILLED (input + max_tokens) : ~{_groq_billed:>5,} tokens")
    print(f"{'='*60}\n")

    # We print a truncated version to console to avoid Unicode/size issues in some terminals
    print(f"--- SYSTEM PROMPT ({_sys_chars} chars) ---")
    print(_sys_prompt[:500] + "..." if _sys_chars > 500 else _sys_prompt)
    print(f"\n--- USER MESSAGE ({_usr_chars} chars) ---")
    print(user_message[:1000] + "..." if _usr_chars > 1000 else user_message)
    print(f"{'='*60}\n")


    kwargs: dict = {
        "model": config.LLM_MODEL,
        "api_key": config.LLM_API_KEY or None,
        "messages": [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": user_message},
        ],
        "temperature": config.LLM_TEMPERATURE,
        "max_tokens": config.LLM_MAX_TOKENS,
    }

    raw = None
    # First attempt: with JSON mode
    try:
        kwargs["response_format"] = {"type": "json_object"}
        response = await acompletion(**kwargs)
        raw = response.choices[0].message.content
    except Exception as e:
        logger.warning("JSON-mode attempt failed (%s), retrying without it", e)
        del kwargs["response_format"]
        try:
            response = await acompletion(**kwargs)
            raw = response.choices[0].message.content
        except Exception as e2:
            logger.error("Both LLM attempts failed: %s", e2)
            raise ValueError(f"LLM call failed: {e2}") from e2

    if not raw:
        raise ValueError("LLM returned an empty response.")

    logger.debug("Raw interpreter response (%d chars): %s", len(raw), raw[:300])

    cleaned = _extract_json(raw)
    if not cleaned:
        logger.error("Could not extract JSON from LLM response. Raw (first 1000):\n%s", raw[:1000])
        raise ValueError("LLM returned a response with no parseable JSON object.")

    try:
        plan_dict = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed: %s\nCleaned text (first 1000):\n%s", e, cleaned[:1000])
        raise ValueError(f"LLM returned invalid JSON: {e}") from e

    # Coerce common type issues before Pydantic sees the dict
    plan_dict = _coerce_plan_dict(plan_dict)

    try:
        plan = TaxComputationPlan(**plan_dict)
        print(f"\n[INTERPRETER] Interpretation Complete.")
        print(f" > Classified {len(plan.income_classifications)} income sources.")
        print(f" > Reasoning: {plan.overall_reasoning}")
        return plan
    except Exception as e:
        logger.error(
            "TaxComputationPlan validation failed: %s\n"
            "plan_dict keys: %s\n"
            "income_classifications sample: %s",
            e,
            list(plan_dict.keys()),
            plan_dict.get("income_classifications", [])[:1],
        )
        raise ValueError(f"LLM response does not match TaxComputationPlan schema: {e}") from e


# ─── JSON extraction ──────────────────────────────────────────────────────────

def _extract_json(raw: str) -> str | None:
    """
    Try multiple strategies to extract a JSON object from the raw LLM text.
    Returns the JSON string, or None if nothing can be parsed.
    """
    text = raw.strip()

    # 1. Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # 2. Try direct parse first (covers the happy path)
    if text.startswith("{"):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

    # 3. Find first { ... } block (handles leading prose)
    start = text.find("{")
    if start == -1:
        return None

    # Walk backwards from end to find matching closing brace
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    pass  # keep trying in case there's another object
    return None


# ─── Type coercion helpers ────────────────────────────────────────────────────

def _coerce_plan_dict(d: dict) -> dict:
    """
    Fix common LLM output issues before Pydantic validation:
    - Coerce float annual_amounts to int
    - Coerce float withholding amounts to int
    - Replace None annual_amount with 0 (with a warning)
    - Strip unknown top-level keys gracefully (Pydantic ignores extras by default)
    """
    # income_classifications
    for ic in d.get("income_classifications") or []:
        if isinstance(ic, dict):
            _coerce_int_field(ic, "annual_amount")

    # withholding_classifications
    for wh in d.get("withholding_classifications") or []:
        if isinstance(wh, dict):
            _coerce_int_field(wh, "amount")

    # deductions
    for ded in d.get("deductions") or []:
        if isinstance(ded, dict):
            _coerce_int_field(ded, "claimed_amount")
            _coerce_int_field(ded, "allowed_amount")

    # exemptions
    for ex in d.get("exemptions") or []:
        if isinstance(ex, dict):
            if ex.get("exempt_amount") is not None:
                _coerce_int_field(ex, "exempt_amount")

    # tax_credits
    for tc in d.get("tax_credits") or []:
        if isinstance(tc, dict):
            if tc.get("credit_amount") is not None:
                _coerce_int_field(tc, "credit_amount")

    # minimum_tax_turnover
    if d.get("minimum_tax_turnover") is not None:
        try:
            d["minimum_tax_turnover"] = int(float(d["minimum_tax_turnover"]))
        except (ValueError, TypeError):
            d["minimum_tax_turnover"] = None

    # Ensure required list fields default to empty lists rather than None
    for list_field in ("income_classifications", "exemptions", "deductions",
                       "tax_credits", "withholding_classifications",
                       "referenced_sections", "caveats"):
        if d.get(list_field) is None:
            d[list_field] = []

    # Ensure boolean fields are actual booleans
    for bool_field in ("minimum_tax_applicable", "super_tax_applicable"):
        val = d.get(bool_field)
        if val is None:
            d[bool_field] = False
        elif not isinstance(val, bool):
            d[bool_field] = bool(val)

    return d


def _coerce_int_field(d: dict, field: str) -> None:
    val = d.get(field)
    if val is None:
        logger.warning("Field '%s' is null; defaulting to 0", field)
        d[field] = 0
    elif isinstance(val, float):
        d[field] = int(val)
    elif isinstance(val, str):
        try:
            d[field] = int(float(val.replace(",", "")))
        except ValueError:
            logger.warning("Could not coerce '%s' value '%s' to int; defaulting to 0", field, val)
            d[field] = 0


# ─── Message builders ─────────────────────────────────────────────────────────

def _build_user_message(
    taxpayer_data: TaxpayerData,
    retrieval_result: RetrievalResult,
    tax_year: str,
    max_section_chars: int = 1800,
) -> str:
    taxpayer_section = _format_taxpayer_data(taxpayer_data)
    retrieval_section = _format_retrieved_sections(retrieval_result, max_section_chars)

    return f"""## Tax Year
{tax_year}

## Taxpayer Information
{taxpayer_section}

## Relevant FBR Law Sections
The following sections were retrieved from the Income Tax Ordinance 2001 as relevant to this taxpayer's situation. Use these to make your classification decisions.

{retrieval_section}

## Your Task
Analyze the taxpayer information against the law sections above. Produce a TaxComputationPlan JSON classifying each income source, determining applicable exemptions/deductions/credits, and classifying each withholding tax. Keep reasoning fields concise (1-2 sentences). Do NOT compute any tax amounts — only classify and interpret. Respond ONLY with the JSON object."""


def _format_taxpayer_data(data: TaxpayerData) -> str:
    parts: list[str] = []

    parts.append(f"- Taxpayer Type: {data.taxpayer_type}")
    parts.append(f"- Residency: {data.residency_status or 'Not specified (assume resident)'}")
    parts.append(f"- Filer Status: {data.filer_status or 'Not specified (assume filer)'}")
    if data.age_above_60:
        parts.append("- Age: Above 60 (senior citizen — 50% tax reduction may apply)")
    if data.disability_status:
        parts.append("- Disability: Yes (tax reduction may apply)")

    if data.salary_income:
        s = data.salary_income
        parts.append(f"- Salary Income (annual): PKR {s.basic_salary_annual:,.0f}")
        if s.allowances and s.allowances > 0:
            parts.append(f"  - Allowances: PKR {s.allowances:,.0f}")
        if s.bonuses and s.bonuses > 0:
            parts.append(f"  - Bonuses: PKR {s.bonuses:,.0f}")
        if s.tax_already_deducted and s.tax_already_deducted > 0:
            parts.append(f"  - Tax withheld by employer (Section 149): PKR {s.tax_already_deducted:,.0f}")

    if data.business_income:
        b = data.business_income
        parts.append(f"- Business Income: gross revenue PKR {b.gross_revenue:,.0f}, net profit PKR {b.net_profit:,.0f}")
        parts.append(f"  - Business type: {b.business_type.replace('_', ' ')}")

    if data.rental_income:
        r = data.rental_income
        parts.append(f"- Rental Income (annual): PKR {r.gross_rent_annual:,.0f}")
        parts.append(f"  - Property type: {r.property_type}")

    if data.capital_gains:
        cg = data.capital_gains
        if cg.gain_from_securities and cg.gain_from_securities > 0:
            parts.append(f"- Capital Gain (securities): PKR {cg.gain_from_securities:,.0f}")
            if cg.holding_period_securities:
                parts.append(f"  - Holding period: {cg.holding_period_securities.replace('_', ' ')}")
        if cg.gain_from_property and cg.gain_from_property > 0:
            parts.append(f"- Capital Gain (property): PKR {cg.gain_from_property:,.0f}")
            if cg.holding_period_property:
                parts.append(f"  - Holding period: {cg.holding_period_property.replace('_', ' ')}")

    if data.freelance_income:
        fi = data.freelance_income
        parts.append(f"- Freelance Income (annual): PKR {fi.annual_income:,.0f}")
        if fi.platform:
            parts.append(f"  - Platform: {fi.platform}")
        if fi.is_it_export:
            parts.append("  - IT Export: Yes (potential exemption applicable)")

    if data.other_income:
        o = data.other_income
        if o.bank_profit and o.bank_profit > 0:
            parts.append(f"- Bank Profit: PKR {o.bank_profit:,.0f}")
        if o.dividends and o.dividends > 0:
            parts.append(f"- Dividends: PKR {o.dividends:,.0f}")
        if o.prize_winnings and o.prize_winnings > 0:
            parts.append(f"- Prize Winnings: PKR {o.prize_winnings:,.0f}")

    if data.agricultural_income:
        parts.append(f"- Agricultural Income: PKR {data.agricultural_income.amount:,.0f} (generally exempt under Section 41)")

    if data.deductions:
        d = data.deductions
        if d.zakat_paid and d.zakat_paid > 0:
            parts.append(f"- Zakat paid: PKR {d.zakat_paid:,.0f}")
        if d.donations and d.donations > 0:
            parts.append(f"- Charitable donations: PKR {d.donations:,.0f}")
        if d.pension_fund_contribution and d.pension_fund_contribution > 0:
            parts.append(f"- Pension fund contribution: PKR {d.pension_fund_contribution:,.0f}")

    if data.withholding_taxes:
        wh = data.withholding_taxes
        if wh.tax_on_salary and wh.tax_on_salary > 0:
            parts.append(f"- Withholding — Salary (Section 149): PKR {wh.tax_on_salary:,.0f}")
        if wh.tax_on_bank_profit and wh.tax_on_bank_profit > 0:
            parts.append(f"- Withholding — Bank profit (Section 151/7B): PKR {wh.tax_on_bank_profit:,.0f}")
        if wh.tax_on_dividends and wh.tax_on_dividends > 0:
            parts.append(f"- Withholding — Dividend (Section 5): PKR {wh.tax_on_dividends:,.0f}")
        if wh.advance_tax_paid and wh.advance_tax_paid > 0:
            parts.append(f"- Advance Tax Paid: PKR {wh.advance_tax_paid:,.0f}")
        if wh.other_withholding and wh.other_withholding > 0:
            parts.append(f"- Withholding — Other: PKR {wh.other_withholding:,.0f}")

    return "\n".join(parts) if parts else "No detailed information provided."


def _format_retrieved_sections(result: RetrievalResult, max_chars_per_section: int = 1800) -> str:
    parts: list[str] = []
    for i, section in enumerate(result.sections, 1):
        parts.append(f"### Retrieved Section {i}: {section.title}")
        if section.summary:
            parts.append(f"Summary: {section.summary}")
        content = section.content
        if len(content) > max_chars_per_section:
            content = content[:max_chars_per_section] + "\n[... content truncated to fit token budget ...]"
        parts.append(f"\n{content}\n")
    return "\n".join(parts) if parts else "No sections retrieved."
