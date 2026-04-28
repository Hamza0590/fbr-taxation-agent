"""Tests for the retrieval query builder."""
import pytest
from tax_extractor.models import (
    TaxpayerData, SalaryIncome, BusinessIncome, RentalIncome,
    FreelanceIncome, CapitalGains, OtherIncome,
)
from rule_retriever.query_builder import build_retrieval_query


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


class TestQueryBuilder:
    def test_salaried_individual_contains_amount(self):
        data = _base(salary_income=SalaryIncome(basic_salary_annual=3_600_000))
        query = build_retrieval_query(data)
        assert "3,600,000" in query
        assert "Salary Income" in query

    def test_salaried_mentions_allowances(self):
        data = _base(salary_income=SalaryIncome(basic_salary_annual=1_200_000, allowances=120_000))
        query = build_retrieval_query(data)
        assert "120,000" in query
        assert "allowances" in query.lower()

    def test_multiple_income_sources(self):
        data = _base(
            salary_income=SalaryIncome(basic_salary_annual=2_400_000),
            rental_income=RentalIncome(gross_rent_annual=600_000, property_type="residential"),
            freelance_income=FreelanceIncome(annual_income=20_000, income_currency="USD"),
        )
        query = build_retrieval_query(data)
        assert "Salary Income" in query
        assert "Rental Income" in query
        assert "Freelance Income" in query

    def test_freelance_it_export_explicitly_mentioned(self):
        data = _base(
            freelance_income=FreelanceIncome(
                annual_income=50_000,
                income_currency="USD",
                is_it_export=True,
                platform="Upwork",
            )
        )
        query = build_retrieval_query(data)
        assert "IT EXPORT" in query.upper() or "IT export" in query

    def test_senior_citizen_mentioned(self):
        data = _base(
            age_above_60=True,
            salary_income=SalaryIncome(basic_salary_annual=1_000_000),
        )
        query = build_retrieval_query(data)
        assert "SENIOR CITIZEN" in query.upper() or "senior citizen" in query.lower()

    def test_non_filer_emphasised(self):
        data = _base(
            filer_status="non_filer",
            salary_income=SalaryIncome(basic_salary_annual=1_000_000),
        )
        query = build_retrieval_query(data)
        assert "non_filer" in query.lower() or "non filer" in query.lower() or "higher withholding" in query.lower()

    def test_closing_instruction_present(self):
        data = _base(salary_income=SalaryIncome(basic_salary_annual=1_000_000))
        query = build_retrieval_query(data)
        assert "I need to find" in query

    def test_assumptions_appended(self):
        data = _base(
            salary_income=SalaryIncome(basic_salary_annual=1_000_000),
            assumptions_made=["Assumed resident", "Monthly salary multiplied by 12"],
        )
        query = build_retrieval_query(data)
        assert "assumed" in query.lower()
        assert "Assumed resident" in query

    def test_no_income_sources(self):
        data = _base()
        query = build_retrieval_query(data)
        assert "I need to find" in query  # still has closing instruction

    def test_capital_gains_holding_period(self):
        data = _base(
            capital_gains=CapitalGains(
                gain_from_securities=500_000,
                holding_period_securities="less_than_1yr",
            )
        )
        query = build_retrieval_query(data)
        assert "Capital Gains" in query
        assert "500,000" in query

    def test_disability_mentioned(self):
        data = _base(
            disability_status=True,
            salary_income=SalaryIncome(basic_salary_annual=800_000),
        )
        query = build_retrieval_query(data)
        assert "Disability" in query or "disability" in query.lower()
