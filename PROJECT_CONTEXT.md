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
| Auth | JWT (python-jose) + bcrypt |
| Document retrieval | Custom tree-index over FBR markdown (~250k chars) |

---

## 3. Directory Structure

```
Tax_Sathi/
├── .env                                          # All credentials + LLM config (see Section 4)
├── PROJECT_CONTEXT.md                            # This file
├── supabase_schema.sql                           # DB schema reference
│
├── backend-prompts/                              # Engineering reference prompts (used to build modules)
│   └── *.md
│
├── backend/
│   ├── main.py                                   # FastAPI app factory + all router mounts
│   ├── config.py                                 # BackendSettings: max_clarification_turns + pipeline node LLM config
│   ├── database.py                               # Supabase client singleton
│   ├── requirements.txt
│   │
│   ├── auth/
│   │   ├── router.py                             # POST /signup, /login, GET /me
│   │   ├── models.py                             # SignupRequest, LoginRequest, AuthResponse, TokenData
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
│   │   ├── prompts/system_prompt.py              # LLM system prompt for extraction
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
│   │   ├── query_builder.py                      # build_retrieval_query(TaxpayerData) → str
│   │   └── prompts/tree_reasoning.py             # TREE_REASONING_PROMPT + CROSS_REF_PROMPT
│   │
│   ├── tax_interpreter/                          # Module 3: LLM classifies income/deductions/credits
│   │   ├── interpreter.py                        # interpret_tax_situation(data, retrieval) → TaxComputationPlan
│   │   ├── config.py                             # TAX_INTERPRETER_* env vars
│   │   ├── router.py                             # POST /api/v1/tax-interpreter (debug standalone)
│   │   ├── models.py                             # TaxComputationPlan, IncomeClassification, etc.
│   │   └── prompts/system_prompt.py              # LLM system prompt for legal interpretation
│   │
│   ├── tax_calculator/                           # Module 4: Pure arithmetic, zero LLM calls
│   │   ├── calculator.py                         # calculate_tax(plan) → TaxCalculationResult
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
│       ├── auth.jsx                              # AuthScreen (login/signup with sliding pill tab)
│       ├── setup.jsx                             # ProfileSetup (4-step wizard after signup)
│       ├── workspace.jsx                         # Main chat UI: message bubbles + prompt input
│       ├── sidebar.jsx                           # Session list, nav items, user footer
│       ├── output.jsx                            # ★ CanvasView: all 5 pipeline trace sections
│       ├── trace.jsx                             # TraceDrawer: backend trace side panel
│       ├── structured.jsx                        # StructuredModal: structured income/deduction entry
│       ├── calendar.jsx                          # TaxCalendarModal
│       ├── profile.jsx                           # ProfileModal (identity + income + deductions)
│       ├── icons.jsx                             # All SVG icons (Icon component)
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
```

Config classes: each module has `backend/<module>/config.py` with a `pydantic_settings.BaseSettings` subclass that reads its own env prefix. The pipeline nodes read from `backend/config.py` (`BackendSettings`, prefix `PIPELINE_`).

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
    taxpayer_data: dict | None          # TaxpayerData serialised
    extraction_status: Literal["complete", "needs_clarification", "not_started"]
    clarification_questions: list[dict]
    clarification_turn: int
    retrieval_result: dict | None
    interpretation_result: dict | None
    calculation_result: dict | None

    # Canvas traces (one per stage, consumed by response_node)
    extraction_trace: dict | None
    retrieval_trace: dict | None
    interpretation_trace: dict | None
    calculation_trace: dict | None

    # FBR Q&A
    retrieved_sections_for_qa: list[dict]
    qa_answer: str | None

    # Output (set by terminal nodes, read by response_node)
    assistant_message: str
    response_stage: Literal["clarification_needed", "extraction_complete", "qa_response", "general_response"]
    turn_number: int

    # Assembled final response (read by pipeline/router.py after graph.ainvoke())
    final_response: dict | None

    error: str | None
    current_node: str
```

### Node Responsibilities

| Node | File | What it does |
|---|---|---|
| `router_node` | `nodes/router_node.py` | Calls LLM (fast model), writes `intent` + `router_reasoning` |
| `extraction_node` | `nodes/extraction_node.py` | Calls `extract_tax_data()`, writes `taxpayer_data`, `extraction_status`, `extraction_trace`, `clarification_questions` |
| `retrieval_node` | `nodes/retrieval_node.py` | Calls `retrieve_relevant_sections()`, writes `retrieval_result`, `retrieval_trace` |
| `interpretation_node` | `nodes/interpretation_node.py` | Calls `interpret_tax_situation()`, writes `interpretation_result`, `interpretation_trace` |
| `calculation_node` | `nodes/calculation_node.py` | Calls `calculate_tax()`, writes `calculation_result`, `calculation_trace`, `assistant_message` |
| `fbr_qa_node` | `nodes/fbr_qa_node.py` | Uses tree-index for retrieval, calls LLM with QA prompt, writes `qa_answer`, `retrieval_trace` |
| `followup_node` | `nodes/followup_node.py` | If clarification pending: increments turn, routes to extraction. If calc done: calls LLM with calc context |
| `general_node` | `nodes/general_node.py` | Calls fast LLM for greeting or polite out-of-scope decline |
| `response_node` | `nodes/response_node.py` | Assembles `PipelineResponse` from all state traces, writes to `final_response` |

### Trace Builders (`backend/pipeline/helpers.py`)

Three pure functions that convert domain model outputs into canvas-friendly trace objects:
- `build_extraction_trace(ExtractionResponse) → ExtractionTrace`
- `build_interpretation_trace(TaxComputationPlan) → InterpretationTrace`
- `build_calculation_trace(TaxCalculationResult) → CalculationTrace`

### How the Router Calls the Graph (`backend/pipeline/router.py`)

```python
initial_state = _build_initial_state(request)          # dict with all state fields initialised
final_state   = await tax_sathi_graph.ainvoke(initial_state)
result        = PipelineResponse.model_validate(final_state["final_response"])
# Then: Supabase session persistence (best-effort)
return result
```

---

## 6. Tax Calculation Sub-Pipeline (Stages 1–4)

When intent is `tax_calculation`, the graph runs these four nodes in sequence:

### Stage 1: Extraction

```
extract_tax_data(user_message, conversation_history)
→ ExtractionResponse
    status: "complete" | "needs_clarification"
    extracted_data: TaxpayerData       (if complete)
    partial_data: TaxpayerData         (if needs_clarification — best effort so far)
    questions: list[ClarificationQuestion]
    message: str                       (conversational text to show user)
```

- If `needs_clarification` AND `turn < max_clarification_turns`: graph routes to `response_node` with questions
- If `turn >= max_clarification_turns` AND partial data exists: force-completes extraction
- Conversation history from all prior turns is passed to the LLM so answers accumulate across turns

### Stage 2: Retrieval (2-pass LLM)

```
retrieve_relevant_sections(taxpayer_data)
→ RetrievalResult
    sections: list[RetrievedSection]   (≤7 markdown sections from FBR doc)
    reasoning: str
    passes_used: int (1 or 2)
```

Pass 1: LLM sees tree titles + query → selects node IDs  
Pass 2: scans content for cross-referenced sections → LLM fetches any missing definitions  
Fallback: heuristic node IDs based on which income fields are populated

### Stage 3: Interpretation

```
interpret_tax_situation(taxpayer_data, retrieval_result)
→ TaxComputationPlan
    income_classifications: list[IncomeClassification]
        # head, tax_regime (NORMAL/FINAL/SEPARATE/EXEMPT), section, schedule, reasoning
    exemptions, deductions, tax_credits, withholding_classifications
    minimum_tax_applicable: bool
    super_tax_applicable: bool
    overall_reasoning: str
    caveats: list[str]
```

### Stage 4: Calculation (pure arithmetic, zero LLM calls)

```
calculate_tax(plan) → TaxCalculationResult
```

1. Compute tax per income source by regime
2. Sum income, subtract deductions, re-run slab on combined NORMAL income
3. Apply tax credits, check minimum tax & super tax
4. Subtract adjustable withholding → net payable or refund

---

## 7. FBR Policy Q&A (fbr_qa_node)

Handles questions like "What does Section 149 say?" without requiring personal income data.

1. Uses user's natural language question as the retrieval query (not TaxpayerData)
2. Runs the same tree-index LLM reasoning (Pass 1 only) to select ≤7 FBR sections
3. Sends retrieved section content + question to LLM with `FBR_QA_SYSTEM_PROMPT`
4. LLM answers citing specific section numbers, constrained to retrieved content only

The retriever model (`RULE_RETRIEVER_LLM_MODEL`) is reused for both the tree-reasoning and the answer generation in this node.

---

## 8. Pipeline Request & Response Contracts

### Request: `POST /api/v1/pipeline/chat`

```python
class PipelineRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] | None = None  # [{role, content}]
    session_id: str | None = None
    profile_context: str | None = None    # formatted profile block when "Use Profile" ON
```

### Response: `PipelineResponse`

```python
class PipelineResponse(BaseModel):
    stage: Literal["clarification_needed", "extraction_complete"]
    assistant_message: str
    questions: list[ClarificationQuestion] | None   # only if clarification_needed
    canvas: CanvasData
    taxpayer_data: TaxpayerData | None              # only if extraction_complete (tax calc path)
    retrieved_sections: list[RetrievedSection] | None
    session_id: str | None
    turn_number: int
```

> **Note:** `stage="extraction_complete"` is returned for all "final answer" responses — tax calculations, FBR Q&A, follow-ups, and general greetings. The frontend does not need to know which LangGraph path was taken.

### Canvas Data

```python
class CanvasData(BaseModel):
    steps: list[ProcessingStep]           # progress indicators (step name, status, summary)
    extraction: ExtractionTrace | None
    retrieval: RetrievalTrace | None
    interpretation: InterpretationTrace | None
    calculation: CalculationTrace | None
    raw_taxpayer_data: dict | None
```

Canvas shape varies by path:
- Tax calc: all 5 sections populated
- FBR Q&A: only steps (2) + retrieval
- General/greeting: only steps (1)

---

## 9. All API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/signup` | — | Register → token |
| POST | `/api/v1/auth/login` | — | Login → token |
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

Auth flow: JWT stored in browser `localStorage` as `ts_token`, sent as `Authorization: Bearer <token>`. 7-day expiry, bcrypt passwords.

---

## 10. Database Schema (Supabase / PostgreSQL)

```sql
-- users
id            UUID PRIMARY KEY DEFAULT uuid_generate_v4()
email         TEXT UNIQUE NOT NULL
password_hash TEXT NOT NULL
full_name     TEXT
phone TEXT, cnic TEXT, ntn TEXT, city TEXT, province TEXT, tax_year TEXT
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

Income data, deductions, preferences are stored in **browser `localStorage`** — not in the DB. Only identity fields are in DB.

---

## 11. Frontend Architecture

### No Build Step

`index.html` loads React 18, Babel Standalone, and all `.jsx` files via `<script type="text/babel" src="...">`. Babel transpiles in the browser at runtime. No npm, no webpack, no Vite.

### App State Machine (`frontend/src/app.jsx`)

```
"boot"  → Check localStorage token → GET /me
           ├─ valid   → load sessions → "app"
           └─ invalid → "auth"

"auth"  → AuthScreen (login/signup with animated sliding pill tab)
           ├─ existing user → "app"
           └─ new user      → "setup"

"setup" → ProfileSetup (4-step wizard: identity, income, deductions, review)
           └─ complete → "app"

"app"   → Full workspace (Sidebar + Workspace + Canvas + Modals)
```

### Key State in App Root

```javascript
bootState        // "boot" | "auth" | "setup" | "app"
user             // { name, email, initials, filerStatus, ntn }
profile          // Full profile (from localStorage + DB merge)
sessions         // list of SessionSummary (sidebar)
currentSessionId // active session UUID
messages         // [{id, role, content, canvas}] — current session
activeCanvas     // canvas object from last assistant message
streaming        // bool — waiting for pipeline response
streamLabel      // "Extracting tax information…" etc.
pendingQuestions // list[ClarificationQuestion] | null
activeNav        // "chat" | "calendar" | "profile"
modal            // null | "profile" | "calendar"
```

### Frontend API Client (`frontend/src/api.jsx`)

All calls go through `window.API`:

```javascript
window.API = {
  login(email, password),
  signup(email, password, name),
  logout(),
  getCurrentUser(),
  getProfile(), saveProfile(profile), updateProfile(patch),
  getSessions(), createSession(title), getSession(id),
  deleteSession(id), updateSessionTitle(id, title),
  sendMessage(sessionId, message, conversationHistory, profileContext),
  formatProfileContext(profile),   // → string for profile_context field
  saveLocal(key, value), loadLocal(key),
  FBR_CATEGORIES, EMPTY_PROFILE,
};
```

### Profile Context Injection

When "Use Profile" is ON, `formatProfileContext(profile)` builds a structured text block (filer status, income types, deductions) that is sent as `profile_context`. The extractor prepends it to the user message so the LLM sees known facts without asking about them.

### Canvas Panel (`frontend/src/output.jsx`)

Renders `CanvasData` as 5 stagger-animated collapsible sections on the right:

1. **01 Processing Pipeline** — step-by-step status (✓/✗/●/—) with timing
2. **02 Tax Data Extracted** — extracted fields grid, missing fields, assumptions, confidence %
3. **03 FBR Rules Retrieved** — `SectionCard` per section (title, relevance, expandable content)
4. **04 Tax Rules Interpreted** — income classifications, deduction decisions, withholding treatment
5. **05 Tax Calculation** — full breakdown table: income by head, deductions, credits, net payable/refund

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

Dark mode: `[data-theme="dark"]` on `<html>`. Theme, density, layout are controlled by the TweaksPanel and persisted in `localStorage`.

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

### Dual Use

- **Tax calculation path:** query is built from `TaxpayerData` via `build_retrieval_query()`
- **FBR Q&A path:** query is the user's raw natural language question (in `fbr_qa_node.py`)

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

### Key Sections
Sec 149 (salary withholding), Sec 155 (property withholding), Sec 113 (minimum tax), Sec 4C (super tax), Sec 61 (donations), Sec 60 (zakat), Second Schedule (exemptions), Eighth Schedule (capital gains on securities)

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
python -m http.server 5173
# Open http://localhost:5173
```

No build step. CORS allows `localhost:5173`, `localhost:3000`, `127.0.0.1:5173`.

---

## 15. Common Patterns

### LangGraph Node Pattern

```python
async def my_node(state: TaxSathiState) -> dict:
    # Read from state
    data = state.get("some_field")
    # Do work
    result = await some_async_call(data)
    # Return only the fields this node updates
    return {
        "some_output_field": result,
        "current_node": "my_node",
    }
```

Nodes return partial state dicts; LangGraph merges them into the shared state.

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

All models use `.model_dump(mode="json")` for serialisation and `.model_validate(dict)` for deserialisation from state. Validators use `@field_validator` / `@model_validator`.

### Frontend JSX

All components register on `window`:
```javascript
window.AuthScreen = AuthScreen;
window.Workspace  = Workspace;
// ...
```
`app.jsx` reads them from `window` — no ES module imports (no build step).

---

## 16. Key Behaviours & Edge Cases

**Clarification turn limit:** After `PIPELINE_MAX_CLARIFICATION_TURNS` (default 5), the graph forces extraction from `partial_data` and continues. If no partial data, it returns a final clarification request.

**Profile context:** `profile_context` from the request is prepended to the extraction message as a `[User Profile Context]` block. The extractor LLM treats it as known facts and avoids re-asking those questions.

**Session persistence:** `pipeline/router.py` saves user + assistant messages to Supabase after every `/pipeline/chat` call. `canvas_data` is stored as JSONB on the assistant message row. Session title is auto-set from the first 50 chars of the first user message.

**FBR Q&A vs tax calculation routing:** The router distinguishes "I earn PKR 5M salary" (→ `tax_calculation`) from "What does Section 149 say?" (→ `fbr_policy_qa`) using a fast LLM call on every request.

**State isolation:** No LangGraph checkpointing. Each `/pipeline/chat` call creates a completely fresh state. Conversation continuity comes from `conversation_history` in the request body (frontend passes all prior turns).

**Canvas backward compatibility:** `PipelineResponse` and `CanvasData` schemas are unchanged from the pre-LangGraph version. The frontend renders identically regardless of which internal graph path was taken.

---

## 17. What Is Not Done Yet / Known Gaps

1. **Social auth** — Google/NADRA buttons exist but `window.API.socialAuth()` is a stub
2. **Voice input** — mic button is wired to a no-op
3. **Export/copy** — "Copy" button in canvas calls `onExport('copy')` but clipboard write may be a stub
4. **CORS in production** — currently hardcoded to `localhost:5173`; needs dynamic origin config before deployment
5. **`.env` in repo** — real credentials committed; must be rotated before any public deployment
6. **Minimum tax & super tax edge cases** — fields exist in all models but the interpreter LLM may not always classify them correctly for complex AOP/company scenarios
7. **AOP / Company taxpayers** — models support them but prompts and FBR retrieval are primarily optimised for individual filers

---

*Last updated: 2026-04-24. Reflects the LangGraph-restructured codebase after project cleanup.*
