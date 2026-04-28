# Tax Sathi — Backend

## Setup

1. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. Create `.env` in the project root with your API keys and file paths.
   See `.env.example` for all required variables.

3. Run the server from the project root:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```

4. Test the pipeline:
   ```bash
   curl -X POST http://localhost:8000/api/v1/pipeline/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "I earn 3 lakh per month from my job and I am a filer"}'
   ```

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/pipeline/chat` | Main chat endpoint (use this) |
| `POST /api/v1/extract` | Direct extraction (debugging) |
| `POST /api/v1/retrieve` | Direct retrieval (debugging) |
| `GET /health` | Health check |

## Architecture

```
User Message
    → tax_extractor (LLM extracts structured data)
    → rule_retriever (LLM reasons over FBR document tree)
    → [Future: tax_calculator]
    → Response to frontend (with full canvas trace data)
```

## Response Structure

Every response includes `canvas` data for the right panel:
- `canvas.steps` — processing timeline (Understanding → Extracting → Finding sections)
- `canvas.extraction` — extracted fields, missing fields, assumptions, confidence
- `canvas.retrieval` — selected FBR sections with relevance explanations
- `canvas.raw_taxpayer_data` — full structured data dump

Even during clarification turns, the canvas shows partial extraction data.
