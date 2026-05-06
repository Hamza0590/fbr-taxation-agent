# Tax Sathi — Full Project Context

> Drop this file into any conversation to give an AI model complete context about the Tax Sathi codebase: architecture, data flow, all endpoints, all models, and every key file.

---

## 1. What Is This Project?

**Tax Sathi** is an AI-powered Pakistani tax advisory web app. A taxpayer types a question in plain English or Urdu and the system:

- Calculates exact income tax liability with a full breakdown
- Answers FBR policy questions ("What does Section 149 say?", "When is the filing deadline?")
- Handles multi-turn clarification, session history, user profiles
- Shows a live canvas panel with the full reasoning trace

**Tax Year:** FY 2025-26 (Pakistan)

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12, Pydantic v2, LiteLLM |
| Orchestration | **LangGraph** (`StateGraph` with conditional routing) |
| LLMs | Groq API (llama-3.1-8b-instant, gpt-oss-20b/120b via OpenRouter) |
| Database | Supabase (PostgreSQL) |
| Frontend | Vanilla React 18 via Babel standalone (no build step) |
| Auth | JWT (python-jose) + bcrypt + Google OAuth 2.0 |
| Document retrieval | Custom tree-index over FBR markdown (~250k chars) |

---

## 3. Directory Structure

```
Tax_Sathi/
├── .env                                          # All credentials + LLM config (see Section 4)
├── .env.example                                  # Template — copy to .env and fill values
├── .gitignore                                    # Excludes .env, __pycache__, *.pyc, .pytest_cache/
├── PROJECT_CONTEXT.md                            # This file
├── supabase_schema.sql                           # DB schema + migration ALTER TABLE statements
│
├── backend-prompts/                              # Engineering reference prompts (used to build modules)
│   └── *.md
│
├── backend/
│   ├── main.py                                   # FastAPI app factory + all router mounts
│   ├── config.py                                 # BackendSettings (PIPELINE_ prefix) + CORSSettings (CORS_ prefix)
│   ├── database.py                               # Supabase client singleton
│   ├── requirements.txt
│   │
│   ├── auth/
│   │   ├── router.py                             # POST /signup, /login, /cnic-login, GET /me, /google/login, /google/callback
│   │   ├── models.py                             # SignupRequest, LoginRequest, CNICLoginRequest, AuthResponse, TokenData
│   │   └── utils.py                              # bcrypt hashing, JWT create/validate, get_current_user dependency
│   │
│   ├── profile/
│   │   ├── router.py                             # GET/PUT /api/v1/profile/
│   │   └── models.py                             # ProfileResponse, ProfileUpdateRequest
│   │
│   ├── sessions/
│   │   ├── router.py                             # GET/POST/GET/{id}/PUT/{id}/DELETE/{id} /api/v1/sessions/
│   │   └── models.py                             # SessionSummary, SessionDetail, MessageResponse
│   │
│   ├── pipeline/                                 # ★ CORE — LangGraph agentic pipeline
│   │   ├── graph.py                              # ★ StateGraph definition: nodes, conditional edges, compile()
│   │   ├── state.py                              # TaxSathiState TypedDict — shared state for all nodes
│   │   ├── helpers.py                            # Trace-builder functions (build_extraction/interpretation/calculation_trace)
│   │   ├── router.py                             # POST /api/v1/pipeline/chat → invokes tax_sathi_graph
│   │   └── models.py                             # PipelineRequest, PipelineResponse, CanvasData, all trace models
│   │   │
│   │   ├── nodes/
│   │   │   ├── router_node.py                    # Intent classifier (uses llama-3.1-8b-instant, fast)
│   │   │   ├── extraction_node.py                # Wraps extract_tax_data() → writes taxpayer_data to state
│   │   │   ├── retrieval_node.py                 # Wraps retrieve_relevant_sections() → writes retrieval_result
│   │   │   ├── interpretation_node.py            # Wraps interpret_tax_situation() → writes interpretation_result
│   │   │   ├── calculation_node.py               # Wraps calculate_tax() → writes calculation_result + assistant_message
│   │   │   ├── fbr_qa_node.py                    # FBR policy Q&A: tree-index retrieval + LLM answer
│   │   │   ├── followup_node.py                  # Routes clarification answers or answers post-calc follow-ups
│   │   │   ├── general_node.py                   # Greetings + out-of-scope responses
│   │   │   └── response_node.py                  # EXIT: assembles PipelineResponse from full state
│   │   │
│   │   └── prompts/
│   │       ├── router_prompt.py                  # ROUTER_SYSTEM_PROMPT — intent classification
│   │       └── fbr_qa_prompt.py                  # FBR_QA_SYSTEM_PROMPT + FOLLOWUP_SYSTEM_PROMPT
│   │
│   ├── tax_extractor/                            # Module 1: LLM extracts TaxpayerData
│   │   ├── extractor.py                          # extract_tax_data(message, history) → ExtractionResponse
│   │   ├── config.py                             # TAX_EXTRACTOR_* env vars
│   │   ├── router.py                             # POST /api/v1/tax-extractor (debug standalone)
│   │   ├── prompts/system_prompt.py              # LLM system prompt — includes AOP/company detection rules
│   │   └── models/
│   │       ├── taxpayer.py                       # TaxpayerData (identity + all income sources)
│   │       ├── income.py                         # SalaryIncome, BusinessIncome, RentalIncome, etc.
│   │       ├── deductions.py                     # Deductions model
│   │       ├── withholding.py                    # WithholdingTaxes model
│   │       ├── clarification.py                  # ClarificationQuestion
│   │       └── response.py                       # ExtractionResponse
│   │
│   ├── rule_retriever/                           # Module 2: Tree-walk + LLM picks FBR sections
│   │   ├── retriever.py                          # retrieve_relevant_sections(taxpayer_data) → RetrievalResult
│   │   ├── config.py                             # RULE_RETRIEVER_* env vars
│   │   ├── router.py                             # POST /api/v1/rule-retriever (debug standalone)
│   │   ├── models.py                             # RetrievedSection, RetrievalResult
│   │   ├── tree_index.py                         # Load & query hierarchical FBR document tree (JSON)
│   │   ├── content_fetcher.py                    # Fetch markdown content by line range
│   │   ├── query_builder.py                      # build_retrieval_query(TaxpayerData) → str (AOP/company aware)
│   │   └── prompts/tree_reasoning.py             # TREE_REASONING_PROMPT — includes AOP/company node rules
│   │
│   ├── tax_interpreter/                          # Module 3: LLM classifies income/deductions/credits
│   │   ├── interpreter.py                        # interpret_tax_situation(data, retrieval) → TaxComputationPlan
│   │   ├── config.py                             # TAX_INTERPRETER_* env vars
│   │   ├── router.py                             # POST /api/v1/tax-interpreter (debug standalone)
│   │   ├── models.py                             # TaxComputationPlan, IncomeClassification, etc.
│   │   └── prompts/system_prompt.py              # LLM prompt — explicit minimum tax + super tax + AOP/company rules
│   │
│   ├── tax_calculator/                           # Module 4: Pure arithmetic, zero LLM calls
│   │   ├── calculator.py                         # calculate_tax(plan) → TaxCalculationResult (+ min/super tax safeguards)
│   │   ├── router.py                             # POST /api/v1/tax-calculator (debug standalone)
│   │   └── models.py                             # TaxCalculationResult, IncomeHeadBreakdown, etc.
│   │
│   ├── tax_rules/                                # Static FBR rate tables (no LLM)
│   │   ├── lookup.py                             # compute_slab_tax(), compute_minimum_tax()
│   │   ├── rates/tax_year_2025_2026.py           # Tax slabs, schedules, rates for FY 2025-26
│   │   └── models.py                             # TaxSlab, RateTable
│   │
│   └── tests/                                    # Integration tests
│       ├── test_e2e_pipeline.py
│       ├── test_extractor_to_retriever.py
│       ├── test_retriever_to_interpreter.py
│       └── test_interpreter_to_calculator.py
│
├── frontend/
│   ├── index.html                                # Main entry — loads app.css + all JSX via Babel standalone
│   ├── app.css                                   # ★ Full stylesheet (design tokens, components, animations)
│   └── src/
│       ├── app.jsx                               # ★ Root: boot → auth → setup → app state machine
│       ├── api.jsx                               # ★ All backend API calls (window.API)
│       ├── data.jsx                              # Static data: SUGGESTIONS, CALENDAR, FBR_CATEGORIES
│       ├── auth.jsx                              # AuthScreen (login/signup + Google OAuth + CNIC mini-form)
│       ├── setup.jsx                             # ProfileSetup (4-step wizard after signup)
│       ├── workspace.jsx                         # Main chat UI: message bubbles + prompt input + mic button
│       ├── sidebar.jsx                           # Session list, nav items, user footer
│       ├── output.jsx                            # ★ CanvasView: all 5 pipeline trace sections + clipboard copy
│       ├── trace.jsx                             # TraceDrawer: backend trace side panel
│       ├── structured.jsx                        # StructuredModal: structured income/deduction entry
│       ├── calendar.jsx                          # TaxCalendarModal
│       ├── profile.jsx                           # ProfileModal (identity + income + deductions)
│       ├── icons.jsx                             # All SVG icons (Icon component) — includes eye, eyeOff, mic
│       └── tweaks.jsx                            # TweaksPanel: theme/layout/density controls
│
└── pre_processing_fbr_doc/
    ├── fbr_combined.md                           # Full FBR ITO 2001 as markdown (~250k chars)
    └── PageIndex-main/results/
        └── fbr_combined_structure.json           # ★ Hierarchical tree index of the FBR document
```

---

## 4. Environment Variables (`.env`)

Every LLM parameter for every module is in `.env`. Change model, temperature, or tokens without touching code.

```env
# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_jwt>

# ── Auth (JWT) ────────────────────────────────────────────────────────────────
AUTH_SECRET_KEY=<strong-random-secret>
AUTH_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_EXPIRE_DAYS=7

# ── Global pipeline behaviour ─────────────────────────────────────────────────
PIPELINE_MAX_CLARIFICATION_TURNS=5

# ── [1] Tax Extractor — deterministic, temperature 0.0 ───────────────────────
TAX_EXTRACTOR_LLM_MODEL=groq/llama-3.1-8b-instant
TAX_EXTRACTOR_LLM_API_KEY=gsk_...
TAX_EXTRACTOR_LLM_TEMPERATURE=0.0
TAX_EXTRACTOR_LLM_MAX_TOKENS=2000
TAX_EXTRACTOR_DEFAULT_TAX_YEAR=2025-2026

# ── [2] Rule Retriever — tree reasoning, 2-pass ───────────────────────────────
RULE_RETRIEVER_LLM_MODEL=groq/openai/gpt-oss-120b
RULE_RETRIEVER_LLM_API_KEY=gsk_...
RULE_RETRIEVER_LLM_TEMPERATURE=0.1
RULE_RETRIEVER_LLM_MAX_TOKENS=2000
RULE_RETRIEVER_MAX_NODES=7
RULE_RETRIEVER_MAX_PASSES=2
RULE_RETRIEVER_TREE_INDEX_PATH=./pre_processing_fbr_doc/PageIndex-main/results/fbr_combined_structure.json
RULE_RETRIEVER_MARKDOWN_PATH=./pre_processing_fbr_doc/fbr_combined.md

# ── [3] Tax Interpreter — legal classification, richer output ─────────────────
TAX_INTERPRETER_LLM_MODEL=groq/openai/gpt-oss-20b
TAX_INTERPRETER_LLM_API_KEY=gsk_...
TAX_INTERPRETER_LLM_TEMPERATURE=0.1
TAX_INTERPRETER_LLM_MAX_TOKENS=2000
TAX_INTERPRETER_DEFAULT_TAX_YEAR=2025-2026
TAX_INTERPRETER_MAX_SECTION_CHARS=600

# ── [4] Pipeline — Router node (runs on EVERY request, must be fastest) ───────
PIPELINE_LLM_API_KEY=gsk_...
PIPELINE_ROUTER_LLM_MODEL=groq/llama-3.1-8b-instant
PIPELINE_ROUTER_LLM_TEMPERATURE=0.0
PIPELINE_ROUTER_LLM_MAX_TOKENS=200

# ── [5] Pipeline — General / out-of-scope node ───────────────────────────────
PIPELINE_GENERAL_LLM_MODEL=groq/llama-3.1-8b-instant
PIPELINE_GENERAL_LLM_TEMPERATURE=0.5
PIPELINE_GENERAL_LLM_MAX_TOKENS=300

# ── [6] Pipeline — Follow-up handler node ────────────────────────────────────
PIPELINE_FOLLOWUP_LLM_MODEL=groq/llama-3.3-70b-versatile
PIPELINE_FOLLOWUP_LLM_TEMPERATURE=0.3
PIPELINE_FOLLOWUP_LLM_MAX_TOKENS=800

# ── Google OAuth ──────────────────────────────────────────────────────────────
GOOGLE_CLIENT_ID=<google-oauth-client-id>
GOOGLE_CLIENT_SECRET=<google-oauth-client-secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
GOOGLE_FRONTEND_REDIRECT=http://localhost:3000

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173
```

Config classes:
- Each module has `backend/<module>/config.py` with a `pydantic_settings.BaseSettings` subclass reading its own env prefix.
- `backend/config.py` has `BackendSettings` (prefix `PIPELINE_`) and `CORSSettings` (prefix `CORS_`).
- `backend/auth/router.py` has `GoogleOAuthSettings` (prefix `GOOGLE_`) with `@lru_cache`.

---

## 5. Pipeline Architecture (LangGraph)

The pipeline is a **LangGraph `StateGraph`** defined in `backend/pipeline/graph.py`. Every request creates a fresh graph invocation with no persistent checkpointing — conversation continuity comes from `conversation_history` in the request.

### Graph Shape

```
                    ┌─────────────────────┐
    ENTRY ──────►   │   router_node        │  (classifies intent)
                    └──────┬──────────────┘
                           │
          ┌────────────────┼──────────────────┬───────────────────┐
          ▼                ▼                  ▼                   ▼
    extraction_node    fbr_qa_node       followup_node       general_node
          │                │                  │                   │
          │ [needs_clarification]             [needs_clarification]
          │      ▼                            │     ▼
          │  response_node              extraction_node
          │ [complete]                        │ [complete]
          ▼                                  ▼
    retrieval_node                     retrieval_node
          │                                  ...
          ▼
    interpretation_node
          │
          ▼
    calculation_node
          │
          └──────────────────────────────────────────►  response_node  ──► END
```

### Intent Classification (router_node)

| Intent | Description | Path |
|---|---|---|
| `tax_calculation` | User provides income/financial data | extraction → retrieval → interpretation → calculation → response |
| `fbr_policy_qa` | Asks about FBR rules/sections/deadlines | fbr_qa → response |
| `follow_up` | Answering a clarification OR asking about a prior result | followup → (extraction or response) |
| `general_greeting` | Hi, thanks, what can you do? | general → response |
| `out_of_scope` | Unrelated question | general → response |

### Shared Graph State (`backend/pipeline/state.py`)

```python
class TaxSathiState(TypedDict, total=False):
    # Input
    user_message: str
    conversation_history: list[dict]    # [{role, content}, ...]
    session_id: str | None
    profile_context: str | None

    # Router output
    intent: Literal["tax_calculation", "fbr_policy_qa", "follow_up", "general_greeting", "out_of_scope"]
    router_reasoning: str

    # Tax calculation pipeline
    taxpayer_data: dict | None
    extraction_status: Literal["complete", "needs_clarification", "not_started"]
    clarification_questions: list[dict]
    clarification_turn: int
    retrieval_result: dict | None
    interpretation_result: dict | None
    calculation_result: dict | None

    # Canvas traces
    extraction_trace: dict | None
    retrieval_trace: dict | None
    interpretation_trace: dict | None
    calculation_trace: dict | None

    # FBR Q&A
    retrieved_sections_for_qa: list[dict]
    qa_answer: str | None

    # Output
    assistant_message: str
    response_stage: Literal["clarification_needed", "extraction_complete", "qa_response", "general_response"]
    turn_number: int
    final_response: dict | None
    error: str | None
    current_node: str
```

---

## 6. Tax Calculation Sub-Pipeline (Stages 1–4)

### Stage 1: Extraction

```
extract_tax_data(user_message, conversation_history)
→ ExtractionResponse
    status: "complete" | "needs_clarification"
    extracted_data: TaxpayerData
    partial_data: TaxpayerData
    questions: list[ClarificationQuestion]
    message: str
```

Extractor prompt now includes explicit rules for detecting:
- **AOP**: keywords "partnership", "firm", "we/our business", "hamare firm" → `taxpayer_type = "aop"`
- **Company**: keywords "Pvt Ltd", "private limited", "limited company" → `taxpayer_type = "company"`
- For AOP/company: asks for NTN, turnover, and (for companies) small-company status.

### Stage 2: Retrieval (2-pass LLM)

```
retrieve_relevant_sections(taxpayer_data) → RetrievalResult
```

`build_retrieval_query()` now appends type-specific search terms:
- AOP → adds `"AOP Association of Persons Section 92 Section 93 Section 94 minimum tax Section 113"`
- Company → adds `"company corporate tax Section 113 Fourth Schedule corporate rate 29 percent small company"`

Tree-reasoning prompt has explicit node-selection rules for AOP (Sections 92–94, AOP slabs) and company (Fourth Schedule, corporate rates).

### Stage 3: Interpretation

```
interpret_tax_situation(taxpayer_data, retrieval_result) → TaxComputationPlan
```

Prompt contains a dedicated **MINIMUM TAX AND SUPER TAX** block:
- **Section 113 (Minimum Tax)**: set `minimum_tax_applicable=true` whenever `business_income` is present; rate = 1.25% of turnover; AOP threshold PKR 100M.
- **Section 4C (Super Tax)**: set `super_tax_applicable=true` when total income > PKR 150M; tiered rates 1%–10%; LLM must name the applicable tier in `overall_reasoning`.
- **Company**: flat 29% rate (20% for small companies); individual slabs must NOT be applied.

### Stage 4: Calculation (pure arithmetic, zero LLM calls)

After Steps 6 and 7, safeguards log warnings and append caveats if:
- `minimum_tax_applicable=True` but `minimum_tax_amount` is 0 or None
- `super_tax_applicable=True` but `super_tax_amount` is 0 or None

---

## 7. FBR Policy Q&A (fbr_qa_node)

Handles questions like "What does Section 149 say?" without requiring personal income data.

1. Uses user's natural language question as the retrieval query
2. Runs tree-index LLM reasoning (Pass 1 only)
3. Sends retrieved sections + question to LLM with `FBR_QA_SYSTEM_PROMPT`
4. LLM answers citing specific section numbers

---

## 8. Pipeline Request & Response Contracts

### Request: `POST /api/v1/pipeline/chat`

```python
class PipelineRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] | None = None
    session_id: str | None = None
    profile_context: str | None = None
```

### Response: `PipelineResponse`

```python
class PipelineResponse(BaseModel):
    stage: Literal["clarification_needed", "extraction_complete"]
    assistant_message: str
    questions: list[ClarificationQuestion] | None
    canvas: CanvasData
    taxpayer_data: TaxpayerData | None
    retrieved_sections: list[RetrievedSection] | None
    session_id: str | None
    turn_number: int
```

### Canvas Data

```python
class CanvasData(BaseModel):
    steps: list[ProcessingStep]
    extraction: ExtractionTrace | None
    retrieval: RetrievalTrace | None
    interpretation: InterpretationTrace | None
    calculation: CalculationTrace | None
    raw_taxpayer_data: dict | None
```

---

## 9. All API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/signup` | — | Register with email + password (optional CNIC) → token |
| POST | `/api/v1/auth/login` | — | Login with email + password → token |
| POST | `/api/v1/auth/cnic-login` | — | Login with CNIC + password → token |
| GET | `/api/v1/auth/google/login` | — | Redirect to Google consent screen |
| GET | `/api/v1/auth/google/callback` | — | Google sends code here → upsert user → redirect to frontend with `?token=&is_new=1` |
| GET | `/api/v1/auth/me` | JWT | Current user from DB |
| GET | `/api/v1/profile/` | JWT | Fetch identity profile |
| PUT | `/api/v1/profile/` | JWT | Update profile fields |
| GET | `/api/v1/sessions/` | JWT | List sessions (with preview) |
| POST | `/api/v1/sessions/` | JWT | Create new session |
| GET | `/api/v1/sessions/{id}` | JWT | Session + full message history |
| PUT | `/api/v1/sessions/{id}` | JWT | Update session title |
| DELETE | `/api/v1/sessions/{id}` | JWT | Delete session + cascade messages |
| **POST** | **`/api/v1/pipeline/chat`** | **JWT** | **Main chat endpoint (LangGraph)** |
| POST | `/api/v1/tax-extractor` | JWT | Debug: run Module 1 standalone |
| POST | `/api/v1/rule-retriever` | JWT | Debug: run Module 2 standalone |
| POST | `/api/v1/tax-interpreter` | JWT | Debug: run Module 3 standalone |
| POST | `/api/v1/tax-calculator` | JWT | Debug: run Module 4 standalone |
| GET | `/health` | — | `{"status": "ok"}` |

### Auth Flow Summary

**Email/Password:** JWT stored in `localStorage` as `ts_token`, sent as `Authorization: Bearer <token>`. 7-day expiry, bcrypt passwords.

**Google OAuth:**
1. Browser → `GET /api/v1/auth/google/login` → redirect to Google
2. User approves → Google → `GET /api/v1/auth/google/callback?code=...`
3. Backend exchanges code for access_token → fetches email+name from Google
4. Upserts user in Supabase (`auth_provider='google'`, `password_hash=''`)
5. Mints JWT → redirects to `{GOOGLE_FRONTEND_REDIRECT}?token={jwt}&is_new=1` (new users only get `is_new=1`)
6. Frontend boot phase detects `?token=`, stores to `localStorage`, cleans URL, boots app or setup

**CNIC Login:** `POST /api/v1/auth/cnic-login` — looks up user by `cnic` field, verifies bcrypt password, returns same `AuthResponse` shape. CNIC must match format `XXXXX-XXXXXXX-X` (validated by Pydantic `@field_validator`).

---

## 10. Database Schema (Supabase / PostgreSQL)

```sql
-- users
id            UUID PRIMARY KEY DEFAULT uuid_generate_v4()
email         TEXT UNIQUE NOT NULL
password_hash TEXT NOT NULL          -- empty string for Google OAuth users
full_name     TEXT
phone TEXT, ntn TEXT, city TEXT, province TEXT, tax_year TEXT
cnic          TEXT UNIQUE            -- optional; used for CNIC login
auth_provider TEXT DEFAULT 'email'  -- 'email' | 'google'
created_at    TIMESTAMPTZ DEFAULT now()

-- sessions
id         UUID PRIMARY KEY DEFAULT uuid_generate_v4()
user_id    UUID REFERENCES users(id) ON DELETE CASCADE
title      TEXT DEFAULT 'New Chat'
created_at TIMESTAMPTZ DEFAULT now()
updated_at TIMESTAMPTZ DEFAULT now()

-- messages
id          UUID PRIMARY KEY DEFAULT uuid_generate_v4()
session_id  UUID REFERENCES sessions(id) ON DELETE CASCADE
role        TEXT CHECK (role IN ('user', 'assistant'))
content     TEXT
canvas_data JSONB    -- full CanvasData JSON (for session restore)
created_at  TIMESTAMPTZ DEFAULT now()
```

Migration SQL (run in Supabase SQL editor for existing DBs):
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider TEXT DEFAULT 'email';
ALTER TABLE users ADD COLUMN IF NOT EXISTS cnic TEXT UNIQUE;
```

Income data, deductions, preferences are stored in **browser `localStorage`** — not in the DB. Only identity fields are in DB.

---

## 11. Frontend Architecture

### No Build Step

`index.html` loads React 18, Babel Standalone, and all `.jsx` files via `<script type="text/babel" src="...?v=N">`. Babel transpiles in the browser at runtime. Cache is busted by incrementing `?v=N` in `index.html` after any JS change.

### App State Machine (`frontend/src/app.jsx`)

```
"boot"  → Check localStorage for ts_token
           Also check URL ?token= param (Google OAuth callback)
             └─ if found: store to localStorage, clean URL
           → Check ?is_new=1 param (new Google user)
           → GET /me
           ├─ valid + is_new=1  → "setup"
           ├─ valid             → load sessions → "app"
           └─ invalid           → "auth"

"auth"  → AuthScreen (login/signup + Google button + CNIC mini-form)
           ├─ existing user     → "app"
           └─ new user          → "setup"

"setup" → ProfileSetup (4-step wizard: identity, income, deductions, review)
           └─ complete          → "app"

"app"   → Full workspace (Sidebar + Workspace + Canvas + Modals)
```

New users are routed to "setup" from ALL auth paths:
- Email signup → `onAuth(res, { isSignup: true })` → `!res.hasProfile` → setup
- Google new user → `is_new=1` in URL → boot phase → setup
- CNIC login on new device → `!loadLocal("profile_extended")` → `forceSetup: true` → setup

### Frontend API Client (`frontend/src/api.jsx`)

All calls go through `window.API`:

```javascript
window.API = {
  // Auth
  login(email, password),
  signup(email, password, name),
  googleLogin(),           // redirects browser to /api/v1/auth/google/login
  cnicLogin(cnic, password),
  logout(),
  getCurrentUser(),

  // Profile
  getProfile(), saveProfile(profile), updateProfile(patch),
  formatProfileContext(profile),   // → string for profile_context field

  // Sessions
  getSessions(), createSession(title), getSession(id),
  deleteSession(id), updateSessionTitle(id, title),

  // Chat
  sendMessage(sessionId, message, conversationHistory, profileContext),

  // Utilities
  saveLocal(key, value), loadLocal(key),
  getToken(),
  FBR_CATEGORIES, EMPTY_PROFILE,
};
```

### Voice Input (`frontend/src/workspace.jsx`)

- Mic button added to the prompt toolbar (hidden in browsers without `SpeechRecognition` support, e.g. Firefox).
- Uses `window.SpeechRecognition || window.webkitSpeechRecognition`.
- `lang = "en-US"`, `interimResults = false`, `maxAlternatives = 1`.
- While active: button shows `.voice-active` CSS class (pulsing red indicator from `app.css`).
- On result: transcript is set as the prompt input value.
- On error: silently logged, UI does not crash.

### Canvas Export (`frontend/src/output.jsx`)

- **Copy button** in canvas header performs real clipboard copy.
- Serialises `CanvasData` into human-readable plain text (extraction fields, FBR sections, tax calculation summary).
- Uses `navigator.clipboard.writeText()` with `document.execCommand('copy')` fallback for non-HTTPS.
- Button label changes to "Copied!" for 2 seconds, then reverts. No new CSS classes.

### Auth Screen (`frontend/src/auth.jsx`)

- **Email/Password**: standard login + signup tabs with sliding pill indicator.
- **Password visibility toggle**: eye/eyeOff icon button inside all password fields (main form + CNIC form). `tabIndex={-1}` to not interrupt keyboard navigation.
- **Google button**: calls `window.API.googleLogin()` — browser redirect, no popup.
- **CNIC / NADRA button**: toggles inline mini-form with CNIC field + password field. Client-side format validation (`XXXXX-XXXXXXX-X`) before API call. Error shown inline.

### CSS & Design System (`frontend/app.css`)

```css
--bg: #f7f4ee          /* page background (cream) */
--bg-raised: #fffdf7   /* card surfaces */
--bg-sunk: #f1ede4     /* sidebar / sunken areas */
--ink: #1a1f1b         /* primary text */
--forest: #2e4a36      /* primary brand green */
--amber: #b8833a       /* warning */
--rose: #a04940        /* error */
--line: #e4dfd3        /* borders */
```

`.voice-active` — pulsing red ring animation used for the active mic button state.

Dark mode: `[data-theme="dark"]` on `<html>`. Theme, density, layout controlled by TweaksPanel, persisted in `localStorage`.

---

## 12. FBR Document Retrieval System

### Document
`pre_processing_fbr_doc/fbr_combined.md` — Full Income Tax Ordinance 2001 as markdown (~250k chars).

### Tree Index
`pre_processing_fbr_doc/PageIndex-main/results/fbr_combined_structure.json`:
```json
{ "node_id": "3.2.1", "title": "Section 149 — Salary Withholding",
  "depth": 3, "line_start": 2554, "line_end": 2612, "children": [...] }
```

### 2-Pass Retrieval

**Pass 1:** LLM sees flattened tree (titles only) + query → responds with `{"node_ids": [...], "reasoning": "..."}`
**Pass 2:** Scans fetched content for cross-referenced section numbers → LLM fills any missing definitions
**Fallback:** Heuristic node IDs keyed by which income fields are populated

---

## 13. Tax Regimes & Income Heads

### Tax Regimes

| Regime | Meaning | Withholding treatment |
|---|---|---|
| `NORMAL` | Normal slab tax | Withholding is adjustable (deducted from liability) |
| `FINAL` | Tax = withholding, no more | Withholding is final — no refund |
| `SEPARATE` | Flat rate (e.g., capital gains) | Own separate calculation |
| `EXEMPT` | Not taxable | No tax, no adjustment |

### Income Heads
`salary`, `business`, `property`, `capital_gains`, `other_sources`

### Taxpayer Types
- `individual` — slab-based (salary or non-salaried slabs)
- `aop` — same slab table as non-salaried individuals; minimum tax applies when turnover > PKR 100M; partner shares taxed in partner's own return
- `company` — flat 29% (20% for small companies: paid-up capital < PKR 25M, turnover < PKR 250M); Section 113 minimum tax applies

### Key Sections
Sec 12 (salary), Sec 18 (business), Sec 15 (property), Sec 37/38 (capital gains), Sec 92–94 (AOP), Sec 113 (minimum tax), Sec 4C (super tax), Sec 61 (donations), Sec 60 (zakat), Second Schedule (exemptions), Fourth Schedule (companies), Eighth Schedule (capital gains on securities)

---

## 14. Running the Project

### Backend

```bash
conda activate Tax_Sathi
cd "E:/Semester 6/NLP/Project/Tax_Sathi"
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
# API docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

No build step. CORS origins are configured via `CORS_ALLOWED_ORIGINS` in `.env`.

---

## 15. Common Patterns

### LangGraph Node Pattern

```python
async def my_node(state: TaxSathiState) -> dict:
    data = state.get("some_field")
    result = await some_async_call(data)
    return {
        "some_output_field": result,
        "current_node": "my_node",
    }
```

### Module Config Pattern

```python
class ModuleSettings(BaseSettings):
    llm_model: str = "groq/..."
    llm_api_key: str = ""
    llm_temperature: float = 0.1
    model_config = {"env_prefix": "MODULE_", "env_file": ".env", "extra": "ignore"}

@lru_cache
def get_settings() -> ModuleSettings:
    return ModuleSettings()
```

### LLM Call Pattern

```python
from litellm import acompletion

response = await acompletion(
    model=settings.llm_model,
    messages=[{"role": "system", "content": PROMPT}, *history, {"role": "user", "content": msg}],
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
    api_key=settings.llm_api_key or None,
)
raw = response.choices[0].message.content
```

### Pydantic v2

All models use `.model_dump(mode="json")` for serialisation and `.model_validate(dict)` for deserialisation. Validators use `@field_validator` / `@model_validator`.

### Frontend JSX

```javascript
window.AuthScreen = AuthScreen;
window.Workspace  = Workspace;
// app.jsx reads from window — no ES module imports (no build step)
```

---

## 16. Key Behaviours & Edge Cases

**Clarification turn limit:** After `PIPELINE_MAX_CLARIFICATION_TURNS` (default 5), forces extraction from `partial_data`.

**Profile context:** `profile_context` from the request is prepended to the extraction message as a `[User Profile Context]` block.

**Session persistence:** `pipeline/router.py` saves user + assistant messages to Supabase after every `/pipeline/chat` call.

**FBR Q&A vs tax calculation routing:** Router LLM distinguishes income statements from policy questions on every request.

**State isolation:** No LangGraph checkpointing. Each `/pipeline/chat` call creates a completely fresh state.

**Google OAuth users:** `password_hash` is stored as empty string. `auth_provider='google'`. CNIC login is not available to them unless they set a CNIC+password via profile update.

**Minimum tax safeguard:** If `minimum_tax_applicable=True` but the calculator cannot compute it (turnover missing), a warning is logged and a caveat string is appended to the result.

**Super tax safeguard:** Same pattern — if `super_tax_applicable=True` but `super_tax_slabs` are absent from the rate table, a caveat is appended.

---

## 17. Implementation Status

All 7 originally listed gaps have been implemented:

| # | Feature | Status | Key Files |
|---|---|---|---|
| 1A | Google OAuth login | ✓ Done | `backend/auth/router.py`, `frontend/src/auth.jsx`, `frontend/src/app.jsx` |
| 1B | CNIC + Password login | ✓ Done | `backend/auth/router.py`, `backend/auth/models.py`, `frontend/src/auth.jsx` |
| 2 | Voice input (Web Speech API) | ✓ Done | `frontend/src/workspace.jsx` |
| 3 | Export / clipboard copy | ✓ Done | `frontend/src/output.jsx` |
| 4 | CORS for production | ✓ Done | `backend/config.py`, `backend/main.py`, `.env` |
| 5 | `.env` security + schema file | ✓ Done | `.gitignore`, `.env.example`, `supabase_schema.sql` |
| 6 | Minimum tax & super tax edge cases | ✓ Done | `backend/tax_interpreter/prompts/system_prompt.py`, `backend/tax_calculator/calculator.py` |
| 7 | AOP / Company taxpayer support | ✓ Done | `backend/tax_extractor/prompts/system_prompt.py`, `backend/rule_retriever/prompts/tree_reasoning.py`, `backend/rule_retriever/query_builder.py` |

Additional improvements made alongside the gaps:
- Password visibility toggle (eye/eyeOff) on all auth form password fields
- New Google users and CNIC users on new devices are routed to ProfileSetup before the main app
- Browser cache busting via `?v=N` query string on all script tags in `index.html`

---

*Last updated: 2026-05-06. Reflects all 7 gap implementations and subsequent auth UX improvements.*
