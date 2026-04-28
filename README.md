# Tax Sathi — AI-Powered Pakistani Tax Advisory Assistant

Tax Sathi is an agentic web application that answers Pakistani income tax questions in plain English or Urdu. It calculates exact tax liability with a full step-by-step breakdown, answers FBR policy questions by citing specific ordinance sections, and handles multi-turn clarification — all for **FY 2025-26**.

---

## Features

- **Tax calculation** — salary, business, property, capital gains, and other-source income with slab tax, minimum tax, super tax, and withholding adjustments
- **FBR Policy Q&A** — cite-accurate answers grounded in the Income Tax Ordinance 2001
- **Multi-turn clarification** — asks follow-up questions when income data is incomplete, up to a configurable turn limit
- **Live canvas panel** — shows the full reasoning trace: extraction → retrieval → interpretation → calculation
- **User profiles** — persists identity and income preferences; optionally injects profile context into every query
- **Session history** — full multi-session chat history stored in Supabase with canvas replay

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12, Pydantic v2, LiteLLM |
| Orchestration | LangGraph (`StateGraph` with conditional routing) |
| LLMs | Groq API (`llama-3.1-8b-instant`, `llama-3.3-70b-versatile`) + OpenRouter (`gpt-oss-20b/120b`) |
| Database | Supabase (PostgreSQL) |
| Frontend | Vanilla React 18 via Babel Standalone — no build step |
| Auth | JWT (python-jose) + bcrypt |
| Document retrieval | Custom 2-pass tree-index over FBR markdown (~250k chars) |

---

## Architecture Overview

The backend is a **LangGraph `StateGraph`** that routes each user message through the appropriate processing path based on intent:

```
ENTRY ──► router_node (intent classifier)
               │
     ┌─────────┼──────────────┬────────────────┐
     ▼         ▼              ▼                 ▼
extraction  fbr_qa_node  followup_node    general_node
  _node         │              │                │
     │          │    [needs clarification]      │
     │          │         extraction_node       │
     │          │              │                │
     ▼          │              ▼                │
retrieval_node  │        retrieval_node         │
     ▼          │              ▼                │
interpretation  │       interpretation_node     │
  _node         │              ▼                │
     ▼          │        calculation_node       │
calculation     │                               │
  _node         └──────────────────────────────►┘
     │
     └──────────────────────► response_node ──► END
```

### Intent Routes

| Intent | Triggered By | Path |
|---|---|---|
| `tax_calculation` | User provides income/financial data | extraction → retrieval → interpretation → calculation → response |
| `fbr_policy_qa` | Asks about FBR rules, sections, or deadlines | fbr_qa → response |
| `follow_up` | Answering a clarification or asking about a prior result | followup → (extraction or response) |
| `general_greeting` | Greetings or capability questions | general → response |
| `out_of_scope` | Unrelated questions | general → response |

---

## Tax Calculation Pipeline

When intent is `tax_calculation`, four sequential stages run:

**Stage 1 — Extraction:** LLM extracts structured `TaxpayerData` (identity, all income sources, deductions, withholding) from the user's message and conversation history. If data is incomplete, it returns clarification questions and the graph pauses until the user answers.

**Stage 2 — Retrieval (2-pass):** An LLM scans the FBR document tree (titles only) to select up to 7 relevant ordinance sections. A second pass resolves any cross-referenced sections found in the fetched content. Falls back to heuristic node IDs if LLM retrieval fails.

**Stage 3 — Interpretation:** An LLM classifies each income source by tax regime (`NORMAL`, `FINAL`, `SEPARATE`, `EXEMPT`), decides which deductions and credits apply, and produces a `TaxComputationPlan` citing specific ordinance sections.

**Stage 4 — Calculation (zero LLM calls):** Pure arithmetic using FBR slab tables from `tax_rules/rates/tax_year_2025_2026.py`. Computes tax per head, applies credits, checks minimum tax and super tax, subtracts adjustable withholding.

---

## Directory Structure

```
Tax_Sathi/
├── .env                          # All credentials + LLM config
├── PROJECT_CONTEXT.md            # Full architecture reference
├── supabase_schema.sql           # Database schema
│
├── backend/
│   ├── main.py                   # FastAPI app + router mounts
│   ├── config.py                 # Pipeline-level settings
│   ├── database.py               # Supabase client singleton
│   │
│   ├── auth/                     # JWT signup/login
│   ├── profile/                  # User profile CRUD
│   ├── sessions/                 # Chat session management
│   │
│   ├── pipeline/                 # ★ LangGraph orchestration
│   │   ├── graph.py              # StateGraph definition
│   │   ├── state.py              # TaxSathiState TypedDict
│   │   ├── helpers.py            # Trace builder functions
│   │   ├── router.py             # POST /api/v1/pipeline/chat
│   │   ├── models.py             # Request/response contracts
│   │   ├── nodes/                # One file per graph node
│   │   └── prompts/              # Router and FBR QA prompts
│   │
│   ├── tax_extractor/            # Module 1: LLM → TaxpayerData
│   ├── rule_retriever/           # Module 2: Tree-index → FBR sections
│   ├── tax_interpreter/          # Module 3: LLM → TaxComputationPlan
│   ├── tax_calculator/           # Module 4: Arithmetic → TaxCalculationResult
│   ├── tax_rules/                # Static FBR rate tables (no LLM)
│   └── tests/                    # Integration tests (e2e + per-stage)
│
├── frontend/
│   ├── index.html                # Entry point (loads JSX via Babel)
│   ├── app.css                   # Design tokens + component styles
│   └── src/
│       ├── app.jsx               # Root state machine (boot/auth/setup/app)
│       ├── api.jsx               # window.API — all backend calls
│       ├── workspace.jsx         # Chat UI
│       ├── sidebar.jsx           # Session list
│       ├── output.jsx            # Canvas panel (5-section trace view)
│       ├── auth.jsx              # Login/signup screen
│       ├── setup.jsx             # 4-step onboarding wizard
│       ├── profile.jsx           # Profile modal
│       ├── calendar.jsx          # Tax calendar modal
│       └── structured.jsx        # Structured income entry modal
│
└── pre_processing_fbr_doc/
    ├── fbr_combined.md           # Full ITO 2001 as markdown (~250k chars)
    └── PageIndex-main/results/
        └── fbr_combined_structure.json  # Hierarchical tree index
```

---

## Setup & Installation

### Prerequisites

- Python 3.12 (conda recommended)
- A Supabase project
- Groq API key (free tier works)
- OpenRouter API key (for the 20b/120b models used in retrieval and interpretation)

### 1. Clone and create the environment

```bash
git clone <repo-url>
cd Tax_Sathi
conda create -n Tax_Sathi python=3.12
conda activate Tax_Sathi
pip install -r backend/requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` (or edit `.env` directly) and fill in your credentials:

```env
# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_jwt>

# Auth
AUTH_SECRET_KEY=<strong-random-secret>
AUTH_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_DAYS=7

# Pipeline behaviour
PIPELINE_MAX_CLARIFICATION_TURNS=5

# [1] Tax Extractor
TAX_EXTRACTOR_LLM_MODEL=groq/llama-3.1-8b-instant
TAX_EXTRACTOR_LLM_API_KEY=gsk_...
TAX_EXTRACTOR_LLM_TEMPERATURE=0.0
TAX_EXTRACTOR_LLM_MAX_TOKENS=2000
TAX_EXTRACTOR_DEFAULT_TAX_YEAR=2025-2026

# [2] Rule Retriever
RULE_RETRIEVER_LLM_MODEL=groq/openai/gpt-oss-120b
RULE_RETRIEVER_LLM_API_KEY=gsk_...
RULE_RETRIEVER_LLM_TEMPERATURE=0.1
RULE_RETRIEVER_LLM_MAX_TOKENS=2000
RULE_RETRIEVER_MAX_NODES=7
RULE_RETRIEVER_MAX_PASSES=2
RULE_RETRIEVER_TREE_INDEX_PATH=./pre_processing_fbr_doc/PageIndex-main/results/fbr_combined_structure.json
RULE_RETRIEVER_MARKDOWN_PATH=./pre_processing_fbr_doc/fbr_combined.md

# [3] Tax Interpreter
TAX_INTERPRETER_LLM_MODEL=groq/openai/gpt-oss-20b
TAX_INTERPRETER_LLM_API_KEY=gsk_...
TAX_INTERPRETER_LLM_TEMPERATURE=0.1
TAX_INTERPRETER_LLM_MAX_TOKENS=2000
TAX_INTERPRETER_DEFAULT_TAX_YEAR=2025-2026
TAX_INTERPRETER_MAX_SECTION_CHARS=600

# [4] Pipeline Router
PIPELINE_LLM_API_KEY=gsk_...
PIPELINE_ROUTER_LLM_MODEL=groq/llama-3.1-8b-instant
PIPELINE_ROUTER_LLM_TEMPERATURE=0.0
PIPELINE_ROUTER_LLM_MAX_TOKENS=200

# [5] Pipeline General node
PIPELINE_GENERAL_LLM_MODEL=groq/llama-3.1-8b-instant
PIPELINE_GENERAL_LLM_TEMPERATURE=0.5
PIPELINE_GENERAL_LLM_MAX_TOKENS=300

# [6] Pipeline Follow-up node
PIPELINE_FOLLOWUP_LLM_MODEL=groq/llama-3.3-70b-versatile
PIPELINE_FOLLOWUP_LLM_TEMPERATURE=0.3
PIPELINE_FOLLOWUP_LLM_MAX_TOKENS=800
```

### 3. Initialize the database

Run `supabase_schema.sql` against your Supabase project via the SQL editor or `psql`.

---

## Running the Project

### Backend

```bash
conda activate Tax_Sathi
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
python -m http.server 5173
```

Open `http://localhost:5173`. No build step — React and Babel run in the browser.

---

## API Reference

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/signup` | — | Register and receive JWT |
| POST | `/api/v1/auth/login` | — | Login and receive JWT |
| GET | `/api/v1/auth/me` | JWT | Current authenticated user |
| GET | `/api/v1/profile/` | JWT | Fetch user profile |
| PUT | `/api/v1/profile/` | JWT | Update profile fields |
| GET | `/api/v1/sessions/` | JWT | List sessions with previews |
| POST | `/api/v1/sessions/` | JWT | Create new session |
| GET | `/api/v1/sessions/{id}` | JWT | Session with full message history |
| PUT | `/api/v1/sessions/{id}` | JWT | Rename session |
| DELETE | `/api/v1/sessions/{id}` | JWT | Delete session and messages |
| **POST** | **`/api/v1/pipeline/chat`** | **JWT** | **Main chat endpoint (LangGraph)** |
| POST | `/api/v1/tax-extractor` | JWT | Debug: run extraction standalone |
| POST | `/api/v1/rule-retriever` | JWT | Debug: run retrieval standalone |
| POST | `/api/v1/tax-interpreter` | JWT | Debug: run interpretation standalone |
| POST | `/api/v1/tax-calculator` | JWT | Debug: run calculation standalone |
| GET | `/health` | — | `{"status": "ok"}` |

### Main Chat Request / Response

```json
// POST /api/v1/pipeline/chat
{
  "message": "I earn PKR 3.6M salary and have rental income of PKR 600k",
  "conversation_history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "session_id": "uuid-or-null",
  "profile_context": "optional pre-formatted profile block"
}

// Response
{
  "stage": "clarification_needed | extraction_complete",
  "assistant_message": "...",
  "questions": [...],
  "canvas": { "steps": [...], "extraction": {...}, "retrieval": {...}, "interpretation": {...}, "calculation": {...} },
  "taxpayer_data": {...},
  "retrieved_sections": [...],
  "session_id": "uuid",
  "turn_number": 1
}
```

---

## Database Schema

```sql
-- users: identity only; income data lives in browser localStorage
id UUID PRIMARY KEY, email TEXT UNIQUE, password_hash TEXT,
full_name TEXT, phone TEXT, cnic TEXT, ntn TEXT, city TEXT, province TEXT, tax_year TEXT

-- sessions
id UUID PRIMARY KEY, user_id UUID → users, title TEXT, created_at, updated_at

-- messages
id UUID PRIMARY KEY, session_id UUID → sessions,
role TEXT (user|assistant), content TEXT, canvas_data JSONB
```

---

## Tax Regimes

| Regime | Meaning | Withholding Treatment |
|---|---|---|
| `NORMAL` | Slab tax on net income | Withholding is adjustable against liability |
| `FINAL` | Tax equals withholding — nothing more | Withholding is final; no refund |
| `SEPARATE` | Flat rate (e.g., capital gains) | Own separate calculation |
| `EXEMPT` | Not taxable | No tax, no withholding adjustment |

**Income heads:** salary, business, property, capital_gains, other_sources

**Key ordinance sections:** Sec 149 (salary withholding), Sec 155 (property withholding), Sec 113 (minimum tax), Sec 4C (super tax), Sec 61 (donations credit), Sec 60 (zakat), Second Schedule (exemptions), Eighth Schedule (capital gains on securities)

---

## Known Limitations

- **Social auth** — Google/NADRA buttons are UI stubs
- **Voice input** — microphone button is not wired up
- **CORS** — hardcoded to `localhost:5173`; must be updated before production deployment
- **Credentials in repo** — `.env` contains real keys; rotate before any public deployment
- **AOP / Company filers** — models support them but prompts are optimised for individual filers
- **Super tax / minimum tax edge cases** — may not classify correctly for complex corporate scenarios

---

## Running Tests

```bash
conda activate Tax_Sathi
cd backend
pytest tests/
```

Tests cover the full e2e pipeline and each inter-module boundary (extractor→retriever, retriever→interpreter, interpreter→calculator).

---

*Tax year: FY 2025-26 (Pakistan) | Built with FastAPI + LangGraph + Groq*
