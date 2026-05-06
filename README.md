# Tax Sathi — AI Tax Assistant for Pakistan

Tax Sathi lets any Pakistani taxpayer type their income situation in plain English or Urdu and instantly get a full income tax calculation with a breakdown, FBR section citations, and an auditable reasoning trace — no accountant required. It covers **FY 2025-26** under the Income Tax Ordinance 2001.

---

## Features

- **Agentic tax calculation** — extracts income data from conversation, retrieves relevant FBR sections, interprets the law, then computes slab tax, minimum tax, super tax, and withholding adjustments deterministically
- **FBR Policy Q&A** — cite-accurate answers grounded in the Income Tax Ordinance 2001 (Section numbers, schedules, deadlines)
- **Image document upload** — attach a salary slip, withholding certificate, or challan; a vision LLM extracts the financial data and feeds it into the pipeline automatically
- **Multi-turn clarification** — asks targeted follow-up questions when income data is incomplete; configurable turn limit
- **Voice input** — speak your question via the Web Speech API (Chrome/Edge)
- **Live canvas panel** — shows the full reasoning trace: extraction → retrieval → interpretation → calculation with collapsible FBR section cards
- **Session history** — full multi-session chat stored in Supabase with canvas replay
- **Export** — copy the full canvas trace to clipboard as plain text

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12, Pydantic v2 |
| Pipeline orchestration | LangGraph (`StateGraph` with conditional routing) |
| LLM abstraction | LiteLLM (swap models by changing one `.env` variable) |
| LLM providers | Groq (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) + OpenRouter (`gpt-oss-20b/120b`) |
| Vision LLM | Any LiteLLM-compatible vision model (default `openai/gpt-4o`) |
| Database | Supabase (PostgreSQL) |
| Auth | JWT via python-jose + bcrypt; Google OAuth 2.0 |
| Frontend | React 18 via Babel Standalone — no build step, no npm |
| FBR document retrieval | Custom 2-pass tree-index over ITO 2001 markdown (~250k chars) |

---

## Getting Started

### Prerequisites

- Python 3.12 (conda recommended)
- A [Supabase](https://supabase.com) project (free tier works)
- A [Groq](https://console.groq.com) API key (free tier works)
- An [OpenRouter](https://openrouter.ai) key for the retriever/interpreter models

### 1. Clone and set up the environment

```bash
git clone <repo-url>
cd Tax_Sathi
conda create -n Tax_Sathi python=3.12
conda activate Tax_Sathi
pip install -r backend/requirements.txt
```

### 2. Configure environment variables

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Open `.env` and fill in at minimum:

| Variable | Where to get it |
|---|---|
| `SUPABASE_URL` | Supabase project → Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase project → Settings → API |
| `AUTH_SECRET_KEY` | Any strong random string (32+ chars) |
| `TAX_EXTRACTOR_LLM_API_KEY` | Groq console |
| `RULE_RETRIEVER_LLM_API_KEY` | OpenRouter |
| `TAX_INTERPRETER_LLM_API_KEY` | OpenRouter |
| `PIPELINE_LLM_API_KEY` | Groq console |
| `IMAGE_EXTRACTOR_LLM_API_KEY` | OpenAI / any vision-capable provider |

All other variables have sensible defaults. See `.env.example` for the full list with comments.

### 3. Initialize the database

In the Supabase SQL editor, paste and run the contents of `supabase_schema.sql`.

### 4. Start the backend

```bash
conda activate Tax_Sathi
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Serve the frontend

```bash
cd frontend
python -m http.server 3000
```

Open `http://localhost:3000`. No build step — React and Babel run in the browser.

---

## Project Structure

```
Tax_Sathi/
├── .env.example                   # Template for all environment variables
├── .gitignore
├── supabase_schema.sql            # Database DDL + migration statements
├── PROJECT_CONTEXT.md             # High-level architecture reference
├── PROJECT_DOCUMENTATION.md      # Full developer documentation (read this for deep detail)
│
├── backend/
│   ├── main.py                    # FastAPI app factory; mounts all routers; CORS config
│   ├── config.py                  # BackendSettings + CORSSettings
│   ├── database.py                # Supabase client singleton
│   │
│   ├── auth/                      # Signup, login, CNIC login, Google OAuth, forgot/reset password
│   ├── profile/                   # GET/PUT user identity profile
│   ├── sessions/                  # Chat session and message CRUD
│   │
│   ├── pipeline/                  # ★ LangGraph orchestration
│   │   ├── graph.py               # StateGraph: nodes, edges, conditional routing
│   │   ├── state.py               # TaxSathiState TypedDict (shared across all nodes)
│   │   ├── helpers.py             # Trace builder functions for the canvas panel
│   │   ├── router.py              # POST /api/v1/pipeline/chat + Supabase message persistence
│   │   ├── models.py              # PipelineRequest, PipelineResponse, CanvasData, trace models
│   │   ├── nodes/                 # One file per graph node (router, extraction, retrieval, …)
│   │   └── prompts/               # Router and FBR Q&A system prompts
│   │
│   ├── tax_extractor/             # Module 1: LLM → TaxpayerData (structured income extraction)
│   ├── rule_retriever/            # Module 2: 2-pass tree-index → relevant FBR sections
│   ├── tax_interpreter/           # Module 3: LLM → TaxComputationPlan (legal classification)
│   ├── tax_calculator/            # Module 4: deterministic arithmetic → TaxCalculationResult
│   ├── tax_rules/                 # Static FBR rate tables for FY 2025-26 (no LLM)
│   ├── image_extractor/           # Vision LLM → plain-text financial summary from images
│   └── tests/                     # Integration tests (e2e + per-stage boundaries)
│
├── frontend/
│   ├── index.html                 # Entry point; loads React 18 + Babel + all JSX files
│   ├── app.css                    # Design tokens + all component styles (dark mode included)
│   └── src/
│       ├── app.jsx                # Root state machine (boot → auth → setup → app)
│       ├── api.jsx                # window.API — all backend calls in one place
│       ├── workspace.jsx          # Chat UI: message thread, input bar, image attachment
│       ├── sidebar.jsx            # Session list + navigation
│       ├── output.jsx             # Canvas panel: 5-section pipeline trace view + copy button
│       ├── auth.jsx               # Login/signup screen (email, CNIC, Google)
│       ├── setup.jsx              # 4-step onboarding wizard (new users)
│       ├── profile.jsx            # Profile modal (identity + income + deductions)
│       ├── structured.jsx         # Structured income entry modal
│       ├── calendar.jsx           # Tax calendar modal
│       ├── trace.jsx              # Backend trace side panel
│       ├── data.jsx               # Static data: suggestions, calendar events, FBR categories
│       ├── icons.jsx              # All SVG icons (single Icon component)
│       └── tweaks.jsx             # TweaksPanel: theme, density, layout controls
│
└── pre_processing_fbr_doc/
    ├── fbr_combined.md            # Full Income Tax Ordinance 2001 as markdown (~250k chars)
    └── PageIndex-main/results/
        └── fbr_combined_structure.json   # Hierarchical tree index for 2-pass retrieval
```

---

## Auth

Tax Sathi supports four login methods:

- **Email + password** — standard signup/login; bcrypt-hashed passwords; 7-day JWT stored in `localStorage`
- **CNIC login** — login with CNIC number (`XXXXX-XXXXXXX-X` format) + password
- **Google OAuth** — one-click login via Google; new users are redirected to the profile setup wizard
- **Forgot password** — enter email to receive a reset link via SMTP; link contains a time-limited token (default 30 min)

New users (via any auth method) are routed through a 4-step profile setup wizard before accessing the main app.

---

## API Docs

Interactive Swagger UI is available while the backend is running:

**`http://localhost:8000/docs`**

All endpoints are listed there with request/response schemas. For a static reference table of every endpoint grouped by module, see [`PROJECT_DOCUMENTATION.md`](./PROJECT_DOCUMENTATION.md#11-all-api-endpoints).

---

## Known Gaps

These items are not production-ready:

- **Image extraction model** — defaults to `openai/gpt-4o`; requires a valid `IMAGE_EXTRACTOR_LLM_API_KEY` in `.env` to function; silently returns no context if the key is missing
- **CORS origins** — hardcoded to `localhost` in `.env`; must be updated before any deployment
- **PDF export** — export button shows a "coming soon" toast; not implemented
- **Share link** — share button shows a "coming soon" toast; not implemented
- **AOP / Company edge cases** — models support these taxpayer types but prompts are optimised for individuals; complex multi-partner AOP scenarios may produce inaccurate interpretations
- **Super tax / minimum tax on complex corporate structures** — interpreter may misclassify when multiple income heads interact with Section 113 and 4C simultaneously
- **No rate-limit or abuse protection** — the pipeline endpoint has no request throttling
- **Session title auto-generation** — titles are set to the first 50 characters of the first message; no LLM-generated summaries

For the full architecture and implementation details, read [`PROJECT_DOCUMENTATION.md`](./PROJECT_DOCUMENTATION.md).

---

*FY 2025-26 · Income Tax Ordinance 2001 · Pakistan FBR*
