import pytest
from pydantic import ValidationError
from tax_extractor.models.income import SalaryIncome, FreelanceIncome, CapitalGains
from tax_extractor.models.deductions import Deductions
from tax_extractor.models.withholding import WithholdingTaxes
from tax_extractor.models.taxpayer import TaxpayerData
from tax_extractor.models.clarification import ClarificationQuestion
from tax_extractor.models.response import ExtractionResponse


class TestSalaryIncome:
    def test_valid_minimal(self):
        s = SalaryIncome(basic_salary_annual=1_200_000)
        assert s.basic_salary_annual == 1_200_000
        assert s.allowances == 0.0
        assert s.bonuses == 0.0

    def test_valid_full(self):
        s = SalaryIncome(
            basic_salary_annual=2_400_000,
            allowances=360_000,
            bonuses=120_000,
            employer_pension_contribution=60_000,
            tax_already_deducted=50_000,
        )
        assert s.tax_already_deducted == 50_000


class TestCapitalGains:
    def test_optional_holding_period_defaults_none(self):
        cg = CapitalGains()
        assert cg.holding_period_securities is None
        assert cg.holding_period_property is None

    def test_valid_holding_period(self):
        cg = CapitalGains(
            gain_from_securities=500_000,
            holding_period_securities="less_than_1yr",
        )
        assert cg.holding_period_securities == "less_than_1yr"

    def test_invalid_holding_period_rejected(self):
        with pytest.raises(ValidationError):
            CapitalGains(holding_period_securities="forever")


class TestDeductions:
    def test_all_defaults_zero(self):
        d = Deductions()
        assert d.zakat_paid == 0.0
        assert d.donations == 0.0
        assert d.pension_fund_contribution == 0.0


class TestWithholdingTaxes:
    def test_all_defaults_zero(self):
        w = WithholdingTaxes()
        assert w.tax_on_salary == 0.0
        assert w.other_withholding == 0.0


class TestTaxpayerData:
    def _base(self, **kwargs):
        defaults = dict(
            tax_year="2025-2026",
            taxpayer_type="individual",
            residency_status="resident",
            filer_status="filer",
            confidence_score=0.9,
        )
        defaults.update(kwargs)
        return TaxpayerData(**defaults)

    def test_valid_minimal(self):
        td = self._base()
        assert td.salary_income is None
        assert td.amounts_currency == "PKR"
        assert td.assumptions_made == []

    def test_confidence_score_bounds(self):
        with pytest.raises(ValidationError):
            self._base(confidence_score=1.1)
        with pytest.raises(ValidationError):
            self._base(confidence_score=-0.1)

    def test_invalid_taxpayer_type(self):
        with pytest.raises(ValidationError):
            self._base(taxpayer_type="trust")

    def test_invalid_filer_status(self):
        with pytest.raises(ValidationError):
            self._base(filer_status="unknown")

    def test_optional_income_sources(self):
        salary = SalaryIncome(basic_salary_annual=3_000_000)
        td = self._base(salary_income=salary)
        assert td.salary_income.basic_salary_annual == 3_000_000
        assert td.business_income is None


class TestClarificationQuestion:
    def test_valid_choice_question(self):
        q = ClarificationQuestion(
            field_name="filer_status",
            question_text="Are you registered as a tax filer with FBR?",
            options=["filer", "non_filer", "late_filer"],
            input_type="choice",
            priority="required",
        )
        assert len(q.options) == 3

    def test_open_ended_question(self):
        q = ClarificationQuestion(
            field_name="business_type",
            question_text="What kind of business do you run?",
            options=None,
            input_type="text",
            priority="optional",
        )
        assert q.options is None

    def test_invalid_input_type(self):
        with pytest.raises(ValidationError):
            ClarificationQuestion(
                field_name="x",
                question_text="q",
                input_type="dropdown",
                priority="required",
            )


class TestExtractionResponse:
    def _taxpayer(self):
        return TaxpayerData(
            tax_year="2025-2026",
            taxpayer_type="individual",
            residency_status="resident",
            filer_status="filer",
            confidence_score=0.95,
        )

    def test_complete_status(self):
        r = ExtractionResponse(
            status="complete",
            extracted_data=self._taxpayer(),
            message="Got it!",
        )
        assert r.questions is None
        assert r.partial_data is None

    def test_needs_clarification_status(self):
        q = ClarificationQuestion(
            field_name="filer_status",
            question_text="Are you a registered filer?",
            input_type="choice",
            priority="required",
            options=["filer", "non_filer", "late_filer"],
        )
        r = ExtractionResponse(
            status="needs_clarification",
            questions=[q],
            partial_data=self._taxpayer(),
            message="I need a bit more info.",
        )
        assert r.extracted_data is None
        assert len(r.questions) == 1

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            ExtractionResponse(status="pending", message="x")
