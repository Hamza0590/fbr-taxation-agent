"""
Standalone CLI test:
    python -m rule_retriever
"""
import asyncio
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main() -> None:
    from tax_extractor.models import TaxpayerData, SalaryIncome
    from .retriever import retrieve_relevant_sections

    test_data = TaxpayerData(
        tax_year="2025-2026",
        taxpayer_type="individual",
        residency_status="resident",
        filer_status="filer",
        age_above_60=False,
        disability_status=False,
        salary_income=SalaryIncome(
            basic_salary_annual=3_600_000,
            allowances=480_000,
            bonuses=200_000,
            employer_pension_contribution=0,
            tax_already_deducted=250_000,
        ),
        confidence_score=0.95,
        assumptions_made=[],
    )

    print("=== Running Rule Retriever ===\n")
    result = await retrieve_relevant_sections(test_data)

    print(f"Passes used:     {result.passes_used}")
    print(f"Nodes selected:  {result.node_ids_selected}")
    print(f"Reasoning:       {result.reasoning}\n")
    print(f"Sections retrieved: {len(result.sections)}")

    for section in result.sections:
        print(f"\n--- [{section.node_id}] {section.title} ---")
        print(f"Lines: {section.line_start}–{section.line_end}  |  Depth: {section.depth}")
        preview = section.content[:200].replace("\n", " ")
        print(f"Content preview: {preview}...")

    print("\n=== Full Result JSON ===")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    asyncio.run(main())
