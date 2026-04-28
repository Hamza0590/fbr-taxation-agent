"""
Test 2a: Extractor → Retriever data flow.
Run from project root: python backend/tests/test_extractor_to_retriever.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.tax_extractor.extractor import extract_tax_data
from backend.rule_retriever.retriever import retrieve_relevant_sections


async def test_extractor_to_retriever():
    message = (
        "I am a salaried person earning 200,000 per month from ABC Company. "
        "My employer deducts 15,000 monthly as tax. "
        "I also have a savings account with 50,000 annual profit."
    )

    print("=== STEP 1: EXTRACTION ===")
    extraction_result = await extract_tax_data(message, conversation_history=[])

    print(f"Status: {extraction_result.status}")

    if extraction_result.status == "needs_clarification":
        print(f"Questions: {[q.question_text for q in (extraction_result.questions or [])]}")
        print("NOTE: Using partial_data for retrieval test.")
        taxpayer_data = extraction_result.partial_data
    else:
        taxpayer_data = extraction_result.extracted_data

    assert taxpayer_data is not None, "TaxpayerData must not be None"
    print(f"TaxpayerData type: {type(taxpayer_data).__name__}")
    print(f"Fields (partial): {taxpayer_data.model_dump_json(indent=2)[:600]}...")

    print("\n=== STEP 2: RETRIEVAL ===")
    retrieval_result = await retrieve_relevant_sections(taxpayer_data)

    print(f"RetrievalResult type: {type(retrieval_result).__name__}")
    print(f"Sections retrieved: {len(retrieval_result.sections)}")
    assert len(retrieval_result.sections) >= 1, "Retriever must return at least 1 section"

    for section in retrieval_result.sections:
        preview = section.content[:120].replace("\n", " ")
        print(f"  [{section.node_id}] {section.title}: {preview}...")

    print(f"\nPasses used: {retrieval_result.passes_used}")
    print(f"Reasoning: {retrieval_result.reasoning[:200]}")

    print("\n✅ Extractor → Retriever: DATA FLOWS CORRECTLY")


if __name__ == "__main__":
    asyncio.run(test_extractor_to_retriever())
