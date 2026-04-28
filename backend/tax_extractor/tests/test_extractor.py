"""
Tests for extraction logic using mocked LLM responses.
All 6 test cases from the spec are covered.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tax_extractor.extractor import extract_tax_data, ExtractionError


def _make_llm_response(payload: dict) -> MagicMock:
    """Build a fake litellm response object."""
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    response = MagicMock()
    response.choices = [choice]
    return response


def _salary_complete(annual: float, filer_status: str = "filer") -> dict:
    return {
        "status": "complete",
        "extracted_data": {
            "tax_year": "2025-2026",
            "taxpayer_type": "individual",
            "residency_status": "resident",
            "filer_status": filer_status,
            "age_above_60": False,
            "disability_status": False,
            "salary_income": {
                "basic_salary_annual": annual,
                "allowances": 0.0,
                "bonuses": 0.0,
                "employer_pension_contribution": 0.0,
                "tax_already_deducted": 0.0,
            },
            "amounts_currency": "PKR",
            "confidence_score": 0.95,
            "assumptions_made": ["Assumed resident", "Assumed individual taxpayer"],
        },
        "partial_data": None,
        "questions": None,
        "message": "Got it! You earn PKR 3,000,000 annually as a salaried filer.",
    }


def _needs_clarification_response(questions: list[dict], partial_data: dict | None = None) -> dict:
    return {
        "status": "needs_clarification",
        "extracted_data": None,
        "partial_data": partial_data,
        "questions": questions,
        "message": "I need a bit more info to proceed.",
    }


FILER_STATUS_QUESTION = {
    "field_name": "filer_status",
    "question_text": "Are you registered as a tax filer with FBR?",
    "options": ["filer", "non_filer", "late_filer"],
    "input_type": "choice",
    "priority": "required",
}

INCOME_SOURCE_QUESTION = {
    "field_name": "salary_income",
    "question_text": "Could you tell me what your main source of income is and approximately how much you earn?",
    "options": None,
    "input_type": "text",
    "priority": "required",
}

PERIOD_QUESTION = {
    "field_name": "salary_income",
    "question_text": "Is the 15 lakhs you mentioned your monthly or annual income?",
    "options": ["Monthly", "Annual"],
    "input_type": "choice",
    "priority": "required",
}


@pytest.mark.asyncio
class TestExtractTaxData:

    async def _call(self, message: str, llm_payload: dict, history=None):
        mock_response = _make_llm_response(llm_payload)
        with patch("tax_extractor.extractor.acompletion", new=AsyncMock(return_value=mock_response)):
            return await extract_tax_data(message, history)

    # ── Test Case 1: Clear salaried individual ──────────────────────────────
    async def test_case_1_clear_salaried_individual(self):
        payload = _salary_complete(annual=3_000_000, filer_status="filer")
        result = await self._call(
            "I'm a salaried individual earning PKR 250,000 per month. I'm a registered filer.",
            payload,
        )
        assert result.status == "complete"
        assert result.extracted_data is not None
        assert result.extracted_data.salary_income.basic_salary_annual == 3_000_000
        assert result.extracted_data.filer_status == "filer"

    # ── Test Case 2: Vague message ──────────────────────────────────────────
    async def test_case_2_vague_message(self):
        payload = _needs_clarification_response([INCOME_SOURCE_QUESTION])
        result = await self._call("I want to calculate my tax", payload)
        assert result.status == "needs_clarification"
        assert result.questions is not None
        field_names = [q.field_name for q in result.questions]
        assert "salary_income" in field_names

    # ── Test Case 3: Freelancer with mixed info ─────────────────────────────
    async def test_case_3_freelancer_mixed(self):
        partial = {
            "tax_year": "2025-2026",
            "taxpayer_type": "individual",
            "residency_status": "resident",
            "filer_status": "non_filer",  # placeholder to pass validation
            "age_above_60": False,
            "disability_status": False,
            "freelance_income": {
                "annual_income": 40_000,
                "income_currency": "USD",
                "platform": "Upwork",
                "is_it_export": True,
                "has_pseb_registration": False,
            },
            "business_income": {
                "gross_revenue": 6_000_000,
                "total_expenses": 0.0,
                "net_profit": 6_000_000,
                "business_type": "sole_proprietor",
                "is_sme": False,
            },
            "amounts_currency": "USD",
            "confidence_score": 0.45,
            "assumptions_made": ["Assumed resident", "Business net_profit assumed equal to revenue"],
        }
        payload = _needs_clarification_response([FILER_STATUS_QUESTION], partial_data=partial)
        result = await self._call(
            "I work on Upwork doing web development, I made about $40,000 last year. "
            "I also have a small shop in Rawalpindi that makes around 5 lakh per month.",
            payload,
        )
        assert result.status == "needs_clarification"
        assert result.partial_data is not None
        assert result.partial_data.freelance_income is not None
        assert result.partial_data.business_income is not None
        filer_q = [q for q in result.questions if q.field_name == "filer_status"]
        assert len(filer_q) == 1

    # ── Test Case 4: Complete complex case ─────────────────────────────────
    async def test_case_4_complete_complex(self):
        payload = {
            "status": "complete",
            "extracted_data": {
                "tax_year": "2025-2026",
                "taxpayer_type": "individual",
                "residency_status": "resident",
                "filer_status": "filer",
                "age_above_60": False,
                "disability_status": False,
                "salary_income": {
                    "basic_salary_annual": 4_800_000,
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
                "rental_income": {
                    "gross_rent_annual": 600_000,
                    "property_type": "residential",
                    "allowable_deductions": 0.0,
                },
                "capital_gains": {
                    "gain_from_securities": 200_000,
                    "holding_period_securities": "less_than_1yr",
                    "gain_from_property": 0.0,
                    "holding_period_property": None,
                },
                "deductions": {
                    "zakat_paid": 30_000,
                    "donations": 0.0,
                    "pension_fund_contribution": 0.0,
                    "education_expenses": 0.0,
                    "health_insurance_premium": 0.0,
                    "investment_in_shares": 0.0,
                    "mortgage_interest": 0.0,
                },
                "amounts_currency": "PKR",
                "confidence_score": 0.92,
                "assumptions_made": ["Assumed resident", "Converted monthly salary to annual"],
            },
            "partial_data": None,
            "questions": None,
            "message": "All set! Here's what I found.",
        }
        result = await self._call(
            "I'm a filer, individual, resident. Monthly salary is 4 lakh, I also have rental income "
            "of 50,000 per month from a residential property, and I earned 2 lakh from stock trading "
            "(held for 8 months). I paid 30,000 in zakat this year.",
            payload,
        )
        assert result.status == "complete"
        assert result.extracted_data.confidence_score > 0.8
        assert result.extracted_data.salary_income.basic_salary_annual == 4_800_000
        assert result.extracted_data.rental_income is not None
        assert result.extracted_data.capital_gains.gain_from_securities == 200_000
        assert result.extracted_data.deductions.zakat_paid == 30_000

    # ── Test Case 5: Urdu-English mix ─────────────────────────────────────
    async def test_case_5_urdu_english_mix(self):
        payload = {
            "status": "needs_clarification",
            "extracted_data": None,
            "partial_data": {
                "tax_year": "2025-2026",
                "taxpayer_type": "individual",
                "residency_status": "resident",
                "filer_status": "non_filer",
                "age_above_60": False,
                "disability_status": False,
                "salary_income": {
                    "basic_salary_annual": 2_400_000,
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
                "freelance_income": {
                    "annual_income": 6_000,
                    "income_currency": "USD",
                    "platform": "Fiverr",
                    "is_it_export": False,
                    "has_pseb_registration": False,
                },
                "amounts_currency": "PKR",
                "confidence_score": 0.45,
                "assumptions_made": ["Assumed resident", "Assumed individual"],
            },
            "questions": [FILER_STATUS_QUESTION],
            "message": "I could extract your salary and freelance income. Just need one more detail.",
        }
        result = await self._call(
            "meri salary 2 lakh hai monthly, aur kuch freelancing bhi karta hoon Fiverr pe, "
            "wo around 500 dollar milte hain month mein",
            payload,
        )
        assert result.partial_data is not None
        assert result.partial_data.salary_income.basic_salary_annual == 2_400_000
        assert result.partial_data.freelance_income.annual_income == 6_000
        assert result.partial_data.freelance_income.income_currency == "USD"

    # ── Test Case 6: Ambiguous period ─────────────────────────────────────
    async def test_case_6_ambiguous_period(self):
        payload = _needs_clarification_response([PERIOD_QUESTION])
        result = await self._call("I earn 15 lakhs", payload)
        assert result.status == "needs_clarification"
        field_names = [q.field_name for q in result.questions]
        assert "salary_income" in field_names

    # ── Error handling ────────────────────────────────────────────────────
    async def test_llm_failure_raises_extraction_error(self):
        with patch("tax_extractor.extractor.acompletion", new=AsyncMock(side_effect=Exception("timeout"))):
            with pytest.raises(ExtractionError):
                await extract_tax_data("some message")

    async def test_bad_json_returns_fallback(self):
        choice = MagicMock()
        choice.message.content = "this is not json at all"
        response = MagicMock()
        response.choices = [choice]
        with patch("tax_extractor.extractor.acompletion", new=AsyncMock(return_value=response)):
            result = await extract_tax_data("some message")
        assert result.status == "needs_clarification"
        assert result.questions is not None

    async def test_markdown_wrapped_json_is_handled(self):
        payload = _salary_complete(annual=1_200_000, filer_status="filer")
        choice = MagicMock()
        choice.message.content = "```json\n" + json.dumps(payload) + "\n```"
        response = MagicMock()
        response.choices = [choice]
        with patch("tax_extractor.extractor.acompletion", new=AsyncMock(return_value=response)):
            result = await extract_tax_data("I earn 1 lakh per month, I'm a filer")
        assert result.status == "complete"

    async def test_multi_turn_passes_history(self):
        history = [
            {"role": "user", "content": "I earn 3 lakh per month"},
            {"role": "assistant", "content": '{"status": "needs_clarification"}'},
        ]
        payload = _salary_complete(annual=3_600_000, filer_status="filer")
        captured_messages = []

        async def fake_completion(**kwargs):
            captured_messages.extend(kwargs["messages"])
            return _make_llm_response(payload)

        with patch("tax_extractor.extractor.acompletion", new=fake_completion):
            result = await extract_tax_data("Yes I am a filer", history)

        assert result.status == "complete"
        roles = [m["role"] for m in captured_messages]
        assert roles[0] == "system"
        assert "user" in roles
        assert "assistant" in roles
