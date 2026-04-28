"""
Standalone CLI test:
    python -m tax_extractor "I earn 3 lakh per month and I am a filer"
"""
import asyncio
import json
import sys
import logging

logging.basicConfig(level=logging.WARNING)


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tax_extractor \"<your tax situation>\"")
        sys.exit(1)

    message = " ".join(sys.argv[1:])

    from .extractor import extract_tax_data
    result = await extract_tax_data(message)
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


asyncio.run(main())
