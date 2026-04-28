"""Tests for retriever.py with mocked LLM calls."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tax_extractor.models import TaxpayerData, SalaryIncome, RentalIncome, FreelanceIncome
from rule_retriever.retriever import retrieve_relevant_sections, RetrievalError


def _base(**kwargs) -> TaxpayerData:
    defaults = dict(
        tax_year="2025-2026",
        taxpayer_type="individual",
        residency_status="resident",
        filer_status="filer",
        confidence_score=0.9,
        assumptions_made=[],
    )
    defaults.update(kwargs)
    return TaxpayerData(**defaults)


def _mock_llm(payload: dict):
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    response = MagicMock()
    response.choices = [choice]
    return AsyncMock(return_value=response)


@pytest.mark.asyncio
class TestRetriever:

    # ── Test Case 1: Simple salaried individual ────────────────────────────
    async def test_case_1_salaried_includes_salary_node(self):
        payload = {
            "node_ids": ["0005", "0066", "0014"],
            "reasoning": "Salary head, individual rate division, exemptions.",
        }
        data = _base(salary_income=SalaryIncome(basic_salary_annual=3_600_000))

        with patch("rule_retriever.retriever.acompletion", _mock_llm(payload)):
            result = await retrieve_relevant_sections(data)

        ids = result.node_ids_selected
        assert "0005" in ids, "Salary head node must be selected"
        assert "0066" in ids, "Individual rate division must be selected"
        assert result.passes_used >= 1
        assert len(result.sections) == len(ids)

    # ── Test Case 2: Salaried + rental ────────────────────────────────────
    async def test_case_2_salary_and_rental(self):
        payload = {
            "node_ids": ["0005", "0006", "0014"],
            "reasoning": "Salary head, property head, exemptions for rental deductions.",
        }
        data = _base(
            salary_income=SalaryIncome(basic_salary_annual=2_400_000),
            rental_income=RentalIncome(gross_rent_annual=600_000, property_type="residential"),
        )
        with patch("rule_retriever.retriever.acompletion", _mock_llm(payload)):
            result = await retrieve_relevant_sections(data)

        ids = result.node_ids_selected
        assert "0005" in ids
        assert "0006" in ids
        assert "0014" in ids

    # ── Test Case 3: Freelancer IT export ─────────────────────────────────
    async def test_case_3_freelance_it_export(self):
        payload = {
            "node_ids": ["0013", "0014", "0039"],
            "reasoning": "Other sources for freelance income, exemptions for IT export, foreign-source income rules.",
        }
        data = _base(
            freelance_income=FreelanceIncome(
                annual_income=40_000,
                income_currency="USD",
                is_it_export=True,
                platform="Upwork",
            )
        )
        with patch("rule_retriever.retriever.acompletion", _mock_llm(payload)):
            result = await retrieve_relevant_sections(data)

        ids = result.node_ids_selected
        assert "0014" in ids, "Exemptions must be included for IT export"

    # ── Test Case 4: Invalid node_ids from LLM ────────────────────────────
    async def test_case_4_invalid_node_id_skipped(self):
        payload = {
            "node_ids": ["0005", "9999", "0006"],
            "reasoning": "Mixed valid and invalid nodes.",
        }
        data = _base(
            salary_income=SalaryIncome(basic_salary_annual=1_200_000),
            rental_income=RentalIncome(gross_rent_annual=300_000, property_type="residential"),
        )
        with patch("rule_retriever.retriever.acompletion", _mock_llm(payload)):
            result = await retrieve_relevant_sections(data)

        ids = result.node_ids_selected
        assert "9999" not in ids, "Invalid node_id must be excluded"
        assert "0005" in ids
        assert "0006" in ids

    # ── Test Case 5: Markdown-wrapped JSON handled ─────────────────────────
    async def test_case_5_markdown_wrapped_json(self):
        raw_payload = {"node_ids": ["0005", "0014"], "reasoning": "Salary and exemptions."}
        wrapped = "```json\n" + json.dumps(raw_payload) + "\n```"

        choice = MagicMock()
        choice.message.content = wrapped
        response = MagicMock()
        response.choices = [choice]
        mock_fn = AsyncMock(return_value=response)

        data = _base(salary_income=SalaryIncome(basic_salary_annual=1_000_000))
        with patch("rule_retriever.retriever.acompletion", mock_fn):
            result = await retrieve_relevant_sections(data)

        assert "0005" in result.node_ids_selected
        assert "0014" in result.node_ids_selected

    # ── LLM failure → heuristic fallback ──────────────────────────────────
    async def test_llm_failure_uses_heuristic(self):
        data = _base(salary_income=SalaryIncome(basic_salary_annual=1_000_000))
        with patch("rule_retriever.retriever.acompletion", AsyncMock(side_effect=Exception("timeout"))):
            result = await retrieve_relevant_sections(data)

        # Should not raise; uses heuristic
        assert len(result.sections) > 0
        assert "0005" in result.node_ids_selected or "0066" in result.node_ids_selected
        assert "Heuristic" in result.reasoning

    # ── Too many nodes → truncated to max_nodes ────────────────────────────
    async def test_too_many_nodes_truncated(self):
        # LLM returns 10 nodes; max_nodes = 7
        many = ["0005", "0006", "0007", "0008", "0009", "0010", "0011", "0012", "0013", "0014"]
        payload = {"node_ids": many, "reasoning": "Many nodes."}
        data = _base(salary_income=SalaryIncome(basic_salary_annual=1_000_000))

        with patch("rule_retriever.retriever.acompletion", _mock_llm(payload)):
            result = await retrieve_relevant_sections(data)

        assert len(result.node_ids_selected) <= 7

    # ── RetrievalResult structure ──────────────────────────────────────────
    async def test_result_structure(self):
        payload = {"node_ids": ["0005"], "reasoning": "Salary only."}
        data = _base(salary_income=SalaryIncome(basic_salary_annual=2_400_000))

        with patch("rule_retriever.retriever.acompletion", _mock_llm(payload)):
            result = await retrieve_relevant_sections(data)

        assert result.passes_used >= 1
        assert isinstance(result.query_used, str)
        assert len(result.query_used) > 50
        assert isinstance(result.reasoning, str)
        for section in result.sections:
            assert section.node_id
            assert section.title
            assert section.content
            assert section.line_start > 0
            assert section.line_end >= section.line_start
