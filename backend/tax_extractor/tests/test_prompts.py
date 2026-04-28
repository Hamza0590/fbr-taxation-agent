"""
Tests for system prompt behavior and edge cases.
Uses mocked LLM calls to verify extraction rules.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from tax_extractor.extractor import extract_tax_data


def _mock_response(payload: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    response = MagicMock()
    response.choices = [choice]
    return response


def _base_taxpayer(filer_status="filer", confidence=0.9) -> dict:
    return {
        "tax_year": "2025-2026",
        "taxpayer_type": "individual",
        "residency_status": "resident",
        "filer_status": filer_status,
        "age_above_60": False,
        "disability_status": False,
        "amounts_currency": "PKR",
        "confidence_score": confidence,
        "assumptions_made": [],
    }


@pytest.mark.asyncio
class TestPromptBehavior:

    async def _run(self, message: str, payload: dict, history=None):
        with patch("tax_extractor.extractor.acompletion", new=AsyncMock(return_value=_mock_response(payload))):
            return await extract_tax_data(message, history)

    async def test_returns_valid_json_no_markdown(self):
        """LLM returning plain JSON (no fences) is parsed cleanly."""
        payload = {
            "status": "complete",
            "extracted_data": {
                **_base_taxpayer(),
                "salary_income": {
                    "basic_salary_annual": 1_200_000,
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
            },
            "partial_data": None,
            "questions": None,
            "message": "Got it.",
        }
        result = await self._run("I earn 1 lakh per month and I'm a filer", payload)
        assert result.status == "complete"
        assert result.extracted_data is not None

    async def test_max_3_questions_rule(self):
        """Clarification responses must have at most 3 questions."""
        questions = [
            {
                "field_name": f"field_{i}",
                "question_text": f"Question {i}?",
                "options": None,
                "input_type": "text",
                "priority": "required",
            }
            for i in range(3)
        ]
        payload = {
            "status": "needs_clarification",
            "extracted_data": None,
            "partial_data": None,
            "questions": questions,
            "message": "Need more info.",
        }
        result = await self._run("vague message", payload)
        assert result.status == "needs_clarification"
        assert len(result.questions) <= 3

    async def test_lakh_conversion(self):
        """5 lakh per month → 6,000,000 annual."""
        payload = {
            "status": "needs_clarification",
            "extracted_data": None,
            "partial_data": {
                **_base_taxpayer(filer_status="non_filer", confidence=0.45),
                "salary_income": {
                    "basic_salary_annual": 6_000_000,  # 5 lakh * 12
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
                "assumptions_made": ["Monthly salary multiplied by 12 for annual figure"],
            },
            "questions": [
                {
                    "field_name": "filer_status",
                    "question_text": "Are you registered as a tax filer with FBR?",
                    "options": ["filer", "non_filer", "late_filer"],
                    "input_type": "choice",
                    "priority": "required",
                }
            ],
            "message": "Got your salary. Just need filer status.",
        }
        result = await self._run("I earn 5 lakh per month", payload)
        assert result.partial_data.salary_income.basic_salary_annual == 6_000_000

    async def test_crore_conversion(self):
        """1 crore → 10,000,000."""
        payload = {
            "status": "needs_clarification",
            "extracted_data": None,
            "partial_data": {
                **_base_taxpayer(filer_status="non_filer", confidence=0.45),
                "salary_income": {
                    "basic_salary_annual": 10_000_000,
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
                "assumptions_made": ["Converted 1 crore annual salary"],
            },
            "questions": [
                {
                    "field_name": "filer_status",
                    "question_text": "Are you registered as a tax filer?",
                    "options": ["filer", "non_filer", "late_filer"],
                    "input_type": "choice",
                    "priority": "required",
                }
            ],
            "message": "Got it.",
        }
        result = await self._run("I earn 1 crore per year", payload)
        assert result.partial_data.salary_income.basic_salary_annual == 10_000_000

    async def test_assumptions_logged(self):
        """Assumptions should always be present when defaults are applied."""
        payload = {
            "status": "complete",
            "extracted_data": {
                **_base_taxpayer(),
                "salary_income": {
                    "basic_salary_annual": 2_400_000,
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
                "assumptions_made": [
                    "Assumed resident — not stated",
                    "Assumed individual taxpayer",
                    "No deductions mentioned, assumed none",
                    "No withholding taxes mentioned, assumed none",
                    "Defaulted tax_year to 2025-2026",
                ],
            },
            "partial_data": None,
            "questions": None,
            "message": "Done.",
        }
        result = await self._run("I'm a filer earning 2 lakh monthly", payload)
        assert len(result.extracted_data.assumptions_made) > 0

    async def test_filer_status_not_assumed(self):
        """filer_status must never be assumed — must ask if missing."""
        payload = {
            "status": "needs_clarification",
            "extracted_data": None,
            "partial_data": {
                **_base_taxpayer(filer_status="non_filer", confidence=0.4),
                "salary_income": {
                    "basic_salary_annual": 3_000_000,
                    "allowances": 0.0,
                    "bonuses": 0.0,
                    "employer_pension_contribution": 0.0,
                    "tax_already_deducted": 0.0,
                },
                "assumptions_made": ["Monthly salary * 12"],
            },
            "questions": [
                {
                    "field_name": "filer_status",
                    "question_text": "Are you a registered tax filer with FBR?",
                    "options": ["filer", "non_filer", "late_filer"],
                    "input_type": "choice",
                    "priority": "required",
                }
            ],
            "message": "Just need to know your filer status.",
        }
        result = await self._run("I earn 3 lakh per month", payload)
        assert result.status == "needs_clarification"
        filer_q = [q for q in result.questions if q.field_name == "filer_status"]
        assert len(filer_q) == 1

    async def test_freelance_it_export_detected(self):
        """Upwork + software work → is_it_export=True."""
        payload = {
            "status": "needs_clarification",
            "extracted_data": None,
            "partial_data": {
                **_base_taxpayer(filer_status="non_filer", confidence=0.45),
                "freelance_income": {
                    "annual_income": 12_000,
                    "income_currency": "USD",
                    "platform": "Upwork",
                    "is_it_export": True,
                    "has_pseb_registration": False,
                },
                "assumptions_made": ["IT export assumed from software work on Upwork"],
            },
            "questions": [
                {
                    "field_name": "filer_status",
                    "question_text": "Are you a registered tax filer with FBR?",
                    "options": ["filer", "non_filer", "late_filer"],
                    "input_type": "choice",
                    "priority": "required",
                }
            ],
            "message": "Got your freelance income.",
        }
        result = await self._run("I do software development on Upwork earning $1000/month", payload)
        assert result.partial_data.freelance_income.is_it_export is True
        assert result.partial_data.freelance_income.platform == "Upwork"
