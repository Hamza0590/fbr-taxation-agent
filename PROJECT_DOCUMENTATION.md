# Tax Sathi — Project Documentation

> Version 0.1.0 | Tax Year 2025-2026 | Pakistan Federal Board of Revenue

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Repository Structure](#3-repository-structure)
4. [Environment Configuration](#4-environment-configuration)
5. [Database Schema](#5-database-schema)
6. [Backend Architecture](#6-backend-architecture)
7. [Pipeline Data Flow](#7-pipeline-data-flow)
8. [FBR Document Retrieval System](#8-fbr-document-retrieval-system)
9. [Frontend Architecture](#9-frontend-architecture)
10. [Auth Flows](#10-auth-flows)
11. [All API Endpoints](#11-all-api-endpoints)
12. [Key Design Decisions](#12-key-design-decisions)
13. [Known Gaps and Future Work](#13-known-gaps-and-future-work)
14. [Running the Project](#14-running-the-project)

---

## 1. Project Overview

Tax Sathi is a conversational Pakistani income tax assistant built to help individuals, freelancers, businesses, and associations of persons (AOPs) understand and compute their tax liability under the Income Tax Ordinance 2001. The application allows users to type their tax situation in plain English or Urdu, ask questions about FBR rules, and receive structured, auditable answers that cite specific sections of the law.

The core problem Tax Sathi solves is that Pakistani tax law is sprawling, frequently amended, and inaccessible to non-experts. A salaried individual earning income across multiple streams — salary, rental income, bank profit, capital gains — faces a web of overlapping sections, schedules, exemptions, withholding rules, and filer/non-filer distinctions. Tax Sathi automates the retrieval of only the relevant sections for a given taxpayer, interprets those sections using a large language model, then applies deterministic arithmetic to produce a verifiable tax computation.

Tax Sathi is targeted at the tax year 2025-2026 (July 2025 to June 2026) and incorporates Finance Act 2025 amendments. Rate tables are hardcoded from the First Schedule of the Income Tax Ordinance, which means calculations are reproducible without further LLM calls and can be independently verified.

The system is technically distinguished by a deliberate separation of concerns: natural language extraction, legal interpretation, and arithmetic calculation are three separate, sequentially chained modules. The LLM is only permitted to make legal classification decisions (which income head? which tax regime? which schedule? is this deduction allowed?) while the actual tax arithmetic is performed by a deterministic Python calculator that operates on a well-typed Pydantic plan object produced by the LLM. This hybrid architecture prevents the LLM from "making up" numbers while preserving its ability to reason about law.

---

## 2. Tech Stack

| Technology | Role | Where it appears |
|---|---|---|
| Python 3.11+ | Primary backend language | All backend modules |
| FastAPI | REST API framework | `backend/main.py`, all routers |
| LangGraph | Pipeline orchestration (stateful DAG) | `backend/pipeline/graph.py` |
| LiteLLM | Unified LLM client (model-agnostic) | All nodes that call an LLM |
| Groq API | LLM inference provider (default) | Via LiteLLM with `groq/` prefix |
| Pydantic v2 | Data validation and settings | All models, all config classes |
| pydantic-settings | Environment variable config | All `*Settings` / `*Config` classes |
| Supabase (PostgreSQL) | Database and storage | `backend/database.py`, all routers |
| python-jose + bcrypt | JWT auth and password hashing | `backend/auth/utils.py` |
| httpx | Async HTTP client (Google OAuth) | `backend/auth/router.py` |
| React 18 (UMD) | Frontend UI framework | `frontend/` |
| Babel Standalone | In-browser JSX transpilation | `frontend/index.html` |
| DM Sans + JetBrains Mono | Typography | `frontend/app.css` |
| SMTP (Gmail) | Password reset emails | `backend/auth/email.py` |

---

## 3. Repository Structure

```
Tax_Sathi/
├── .env.example                   # Template for all required environment variables
├── .gitignore                     # Excludes .env, __pycache__, .pyc, .pytest_cache
├── supabase_schema.sql            # SQL DDL for all four database tables + migration statements
├── PROJECT_CONTEXT.md             # High-level project intent and design philosophy
├── IMAGE_UPLOAD_PROMPT.md         # Prompt instructions file for image upload feature (not read)
├── GENERATE_DOCS_PROMPT.md        # Instructions that generated this document (not read)
│
├── backend/
│   ├── __init__.py                # Package version marker (0.1.0)
│   ├── main.py                    # FastAPI app factory; mounts all routers; CORS config
│   ├── config.py                  # CORSSettings + BackendSettings (pipeline model configs)
│   ├── database.py                # Supabase client singleton
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── config.py              # AuthSettings: SMTP config, reset token TTL, frontend URL
│   │   ├── email.py               # send_password_reset_email() via smtplib
│   │   ├── models.py              # SignupRequest, LoginRequest, CNICLoginRequest, AuthResponse, etc.
│   │   ├── router.py              # /signup, /login, /cnic-login, /me, /google/*, /forgot-password, /reset-password
│   │   └── utils.py               # hash_password, verify_password, create_access_token, get_current_user
│   │
│   ├── profile/
│   │   ├── models.py              # ProfileResponse, ProfileUpdateRequest
│   │   └── router.py              # GET/PUT /api/v1/profile/
│   │
│   ├── sessions/
│   │   ├── models.py              # SessionSummary, SessionDetail, MessageResponse, CreateSessionRequest
│   │   └── router.py              # CRUD for sessions and messages
│   │
│   ├── pipeline/
│   │   ├── graph.py               # LangGraph StateGraph definition; compiled tax_sathi_graph
│   │   ├── helpers.py             # build_extraction_trace, build_interpretation_trace, build_calculation_trace
│   │   ├── models.py              # PipelineRequest/Response, CanvasData, all trace models
│   │   ├── router.py              # POST /api/v1/pipeline/chat; Supabase message persistence
│   │   ├── state.py               # TaxSathiState TypedDict (all graph state fields)
│   │   ├── nodes/
│   │   │   ├── __init__.py        # Re-exports all node functions
│   │   │   ├── router_node.py     # Intent classification (LLM)
│   │   │   ├── extraction_node.py # Calls tax_extractor; populates taxpayer_data in state
│   │   │   ├── retrieval_node.py  # Calls rule_retriever; populates retrieval_result in state
│   │   │   ├── interpretation_node.py  # Calls tax_interpreter; populates interpretation_result
│   │   │   ├── calculation_node.py     # Calls tax_calculator; populates calculation_result
│   │   │   ├── fbr_qa_node.py     # FBR Q&A via tree retrieval + LLM answer generation
│   │   │   ├── followup_node.py   # Handles post-calculation follow-up and clarification routing
│   │   │   ├── general_node.py    # Greetings and out-of-scope responses
│   │   │   └── response_node.py   # Builds final PipelineResponse with CanvasData
│   │   └── prompts/
│   │       ├── router_prompt.py   # ROUTER_SYSTEM_PROMPT — intent classification instructions
│   │       └── fbr_qa_prompt.py   # FBR_QA_SYSTEM_PROMPT + FOLLOWUP_SYSTEM_PROMPT
│   │
│   ├── tax_extractor/
│   │   ├── config.py              # ExtractorSettings (TAX_EXTRACTOR_ prefix)
│   │   ├── extractor.py           # extract_tax_data(message, history, image_context) → ExtractionResponse
│   │   ├── router.py              # POST /api/v1/extract (debug endpoint, no auth)
│   │   └── models/
│   │       ├── taxpayer.py        # TaxpayerData (master extraction schema)
│   │       ├── income.py          # SalaryIncome, BusinessIncome, RentalIncome, CapitalGains, etc.
│   │       ├── deductions.py      # Deductions model (zakat, donations, pension, etc.)
│   │       ├── withholding.py     # WithholdingTaxes model
│   │       ├── clarification.py   # ClarificationQuestion model
│   │       └── response.py        # ExtractionResponse (complete | needs_clarification)
│   │
│   ├── rule_retriever/
│   │   ├── config.py              # RetrieverSettings (RULE_RETRIEVER_ prefix)
│   │   ├── models.py              # TreeNode, RetrievedSection, RetrievalResult
│   │   ├── retriever.py           # retrieve_relevant_sections() — two-pass tree-reasoning retrieval
│   │   ├── router.py              # POST /api/v1/retrieve (debug endpoint, no auth)
│   │   ├── tree_index.py          # TreeIndex class — loads fbr_combined_structure.json as a singleton
│   │   ├── content_fetcher.py     # ContentFetcher class — loads fbr_combined.md as a singleton; line-range fetch
│   │   ├── query_builder.py       # build_retrieval_query() — converts TaxpayerData to NL query string
│   │   └── prompts/
│   │       └── tree_reasoning.py  # TREE_REASONING_PROMPT + CROSS_REF_PROMPT for the retrieval LLM
│   │
│   ├── tax_interpreter/
│   │   ├── config.py              # TaxInterpreterConfig (TAX_INTERPRETER_ prefix)
│   │   ├── interpreter.py         # interpret_tax_situation() — LLM legal classification
│   │   ├── models.py              # TaxComputationPlan, IncomeClassification, TaxRegime, etc.
│   │   ├── router.py              # POST /api/v1/interpret/ (debug endpoint, no auth)
│   │   └── prompts/
│   │       └── system_prompt.py   # Detailed LLM system prompt instructing legal classification decisions
│   │
│   ├── tax_calculator/
│   │   ├── calculator.py          # calculate_tax(plan) — deterministic 10-step arithmetic
│   │   ├── models.py              # TaxCalculationResult, IncomeHeadBreakdown, DeductionApplied, etc.
│   │   └── router.py              # POST /api/v1/calculate/ (debug endpoint, no auth)
│   │
│   ├── tax_rules/
│   │   ├── config.py              # TaxRulesConfig (TAX_RULES_ prefix; default tax year)
│   │   ├── models.py              # TaxSlab, TaxTable, FlatRate, WithholdingRate, TaxYearRates
│   │   ├── lookup.py              # compute_slab_tax, lookup_capital_gains_rate, compute_minimum_tax, lookup_withholding_rate
│   │   ├── __main__.py            # CLI entry point for tax_rules package
│   │   └── rates/
│   │       ├── __init__.py        # RATE_REGISTRY dict + get_rates(tax_year) dispatcher
│   │       └── tax_year_2025_2026.py  # Complete rate tables for TY 2025-26 (salary slabs, business slabs, capital gains, withholding, super tax)
│   │
│   ├── image_extractor/
│   │   ├── config.py              # ImageExtractorSettings (IMAGE_EXTRACTOR_ prefix)
│   │   ├── extractor.py           # extract_from_image(base64, media_type) → ImageExtractionResult
│   │   ├── models.py              # ImageExtractionResult(success, raw_text, error, model_used)
│   │   ├── prompts.py             # IMAGE_EXTRACTION_PROMPT for vision LLM
│   │   └── router.py              # POST /api/v1/image-extractor/extract (JWT required, multipart)
│   │
│   └── tests/
│       ├── test_e2e_pipeline.py           # Full end-to-end pipeline test (requires running server)
│       ├── test_extractor_to_retriever.py # Integration test: extraction → retrieval
│       ├── test_retriever_to_interpreter.py # Integration test: retrieval → interpretation
│       └── test_interpreter_to_calculator.py # Unit test: interpretation → calculation with slab math verification
│
├── frontend/
│   ├── index.html                 # No-build HTML entry point; loads React 18 UMD + Babel + all JSX files
│   ├── app.css                    # Complete design system: CSS custom properties, all component styles
│   └── src/
│       ├── data.jsx               # Static mock data: SAMPLE_USER, SUGGESTIONS, HISTORY, CALENDAR, SAMPLE_ANSWER
│       ├── api.jsx                # window.API — all backend API calls; localStorage profile storage
│       ├── icons.jsx              # Icon component — SVG paths for all used icons
│       ├── app.jsx                # App root: state machine (boot/auth/setup/app/reset_password)
│       ├── auth.jsx               # AuthScreen (email/CNIC/Google login + signup) + ResetPasswordScreen
│       ├── setup.jsx              # ProfileSetup wizard (4 steps: Identity, Income, Deductions, Preferences)
│       ├── sidebar.jsx            # Sidebar: session list, navigation, user info, logout
│       ├── workspace.jsx          # Chat workspace: message input, image attachment, conversation history
│       ├── output.jsx             # CanvasView: pipeline trace rendering; PDF generation; copy-to-clipboard
│       ├── trace.jsx              # TraceDrawer: collapsible backend trace panel (reasoning/tools/sources/meta)
│       ├── structured.jsx         # StructuredModal: guided CSV-style form with per-category FBR field schema
│       ├── calendar.jsx           # CalendarModal: Pakistani tax deadlines display
│       ├── profile.jsx            # ProfileModal: editable profile with identity/income/deductions/preferences tabs
│       └── tweaks.jsx             # Tweaks panel: theme, layout, density, trace toggle
│
└── pre_processing_fbr_doc/
    ├── parse_income_tax.py        # Script that parses the original FBR document into structured chapters
    ├── clean_fbr_data.py          # Data cleaning script for parsed FBR content
    ├── build_fbr_markdown.py      # Script that assembles fbr_combined.md from the cleaned chapter files
    ├── fbr_combined.md            # Full Income Tax Ordinance 2001 in Markdown (~23,795 lines); runtime document
    ├── fbr_processed_original/    # Chapter-by-chapter .txt files from the original FBR document
    └── PageIndex-main/
        ├── requirements.txt       # Dependencies for the PageIndex tool
        └── results/
            └── fbr_combined_structure.json  # Hierarchical tree index of fbr_combined.md (node titles, summaries, line numbers)
```

---

## 4. Environment Configuration

All configuration is loaded from a single `.env` file at the project root. Copy `.env.example` to `.env` and fill in the values before running the backend.

### Supabase

| Variable | Controls | Required |
|---|---|---|
| `SUPABASE_URL` | Supabase project API URL | Required |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for direct DB access | Required |

### Auth

| Variable | Controls | Required |
|---|---|---|
| `AUTH_SECRET_KEY` | JWT signing secret (use a long random string) | Required |
| `AUTH_ALGORITHM` | JWT algorithm (default: `HS256`) | Optional |
| `AUTH_ACCESS_TOKEN_EXPIRE_DAYS` | JWT validity period (default: `7`) | Optional |

### Pipeline (BackendSettings, prefix: `PIPELINE_`)

| Variable | Controls | Required |
|---|---|---|
| `PIPELINE_LLM_API_KEY` | Shared API key passed to LiteLLM for router/general/followup nodes | Required |
| `PIPELINE_MAX_CLARIFICATION_TURNS` | Max clarification turns before forcing calculation (default: `5`) | Optional |
| `PIPELINE_ROUTER_LLM_MODEL` | Model for intent classification (default: `groq/llama-3.1-8b-instant`) | Optional |
| `PIPELINE_ROUTER_LLM_TEMPERATURE` | Router model temperature (default: `0.0`) | Optional |
| `PIPELINE_ROUTER_LLM_MAX_TOKENS` | Router output token cap (default: `200`) | Optional |
| `PIPELINE_GENERAL_LLM_MODEL` | Model for general/out-of-scope replies (default: `groq/llama-3.1-8b-instant`) | Optional |
| `PIPELINE_GENERAL_LLM_TEMPERATURE` | General node temperature (default: `0.5`) | Optional |
| `PIPELINE_GENERAL_LLM_MAX_TOKENS` | General node token cap (default: `300`) | Optional |
| `PIPELINE_FOLLOWUP_LLM_MODEL` | Model for post-calculation follow-ups (default: `groq/llama-3.3-70b-versatile`) | Optional |
| `PIPELINE_FOLLOWUP_LLM_TEMPERATURE` | Followup model temperature (default: `0.3`) | Optional |
| `PIPELINE_FOLLOWUP_LLM_MAX_TOKENS` | Followup output token cap (default: `800`) | Optional |

### Tax Extractor (prefix: `TAX_EXTRACTOR_`)

| Variable | Controls | Required |
|---|---|---|
| `TAX_EXTRACTOR_LLM_MODEL` | Model for NL extraction to structured JSON | Required |
| `TAX_EXTRACTOR_LLM_API_KEY` | API key for the extractor model | Required |
| `TAX_EXTRACTOR_LLM_TEMPERATURE` | Extraction temperature (low recommended) | Optional |
| `TAX_EXTRACTOR_LLM_MAX_TOKENS` | Extraction output token cap | Optional |

### Rule Retriever (prefix: `RULE_RETRIEVER_`)

| Variable | Controls | Required |
|---|---|---|
| `RULE_RETRIEVER_LLM_MODEL` | Model for tree reasoning (default: `groq/llama-3.3-70b-versatile`) | Required |
| `RULE_RETRIEVER_LLM_API_KEY` | API key for the retriever model | Required |
| `RULE_RETRIEVER_LLM_TEMPERATURE` | Retrieval temperature (default: `0.1`) | Optional |
| `RULE_RETRIEVER_TREE_INDEX_PATH` | Path to `fbr_combined_structure.json` | Optional |
| `RULE_RETRIEVER_MARKDOWN_PATH` | Path to `fbr_combined.md` | Optional |
| `RULE_RETRIEVER_MAX_NODES` | Max nodes to retrieve per query (default: `7`) | Optional |
| `RULE_RETRIEVER_MAX_PASSES` | Max retrieval passes (default: `2`) | Optional |

### Tax Interpreter (prefix: `TAX_INTERPRETER_`)

| Variable | Controls | Required |
|---|---|---|
| `TAX_INTERPRETER_LLM_MODEL` | Model for legal classification (default: `groq/llama-3.3-70b-versatile`) | Required |
| `TAX_INTERPRETER_LLM_API_KEY` | API key for the interpreter model | Required |
| `TAX_INTERPRETER_LLM_TEMPERATURE` | Interpreter temperature (default: `0.1`) | Optional |
| `TAX_INTERPRETER_LLM_MAX_TOKENS` | Interpreter output token cap (default: `4000`) | Optional |
| `TAX_INTERPRETER_DEFAULT_TAX_YEAR` | Default tax year if not extracted (default: `2025-2026`) | Optional |
| `TAX_INTERPRETER_MAX_SECTION_CHARS` | Max chars per retrieved section in prompt (default: `1800`) | Optional |

### Image Extractor (prefix: `IMAGE_EXTRACTOR_`)

| Variable | Controls | Required |
|---|---|---|
| `IMAGE_EXTRACTOR_LLM_MODEL` | Vision model for document image OCR | Required |
| `IMAGE_EXTRACTOR_LLM_API_KEY` | API key for the vision model | Required |
| `IMAGE_EXTRACTOR_LLM_TEMPERATURE` | Vision model temperature | Optional |
| `IMAGE_EXTRACTOR_LLM_MAX_TOKENS` | Vision model output token cap | Optional |

### SMTP (no prefix — raw variable names)

| Variable | Controls | Required |
|---|---|---|
| `SMTP_HOST` | SMTP server hostname (default: `smtp.gmail.com`) | Required for password reset |
| `SMTP_PORT` | SMTP port (default: `587`) | Optional |
| `SMTP_USERNAME` | SMTP auth username | Required for password reset |
| `SMTP_PASSWORD` | SMTP auth password / app password | Required for password reset |
| `SMTP_FROM_EMAIL` | Sender email address | Required for password reset |
| `FRONTEND_BASE_URL` | Frontend URL for password reset links (default: `http://localhost:3000`) | Required |

### Google OAuth (prefix: `GOOGLE_`)

| Variable | Controls | Required |
|---|---|---|
| `GOOGLE_CLIENT_ID` | Google OAuth 2.0 client ID | Required for Google login |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 2.0 client secret | Required for Google login |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL (default: `http://localhost:8000/api/v1/auth/google/callback`) | Optional |
| `GOOGLE_FRONTEND_REDIRECT` | Frontend URL to redirect after OAuth (default: `http://localhost:3000`) | Optional |

### CORS (prefix: `CORS_`)

| Variable | Controls | Required |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins (default: `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173`) | Optional |

---

## 5. Database Schema

Tax Sathi uses four tables in a Supabase (PostgreSQL) database. The schema is defined in `supabase_schema.sql`.

### users

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated via `uuid_generate_v4()` |
| `email` | TEXT UNIQUE | User's email address |
| `password_hash` | TEXT | bcrypt hash; empty string for Google OAuth users |
| `full_name` | TEXT | Optional display name |
| `phone` | TEXT | Optional phone number |
| `cnic` | TEXT UNIQUE | Pakistani national ID (XXXXX-XXXXXXX-X format); nullable |
| `ntn` | TEXT | National Tax Number; nullable |
| `city` | TEXT | Optional city |
| `province` | TEXT | Optional province |
| `tax_year` | TEXT | Preferred active tax year |
| `auth_provider` | TEXT | `email` or `google`; defaults to `email` |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |

### sessions

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `user_id` | UUID (FK → users.id) | CASCADE DELETE |
| `title` | TEXT | Session title (default: `New Chat`) |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |
| `updated_at` | TIMESTAMPTZ | Updated by application on message activity |

### messages

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `session_id` | UUID (FK → sessions.id) | CASCADE DELETE |
| `role` | TEXT | CHECK constraint: `user` or `assistant` |
| `content` | TEXT | Plain text message content |
| `canvas_data` | JSONB | Full CanvasData blob for assistant messages (includes all traces) |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |

### password_reset_tokens

| Column | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | Auto-generated |
| `user_id` | UUID (FK → users.id) | CASCADE DELETE |
| `token` | TEXT UNIQUE | `secrets.token_urlsafe(32)` |
| `expires_at` | TIMESTAMPTZ | 30 minutes from creation by default |
| `used` | BOOLEAN | Set to `true` after successful reset |
| `created_at` | TIMESTAMPTZ | Auto-set on insert |

An index `idx_reset_tokens_token` is created on `password_reset_tokens(token)` for fast lookup.

### Data Ownership

All data is strictly user-scoped. Sessions reference a `user_id` with CASCADE DELETE, so deleting a user deletes all their sessions. Messages reference a `session_id` with CASCADE DELETE, so deleting a session removes all its messages. The sessions router enforces ownership checks at the application layer: every session read, update, or delete verifies that `session.user_id == current_user.user_id` and raises HTTP 403 otherwise. The `canvas_data` JSONB column stores the full pipeline trace (extraction, retrieval, interpretation, calculation) alongside each assistant message so that historical sessions render identically to the original response.

---

## 6. Backend Architecture

### 6.1 Application Entry Point

`backend/main.py` creates the FastAPI application and mounts all module routers. CORS middleware is applied using the comma-separated origins from `CORSSettings`. The routers mounted are:

- Auth router (`/api/v1/auth`)
- Profile router (`/api/v1/profile`)
- Sessions router (`/api/v1/sessions`)
- Pipeline router (`/api/v1/pipeline`)
- Tax Extractor router (`/api/v1/extract`)
- Rule Retriever router (`/api/v1/retrieve`)
- Tax Interpreter router (`/api/v1/interpret`)
- Tax Calculator router (`/api/v1/calculate`)
- Image Extractor router (`/api/v1/image-extractor`)

### 6.2 Auth Module

**Path:** `backend/auth/`

The auth module handles all identity operations. It uses bcrypt for password hashing (via the `bcrypt` library) and HS256 JWT tokens issued by `python-jose`. Tokens are valid for a configurable number of days (default 7).

**Models:**
- `SignupRequest` — email, password, full_name, optional CNIC
- `LoginRequest` — email + password
- `CNICLoginRequest` — CNIC (validated against `^\d{5}-\d{7}-\d$` regex) + password
- `AuthResponse` — user_id, email, full_name, JWT token
- `ForgotPasswordRequest` — email
- `ResetPasswordRequest` — token + new_password (min 8 chars)

**Middleware:** `get_current_user()` in `utils.py` is a FastAPI dependency that extracts and validates the Bearer token from the `Authorization` header. It is used by all protected endpoints.

**Email:** `email.py` sends HTML password reset emails via `smtplib` with STARTTLS. The `_send()` function is executed in a thread pool executor to avoid blocking the async event loop.

### 6.3 Profile Module

**Path:** `backend/profile/`

Two endpoints provide read and write access to the extended user profile fields stored in the `users` table. Both are JWT-protected. The PUT endpoint uses `model_dump(exclude_none=True)` so that only supplied fields are updated, leaving other fields unchanged.

**ProfileUpdateRequest fields:** full_name, phone, cnic, ntn, city, province, tax_year (all optional).

### 6.4 Sessions Module

**Path:** `backend/sessions/`

Full CRUD for chat sessions and read access to messages within a session. All endpoints are JWT-protected. The `list_sessions` endpoint fetches sessions sorted by `updated_at DESC` and makes one additional Supabase query per session to retrieve the last message preview (first 100 characters of the most recent message content).

| Endpoint | Action |
|---|---|
| GET `/sessions/` | List all sessions for authenticated user, with last message preview |
| POST `/sessions/` | Create new session with optional title |
| GET `/sessions/{id}` | Get session detail with all messages and their `canvas_data` |
| DELETE `/sessions/{id}` | Delete session (and all messages by CASCADE) |
| PUT `/sessions/{id}` | Update session title |

### 6.5 Pipeline Module

**Path:** `backend/pipeline/`

The pipeline module is the most complex part of the system. It orchestrates a LangGraph state machine that routes each user message through different processing paths depending on intent.

#### 6.5.1 Graph Topology (ASCII Diagram)

```
                         ┌────────────────┐
                         │    [ENTRY]     │
                         │     router     │
                         └───────┬────────┘
              intent="tax_calculation"  intent="fbr_policy_qa"
              ┌────────────────────┘         └──────────────────┐
              ▼                                                   ▼
      ┌──────────────┐                                   ┌──────────────┐
      │  extraction  │                                   │   fbr_qa     │
      └──────┬───────┘                                   └──────┬───────┘
             │                                                   │
    status="needs_clarification"                                 │
      ┌──────┘  status="complete"                               │
      ▼                   ▼                                      │
 ┌──────────┐    ┌──────────────┐                               │
 │ response │    │  retrieval   │                               │
 └──────────┘    └──────┬───────┘                               │
                         ▼                                       │
                 ┌───────────────┐                               │
                 │ interpretation│                               │
                 └──────┬────────┘                               │
                         ▼                                       │
                 ┌───────────────┐                               │
                 │  calculation  │                               │
                 └──────┬────────┘                               │
                         └──────────────────────────────┐        │
                                                         ▼        ▼
       intent="follow_up" ──────────────────► ┌──────────────────────┐
       intent="general_greeting" ──────────► │       general        │
       intent="out_of_scope" ─────────────► │  (general_node)      │
                                             └──────┬───────────────┘
                                                    │
                              ┌─────────────────────┘
                              ▼
                        ┌──────────┐
                        │ response │ ──► [END]
                        └──────────┘

followup node routing:
  - extraction_status="needs_clarification" → loops back to extraction
  - calculation_result present → generates LLM answer → response
  - neither → fallback message → response
```

#### 6.5.2 TaxSathiState Fields

`TaxSathiState` is a `TypedDict` that flows through the graph. Each node reads from and writes to this shared state.

| Field | Type | Written by | Purpose |
|---|---|---|---|
| `user_message` | str | pipeline router | The user's current message text |
| `session_id` | str | pipeline router | Supabase session ID for message persistence |
| `turn_number` | int | pipeline router | Incrementing turn counter for the session |
| `conversation_history` | list[dict] | pipeline router | Prior messages from Supabase (role + content) |
| `image_context` | str | pipeline router | Extracted text from uploaded image (optional) |
| `intent` | str | router_node | Classified intent: `tax_calculation`, `fbr_policy_qa`, `follow_up`, `general_greeting`, `out_of_scope` |
| `router_reasoning` | str | router_node | One-sentence explanation of intent classification |
| `extraction_status` | str | extraction_node | `complete`, `needs_clarification`, or `not_started` |
| `taxpayer_data` | dict | extraction_node | Serialised `TaxpayerData` Pydantic model |
| `clarification_questions` | list | extraction_node | List of `ClarificationQuestion` dicts |
| `clarification_turn` | int | followup_node | Incremented on each clarification loop |
| `extraction_trace` | dict | extraction_node | ExtractionTrace for frontend display |
| `retrieval_result` | dict | retrieval_node | Serialised `RetrievalResult` |
| `retrieval_trace` | dict | retrieval_node | RetrievalTrace for frontend display |
| `interpretation_result` | dict | interpretation_node | Serialised `TaxComputationPlan` |
| `interpretation_trace` | dict | interpretation_node | InterpretationTrace for frontend display |
| `calculation_result` | dict | calculation_node | Serialised `TaxCalculationResult` |
| `calculation_trace` | dict | calculation_node | CalculationTrace for frontend display |
| `assistant_message` | str | calculation/fbr_qa/followup/general nodes | Final text response for the user |
| `response_stage` | str | various nodes | `clarification_needed`, `extraction_complete`, `qa_response`, `general_response` |
| `current_node` | str | every node | Debug field: name of the most recently executed node |
| `final_response` | dict | response_node | Serialised `PipelineResponse` |
| `retrieved_sections_for_qa` | list | fbr_qa_node | Section traces for Q&A responses |
| `qa_answer` | str | fbr_qa/followup nodes | Answer text for Q&A and follow-up responses |

#### 6.5.3 Node Descriptions

**router_node** — Calls the router LLM (cheapest model, `groq/llama-3.1-8b-instant`) with `ROUTER_SYSTEM_PROMPT` which defines five intents. The prompt is context-aware: if `extraction_status == "needs_clarification"` the router is told the user may be answering a clarification question and should use `follow_up`; if `calculation_result` exists and the message looks like a follow-up question the same applies. Falls back to `tax_calculation` on LLM error.

**extraction_node** — Calls `extract_tax_data()` from the tax extractor module, passing `user_message`, `conversation_history`, and optional `image_context`. Updates `extraction_status`, `taxpayer_data`, `clarification_questions`, and `extraction_trace` in state. Serialises `TaxpayerData` via `model_dump()` so it survives state serialisation.

**retrieval_node** — Deserialises `taxpayer_data` from state into a `TaxpayerData` object, calls `retrieve_relevant_sections()`, and serialises the result back. Also runs `_infer_relevance()` to annotate each retrieved section with a plain-English explanation of why it is relevant to this taxpayer's specific figures.

**interpretation_node** — Deserialises both `taxpayer_data` and `retrieval_result`, calls `interpret_tax_situation()`, and serialises the `TaxComputationPlan` result. Builds an `InterpretationTrace` via `build_interpretation_trace()`.

**calculation_node** — Deserialises `TaxComputationPlan` from `interpretation_result`, calls `calculate_tax()`, builds a `CalculationTrace`, and sets `assistant_message` to the human-readable `summary_text` from the calculation result.

**fbr_qa_node** — Performs two LLM calls: (1) tree-index reasoning to select relevant nodes for the user's question, (2) answer generation using retrieved section content. Uses the same `TREE_REASONING_PROMPT` as the retriever but passes the user's natural language question directly as the query. Falls back to nodes `0005` and `0066` on LLM error.

**followup_node** — Handles two distinct cases: if `extraction_status == "needs_clarification"`, increments `clarification_turn` and returns (the conditional edge routes back to extraction for re-extraction with the user's answer included in the conversation history); if `calculation_result` exists, calls `FOLLOWUP_SYSTEM_PROMPT` with the calculation summary and top 3 retrieved sections as context to generate a contextual answer. Falls back to a generic message if neither condition is met.

**general_node** — Calls the general LLM with a compact system prompt that covers both greetings and out-of-scope messages. Responds in the language the user used (English or Urdu).

**response_node** — Assembles the final `PipelineResponse` based on `response_stage`. For `clarification_needed` stages, includes only extraction trace and clarification questions. For `extraction_complete` stages, includes all four traces (extraction, retrieval, interpretation, calculation). For `qa_response`, includes retrieval trace. For `general_response`, includes only processing steps. Builds `ProcessingStep` objects that summarise each pipeline stage with status and human-readable summaries.

#### 6.5.4 Pipeline Models

**PipelineRequest** — session_id (str), message (str), conversation_history (list[dict]), image_context (str, optional).

**PipelineResponse** — stage (str), assistant_message (str), questions (list[ClarificationQuestion], optional), canvas (CanvasData), taxpayer_data (TaxpayerData, optional), retrieved_sections (list[RetrievedSection], optional), session_id (str), turn_number (int).

**CanvasData** — steps (list[ProcessingStep]), extraction (ExtractionTrace, optional), retrieval (RetrievalTrace, optional), interpretation (InterpretationTrace, optional), calculation (CalculationTrace, optional), raw_taxpayer_data (dict, optional).

**ExtractionTrace** — status, extracted_fields (dict), missing_fields (list), assumptions (list), confidence (float 0–1), confidence_label (High/Medium/Low).

**RetrievalTrace** — status, query_summary, selected_sections (list[SectionTrace]), passes_used, reasoning, error_message.

**InterpretationTrace** — status, income_classifications (list), exemptions (list), deductions (list), tax_credits (list), withholding (list), minimum_tax_applicable, super_tax_applicable, overall_reasoning, caveats, referenced_sections.

**CalculationTrace** — status, all numeric summary fields (gross income, taxable income, deductions, tax on normal/separate income, gross liability, credits, minimum tax, super tax, total liability, adjustable withholding, final withholding, net payable, refund, effective rate), plus income_breakdowns, deductions_applied, tax_credits_applied, withholding_adjustments, computation_notes, caveats, summary_text.

### 6.6 Tax Extractor

**Path:** `backend/tax_extractor/`

The tax extractor converts unstructured natural language user input into a strongly-typed `TaxpayerData` Pydantic model (or signals that clarification questions must be asked first).

**Entry function:** `extract_tax_data(user_message, conversation_history, image_context)` returns `ExtractionResponse`.

**TaxpayerData schema** — a hierarchical model with:
- Identity: `tax_year`, `taxpayer_type` (individual/aop/company), `residency_status` (resident/non_resident), `filer_status` (filer/non_filer/late_filer), `age_above_60`, `disability_status`, `confidence_score`, `assumptions_made`
- Income sub-models (all optional):
  - `SalaryIncome` — basic_salary_annual, allowances, bonuses, employer_pension_contribution, tax_already_deducted
  - `BusinessIncome` — gross_revenue, total_expenses, net_profit, business_type (sole_proprietor/partnership_share), is_sme
  - `RentalIncome` — gross_rent_annual, property_type (residential/commercial), allowable_deductions
  - `CapitalGains` — gain_from_securities + holding period, gain_from_property + holding period
  - `FreelanceIncome` — annual_income, income_currency, platform, is_it_export, has_pseb_registration
  - `OtherIncome` — bank_profit, dividends, prize_winnings
  - `AgriculturalIncome` — amount
- `Deductions` — zakat_paid, donations, pension_fund_contribution, education_expenses, health_insurance_premium, investment_in_shares, mortgage_interest
- `WithholdingTaxes` — tax_on_salary, tax_on_bank_profit, tax_on_dividends, tax_on_property, tax_on_vehicle, advance_tax_paid, other_withholding

**ExtractionResponse** — status (`complete` or `needs_clarification`), extracted_data (`TaxpayerData`, when complete), questions (list of `ClarificationQuestion`, when clarification needed), partial_data (partially populated `TaxpayerData` preserved during clarification turns), message (conversational text).

**ClarificationQuestion** — field_name, question_text, options (list or None), input_type (choice/number/text), priority (required/optional).

The system prompt for the extractor (in `tax_extractor/prompts/system_prompt.py`) instructs the LLM to extract all available information into `TaxpayerData`, populate `partial_data` with what was found, and generate targeted clarification questions for fields that are `required` priority and still missing.

### 6.7 Rule Retriever

**Path:** `backend/rule_retriever/`

The rule retriever selects the minimum set of FBR document sections required to answer a specific taxpayer's tax computation. It operates on two artefacts loaded as singletons at startup:

1. **`fbr_combined_structure.json`** — a hierarchical tree index where each node has a `node_id`, `title`, `line_num`, `summary`, and nested `nodes` children. This represents the organisational structure of the entire Income Tax Ordinance 2001.

2. **`fbr_combined.md`** — the complete Income Tax Ordinance 2001 in Markdown format (approximately 23,795 lines). Content is retrieved by line range.

**TreeIndex** (`tree_index.py`) — loads the JSON tree, builds three in-memory indexes:
- `node_map` — `node_id` → `TreeNode`
- `parent_map` — `node_id` → parent `TreeNode`
- `line_ranges` — `node_id` → `(start_line, end_line)` computed from sibling ordering

The `get_tree_for_prompt()` method renders the entire tree as an indented text string including node IDs, titles, and truncated summaries for inclusion in the LLM prompt.

**ContentFetcher** (`content_fetcher.py`) — loads `fbr_combined.md` entirely into memory as a list of lines. The `fetch(start_line, end_line)` method slices the list (1-indexed, inclusive) and returns the content as a string.

**Retrieval algorithm** (`retriever.py`):

Pass 1 — `build_retrieval_query()` converts `TaxpayerData` into a detailed natural language query string listing the taxpayer's profile, income sources with amounts, deductions, and withholding taxes. This query plus the full tree structure is sent to the retrieval LLM with `TREE_REASONING_PROMPT`, which instructs the LLM to return a JSON array of `node_ids` and a reasoning string. The LLM is instructed to prefer leaf nodes (most specific), always include the exemptions section, and include the applicable rate schedule.

Pass 2 (optional, if `max_passes >= 2`) — scans the content of all Pass 1 sections for cross-references to other section numbers not yet fetched. For each missing cross-reference, `CROSS_REF_PROMPT` asks the LLM to identify which tree node contains that section. Up to 3 additional nodes are added.

On LLM error in either pass, a heuristic fallback uses `_INCOME_FALLBACK` — a hardcoded dict mapping each income field to the relevant node IDs (e.g., `salary_income` → `["0005", "0066"]`).

**`build_retrieval_query()`** (`query_builder.py`) — produces a human-readable summary of the taxpayer's situation with special flags like "IMPORTANT: higher withholding rates apply" for non-filers, "SENIOR CITIZEN — 50% tax reduction may apply" for age_above_60, and "IT EXPORT INCOME — check IT export exemption provisions" for qualifying freelancers.

### 6.8 Tax Interpreter

**Path:** `backend/tax_interpreter/`

The tax interpreter is the LLM reasoning step that takes structured `TaxpayerData` and the retrieved FBR sections and makes all legal classification decisions needed to compute tax. It produces a `TaxComputationPlan` — a structured object that the deterministic calculator then executes.

**Entry function:** `interpret_tax_situation(taxpayer_data, retrieval_result, tax_year)` → `TaxComputationPlan`.

The interpreter formats the taxpayer data and retrieved sections into a user message, calls the LLM with JSON mode enabled (falls back to plain text mode on JSON mode failure), then extracts the JSON object from the response using a multi-strategy parser (`_extract_json()`). The raw JSON is coerced via `_coerce_plan_dict()` to fix common LLM output issues (floats where ints are expected, None values, string number representations).

**TaxComputationPlan fields:**
- `tax_year`, `filer_status`, `residency_status`, `taxpayer_category`
- `income_classifications` — list of `IncomeClassification` (source description, head enum, section, annual amount, tax regime, schedule, reasoning)
- `exemptions` — list of `ExemptionDecision` (clause, description, applies bool, exempt amount, reasoning)
- `deductions` — list of `DeductionDecision` (section, type, claimed amount, allowed bool, allowed amount, cap rule, reasoning)
- `tax_credits` — list of `TaxCreditDecision` (section, type, eligible bool, credit amount, reasoning)
- `withholding_classifications` — list of `WithholdingClassification` (source, section, amount, regime, reasoning)
- `minimum_tax_applicable` (bool), `minimum_tax_turnover` (int, optional)
- `super_tax_applicable` (bool)
- `overall_reasoning` (str), `referenced_sections` (list[str]), `caveats` (list[str])

**TaxRegime enum:** NORMAL (slab-based), FINAL (withholding IS the final tax), SEPARATE (flat rate, taxed independently), EXEMPT.

**IncomeHead enum:** SALARY, BUSINESS, PROPERTY, CAPITAL_GAINS, OTHER_SOURCES.

The system prompt (in `prompts/system_prompt.py`) is a detailed legal expert prompt that instructs the LLM to classify each income source into the correct head and tax regime, evaluate which exemptions apply, assess which deductions are allowed and at what cap, check tax credit eligibility, and classify each withholding tax as final or adjustable. It instructs the LLM to output ONLY a JSON object matching the `TaxComputationPlan` schema.

### 6.9 Tax Calculator

**Path:** `backend/tax_calculator/`

The tax calculator is a zero-LLM, deterministic Python module that executes the legal decisions made by the interpreter against the hardcoded rate tables. It follows a strict 10-step sequence.

**Entry function:** `calculate_tax(plan: TaxComputationPlan)` → `TaxCalculationResult`.

**10-step computation sequence:**

1. Compute per-income-head tax — for each `IncomeClassification`, dispatch to the appropriate computation based on `TaxRegime`: EXEMPT → 0 tax; FINAL → 0 tax (withholding is final, informational only); SEPARATE → flat rate from interpreter reasoning text; NORMAL → `compute_slab_tax()` using `salary_slabs` or `business_individual_slabs` based on income head.
2. Apply deductions — for each allowed `DeductionDecision`, apply percentage-based caps from `cap_rule` (regex extracts the percentage) and accumulate `total_deductions`.
3. Recompute normal income tax after deductions — sum all NORMAL income, subtract deductions, re-run slab lookup on combined net amount. This produces the correct marginal rate by pooling all normal income.
4. Gross tax liability — normal tax + separate tax.
5. Apply tax credits — subtract eligible credits from gross liability; floor at 0.
6. Section 113 minimum tax — if `minimum_tax_applicable` and `minimum_tax_turnover` is provided, compute `turnover × rate_percent / 100` and compare with normal tax; higher value is used.
7. Super tax (Section 4C) — if `super_tax_applicable` and `super_tax_slabs` present in rate table, run slab computation on total taxable income.
8. Final liability — max(tax_after_credits, minimum_tax) + super tax.
9. Withholding adjustments — FINAL regime withholding is informational; NORMAL regime withholding is adjustable (subtracted from liability).
10. Net result — `net_payable = max(0, total_liability - adjustable_withholding)`; refund if adjustable_withholding > total_liability.

**Capital gains tax** — handled specially: holding period is inferred from the interpreter's `reasoning` and `applicable_schedule` text using regex patterns; `lookup_capital_gains_rate()` maps the holding period to the applicable FlatRate entry for securities or property (plots/constructed/flats).

**Schedule → rate table mapping** — `_get_table_for_head_and_schedule()` maps income head + schedule string to the correct `TaxTable`. Salary head always uses `salary_slabs`; business head uses `business_individual_slabs`; the fallback analyses the schedule string for keywords like "Division II", "AOP", or "business".

All computation steps are appended to `computation_notes` in sequence, providing a full step-by-step audit trail.

### 6.10 Tax Rules

**Path:** `backend/tax_rules/`

The tax rules module is a static data registry of FBR rate tables. All values are hardcoded from the First Schedule of the Income Tax Ordinance 2001, Finance Act 2025.

**TaxYearRates** (`models.py`) — the master container for one tax year:
- `salary_slabs` — Division I (1A/2): 6 brackets from 0–600k (0%) to 4.1M+ (35%), hardcoded from fbr_combined.md lines 19324–19343
- `business_individual_slabs` — Division I (1): 6 brackets from 0–600k (0%) to 5.6M+ (45%), from lines 19237–19256
- `business_aop_slabs` — same as individual from Finance Act 2024 onwards
- `business_company_rate` — 29% (general), `business_company_rate_small` — 20%, `business_company_rate_banking` — 44%
- `capital_gains_securities` — 8 FlatRate entries by holding period (0–6+ years, filer rates from 15% down to 0% for 6+ years; non-filer rate always 15%)
- `capital_gains_property_plots` — 7 FlatRate entries (15% down to 0% for 6+ years)
- `capital_gains_property_constructed` — 5 FlatRate entries (15% down to 0% for 4+ years)
- `capital_gains_property_flats` — 3 FlatRate entries (15% down to 0% for 2+ years)
- `dividend_rate_general` — 15%, `dividend_rate_ipp` — 7.5%
- `profit_on_debt_rate_bank` — 20%, `profit_on_debt_rate_other` — 15%
- `withholding_rates` — list of `WithholdingRate` for key sections (149, 151, 153, 155, 231A, 236, 5, 7B) with filer and non-filer rates and `is_final` flag
- `minimum_tax_rate_general` — 1.25%, `minimum_tax_rate_sui_gas_airlines_poultry` — 0.75%, `minimum_tax_rate_distributors_pharma` — 0.25%
- `super_tax_slabs` — Division IIB: 8 brackets from 150M (1%) to 500M+ (10%)

**`RATE_REGISTRY`** — a dict mapping tax year strings to `TaxYearRates` objects. Currently only `"2025-2026"` is registered. `get_rates(tax_year)` raises `ValueError` if the year is not available; the calculator falls back to 2025-2026 with a warning.

**Lookup functions** (`lookup.py`):
- `compute_slab_tax(amount, table)` — finds the applicable slab and returns fixed_tax + rate × excess; also returns effective rate
- `lookup_capital_gains_rate(gain_type, holding_years, filer_status, rates, sub_type)` — maps holding period and filer status to the correct flat rate percentage
- `compute_minimum_tax(turnover, rates, category)` — multiplies turnover by the category-appropriate minimum tax rate
- `lookup_withholding_rate(section, filer_status, rates)` — looks up a specific section's rate and `is_final` flag

### 6.11 Image Extractor

**Path:** `backend/image_extractor/`

The image extractor allows users to upload document images (salary slips, bank statements, tax certificates) to the chat and have their content extracted as text context for the pipeline.

**Entry function:** `extract_from_image(image_base64, media_type)` → `ImageExtractionResult`.

The extractor calls a vision-capable LLM (configured via `IMAGE_EXTRACTOR_LLM_MODEL`) with `IMAGE_EXTRACTION_PROMPT` and the base64-encoded image. The prompt instructs the model to extract all financial data, labels, numbers, names, and amounts from the image in structured text format.

**`ImageExtractionResult`** — success (bool), raw_text (str, the extracted content), error (str, optional), model_used (str).

**Router** (`router.py`) — POST `/api/v1/image-extractor/extract` accepts `multipart/form-data` with a `file` field. Requires a valid JWT. Reads the uploaded file bytes, base64-encodes them, detects the media type from the content type header, and calls `extract_from_image()`. Returns `ImageExtractionResult`.

The extracted text (`raw_text`) from the image extractor is passed to the pipeline as `image_context`, which the extraction node passes to `extract_tax_data()` as additional context alongside the user's message.

### 6.12 Debug Standalone Endpoints

Each sub-module exposes a standalone debug endpoint for testing without going through the full pipeline. These endpoints have no authentication requirement.

| Endpoint | Module | Input | Output |
|---|---|---|---|
| POST `/api/v1/extract` | tax_extractor | `{message, conversation_history}` | `ExtractionResponse` |
| POST `/api/v1/retrieve` | rule_retriever | `{taxpayer_data: TaxpayerData}` | `RetrievalResult` |
| POST `/api/v1/interpret/` | tax_interpreter | `{taxpayer_data, retrieval_result, tax_year?}` | `TaxComputationPlan` |
| POST `/api/v1/calculate/` | tax_calculator | `TaxComputationPlan` | `TaxCalculationResult` |
| POST `/api/v1/image-extractor/extract` | image_extractor | multipart file upload (JWT required) | `ImageExtractionResult` |

---

## 7. Pipeline Data Flow

### Happy Path (tax_calculation intent, complete extraction)

1. **Request arrives** — POST `/api/v1/pipeline/chat` with `session_id`, `message`, `conversation_history`, and optional `image_context`.
2. **State initialised** — `_build_initial_state()` in `pipeline/router.py` fetches existing messages from Supabase to populate `conversation_history` (if not provided), sets `turn_number` to 1 + count of existing assistant messages.
3. **Graph executes** — `await tax_sathi_graph.ainvoke(initial_state)`.
4. **router_node** — LLM classifies intent as `tax_calculation`. State: `intent = "tax_calculation"`.
5. **extraction_node** — LLM extracts all income/deduction data from the message. Returns `extraction_status = "complete"`, `taxpayer_data` dict, `extraction_trace`.
6. **Conditional edge** — `route_after_extraction()` checks `extraction_status == "complete"` → routes to `retrieval`.
7. **retrieval_node** — builds query from `TaxpayerData`, calls `retrieve_relevant_sections()`, receives 2–7 retrieved sections from the FBR document. Sets `retrieval_result` and `retrieval_trace`.
8. **interpretation_node** — passes `TaxpayerData` + retrieved sections to the interpreter LLM. LLM makes all legal decisions and returns a `TaxComputationPlan`. Sets `interpretation_result` and `interpretation_trace`.
9. **calculation_node** — executes `calculate_tax(plan)` deterministically in 10 steps. Sets `calculation_result`, `calculation_trace`, and `assistant_message` to the human-readable summary.
10. **response_node** — assembles `PipelineResponse` with `stage = "extraction_complete"`, all four traces in `CanvasData`, and the summary text as `assistant_message`.
11. **Message persistence** — back in `pipeline/router.py`, both the user message and the assistant response (with full `canvas_data` JSONB blob) are saved to Supabase.
12. **Response returned** — the `PipelineResponse` is serialised and returned to the frontend.

### Clarification Path (extraction incomplete)

Steps 1–5 as above, but step 5 returns `extraction_status = "needs_clarification"` with `clarification_questions` and `partial_data`.

The conditional edge `route_after_extraction()` sees `"needs_clarification"` → routes to `response`. The response node builds a canvas with `stage = "clarification_needed"` and includes the `questions` list in the response.

The user answers the clarification question. On the next request, `conversation_history` contains the previous exchange. The router node sees the prior clarification context and classifies intent as `follow_up`. The followup node sees `extraction_status == "needs_clarification"`, increments `clarification_turn`, and returns. The conditional edge `route_after_followup()` routes back to `extraction`. The extraction node now has the user's answer in conversation history and can complete the extraction.

### FBR Policy Q&A Path

Intent classified as `fbr_policy_qa`. Routes to `fbr_qa_node`. Node does two LLM calls: tree-index selection then answer generation. Routes to `response_node` which builds a `qa_response` stage canvas with only the retrieval trace.

### General / Out-of-Scope Path

Intent classified as `general_greeting` or `out_of_scope`. Routes to `general_node`. Node generates a brief polite response. Routes to `response_node` which builds a minimal canvas with just processing steps.

### Follow-Up Path (post-calculation)

Intent classified as `follow_up`, `calculation_result` exists in state. `followup_node` calls the followup LLM with the calculation summary and top 3 retrieved sections as context. Generates a direct answer. Routes to `response_node`.

---

## 8. FBR Document Retrieval System

The FBR document retrieval system is built around a pre-processed, hierarchically indexed copy of the Income Tax Ordinance 2001.

### Document Preparation

The original FBR document was processed using three scripts in `pre_processing_fbr_doc/`:

1. `parse_income_tax.py` — parses the original document into per-chapter text files stored in `fbr_processed_original/`. The directory contains chapters 1–13 with nested parts and divisions.
2. `clean_fbr_data.py` — applies text normalisation and cleaning to the parsed chapter files.
3. `build_fbr_markdown.py` — assembles all cleaned chapter files into the single `fbr_combined.md` file (~23,795 lines).

### Tree Index

`fbr_combined_structure.json` is a hierarchical JSON produced by the **PageIndex** tool (in `pre_processing_fbr_doc/PageIndex-main/`). The PageIndex tool reads `fbr_combined.md` and produces a tree where each node stores:

| Field | Description |
|---|---|
| `node_id` | Zero-padded 4-digit string (e.g., `"0005"`) |
| `title` | Human-readable section title (e.g., `"Part 2 — HEAD OF INCOME: SALARY"`) |
| `line_num` | Line number in `fbr_combined.md` where this section begins |
| `summary` | LLM-generated summary of the section content |
| `prefix_summary` | Alternative short summary for header-level nodes |
| `nodes` | Array of child nodes (recursive) |

The root node `0000` is "Income Tax Ordinance 2001" and contains approximately 80+ child and grandchild nodes covering all chapters, parts, and divisions.

### Runtime Line-Range Computation

The `TreeIndex` class computes line ranges at load time: for each parent node, it iterates its children in order and assigns end line = next sibling's start line − 1 (or parent's end line for the last child). This means fetching a node's content requires no full-text search — it is purely a range slice of the pre-loaded markdown file.

### Two-Pass Retrieval Design

Pass 1 selects the most relevant leaf-level nodes for a given taxpayer's profile by reasoning over the tree structure (not the content). This is efficient because the tree with summaries is much smaller than the full document.

Pass 2 is optional and addresses cross-references: after fetching Pass 1 content, any section numbers mentioned in that content but not yet fetched trigger a second LLM call to identify which tree node covers that section. This handles cases where, for example, a salary withholding section refers to "Section 149" which is defined in a different node.

The system cap is `max_nodes = 7` by default, limiting total prompt size for the interpreter.

---

## 9. Frontend Architecture

### 9.1 No-Build Approach

The frontend uses no build toolchain. `index.html` loads React 18 and ReactDOM from unpkg CDN with subresource integrity hashes, then loads Babel Standalone to transpile JSX at runtime in the browser. All source files are loaded as `<script type="text/babel">` tags in dependency order. This eliminates npm, webpack, and build steps entirely. The trade-off is a slightly slower initial load (Babel transpilation) and no tree-shaking.

Cache-busting is handled by a `?v=7` query parameter on each JSX `src` attribute in `index.html`.

### 9.2 App State Machine

`app.jsx` controls the top-level application state via a `mode` string. The state machine has five modes:

| Mode | Condition | Renders |
|---|---|---|
| `boot` | Initial state while checking auth | Loading spinner |
| `reset_password` | `?reset_token=` query param in URL | `ResetPasswordScreen` |
| `auth` | No valid JWT in localStorage | `AuthScreen` |
| `setup` | JWT valid but `profile_extended` not in localStorage | `ProfileSetup` |
| `app` | JWT valid and profile complete | Full app shell (Sidebar + Workspace + CanvasView) |

On boot, the app reads the JWT from localStorage, verifies it with `GET /api/v1/auth/me`, and transitions accordingly. Google OAuth callback tokens are read from the `?token=` query parameter and stored in localStorage.

### 9.3 Component Reference

| Component | File | Purpose |
|---|---|---|
| `AuthScreen` | `auth.jsx` | Split-screen auth: email/password forms + CNIC form + Google button; tab-switching between login and signup |
| `ResetPasswordScreen` | `auth.jsx` | Full-page reset password form for token-based reset flow |
| `ProfileSetup` | `setup.jsx` | Post-signup 4-step wizard: Identity, Income, Deductions, Preferences; saves to localStorage |
| `Sidebar` | `sidebar.jsx` | Left navigation: session list with previews, navigation buttons (Ask/Calendar/Profile), user info, logout |
| `Workspace` (default export) | `workspace.jsx` | Main chat area: message input with paperclip (image attach), image preview strip, conversation bubble rendering, suggestion chips |
| `CanvasView` | `output.jsx` | Right canvas panel: renders all pipeline traces; PDF generation; copy to clipboard |
| `SectionCard` | `output.jsx` | Collapsible FBR section card showing title, relevance, preview, and expandable full content |
| `TraceDrawer` | `trace.jsx` | Collapsible backend trace sidebar with tabs: Reasoning, Tools, Sources, Meta, Payload |
| `StructuredModal` | `structured.jsx` | Guided form modal with category-specific FBR field schemas; CSV download/upload; transaction rows |
| `CalendarModal` | `calendar.jsx` | FBR deadline calendar modal showing upcoming dates from static `CALENDAR` data |
| `ProfileModal` | `profile.jsx` | Editable profile modal with Identity/Income/Deductions/Preferences tabs; saves via `window.API.saveProfile()` |
| `Tweaks` | `tweaks.jsx` | Debug panel for theme (light/dark), layout (split/stack), backend trace toggle, density |
| `Icon` | `icons.jsx` | SVG icon component; accepts `name` and `size`; supports: arrow, chat, calendar, user, settings, logout, plus, close, copy, download, info, upload, eye, eyeOff, chevL, chevR, x |

### 9.4 API Client

`window.API` in `api.jsx` is the single interface between the frontend and backend. It stores the JWT in `localStorage` under the key `token`.

| Method | HTTP | Endpoint | Description |
|---|---|---|---|
| `signup(email, password, name)` | POST | `/api/v1/auth/signup` | Create account, stores token |
| `login(email, password)` | POST | `/api/v1/auth/login` | Email+password login, stores token |
| `cnicLogin(cnic, password)` | POST | `/api/v1/auth/cnic-login` | CNIC-based login, stores token |
| `getMe()` | GET | `/api/v1/auth/me` | Fetch current user info |
| `googleLogin()` | — | — | Redirects to `/api/v1/auth/google/login` |
| `forgotPassword(email)` | POST | `/api/v1/auth/forgot-password` | Request password reset email |
| `resetPassword(token, newPassword)` | POST | `/api/v1/auth/reset-password` | Submit new password with token |
| `logout()` | — | — | Clears localStorage token |
| `getProfile()` | — | — | Reads profile from localStorage |
| `saveProfile(profile)` | PUT | `/api/v1/profile/` | Saves flat profile fields to backend |
| `getSessions()` | GET | `/api/v1/sessions/` | List all user sessions |
| `createSession(title)` | POST | `/api/v1/sessions/` | Create new session |
| `getSession(id)` | GET | `/api/v1/sessions/{id}` | Get session with all messages |
| `deleteSession(id)` | DELETE | `/api/v1/sessions/{id}` | Delete a session |
| `updateSessionTitle(id, title)` | PUT | `/api/v1/sessions/{id}` | Update session title |
| `sendMessage(sessionId, message, history, imageContext)` | POST | `/api/v1/pipeline/chat` | Send message through the full pipeline |
| `extractImageContext(file)` | POST | `/api/v1/image-extractor/extract` | Upload an image and extract text |
| `loadLocal(key)` | — | — | Read value from localStorage |
| `saveLocal(key, value)` | — | — | Write value to localStorage |

Constants exposed on `window.API`:
- `FBR_CATEGORIES` — array of `{id, label, hint}` objects for all 14 taxpayer categories (salaried, small_business, freelancer, aop, company, non_resident, retailer_t1, retailer_t2, manufacturer, importer_exporter, property_income, agriculturist, pensioner, other)
- `EMPTY_PROFILE` — default profile structure template

### 9.5 Design System

`app.css` defines a comprehensive CSS custom property system:

**Colour tokens (light theme):**

| Variable | Value | Usage |
|---|---|---|
| `--bg` | `#f7f4ee` | Page background (warm off-white) |
| `--bg-raised` | `#fffdf7` | Card and input backgrounds |
| `--bg-sunk` | `#f1ede4` | Sidebar, sunken surfaces |
| `--ink` | `#1a1f1b` | Primary text |
| `--ink-2` | `#3c4a40` | Secondary text |
| `--ink-3` | `#6b776d` | Muted text, labels |
| `--ink-4` | `#9aa59c` | Placeholder, hint text |
| `--forest` | `#2e4a36` | Primary brand colour (buttons, accents) |
| `--forest-2` | `#3a5c44` | Hover state for forest |
| `--forest-tint` | `#e9efe9` | Background tint for active states |
| `--amber` | `#b8833a` | Warning colour (pending, assumptions) |
| `--rose` | `#a04940` | Error colour (failed, required) |
| `--teal` | `#3a6b6a` | Accent |
| `--line` | `#e4dfd3` | Default border colour |
| `--line-strong` | `#cfc8b8` | Stronger border |

A `[data-theme="dark"]` block inverts all tokens to a dark green-tinted palette.

**Typography:**
- `--sans`: "Geist" fallback system sans-serif (DM Sans loaded from Google Fonts)
- `--serif`: "Instrument Serif" fallback Palatino (for headings and brand elements)
- `--mono`: "JetBrains Mono" loaded from Google Fonts (numbers, code, section IDs)

**Component classes defined:** `.auth`, `.auth-brand`, `.auth-form`, `.btn`, `.field`, `.app`, `.sidebar`, `.nav-item`, `.history-item`, `.workspace`, `.output-col`, `.out-section`, `.pipeline-step`, `.section-card`, `.trace-drawer`, `.modal`, `.structured-modal`, `.cal-item`, `.profile-tabs`, `.tweaks-panel`, `.switch`, `.chip`, `.notice`, `.shimmer`, `.streaming-shell`, `.setup-wrap`, `.setup-card`, `.setup-steps`

**Responsive:** The layout uses CSS Grid (`grid-template-columns: 260px 1fr` for the app shell) with `height: 100vh; overflow: hidden`. No responsive breakpoints are currently defined.

### 9.6 Canvas Panel

`CanvasView` in `output.jsx` renders the right-side panel. It displays five numbered sections:

- **01 Processing pipeline** — status icons and summaries for each processing step
- **02 Tax data extracted** — extraction status badge, confidence percentage, extracted field grid, missing fields, assumptions list
- **03 FBR rules retrieved** — retrieval query summary, LLM reasoning quote, collapsible `SectionCard` components for each retrieved section (showing title, relevance, 300-char preview, and expandable full content with line range in monospace)
- **04 Tax rules interpreted** — income classification cards with tax regime colour-coded badges (green=exempt, amber=final, grey=normal/separate), deduction allow/deny indicators, withholding regime badges, overall reasoning blockquote, caveats box
- **05 Tax calculation** — summary box (gross income, taxable income, gross liability, withholding adjusted, net payable/refund in large type), income breakdown table, collapsible deductions & credits panel, collapsible withholding adjustments panel, collapsible step-by-step computation notes

**PDF export** — `buildPDFHtml(canvas)` generates a standalone HTML document styled for print (with `@media print`) and opens it in a new tab where the user can trigger the browser's print dialog.

**Copy to clipboard** — `serializeCanvas(canvas)` generates a plain-text summary of the result, copied via `navigator.clipboard.writeText()` with `execCommand` fallback.

---

## 10. Auth Flows

### 10.1 Email/Password Signup

1. User fills the signup form (full name, email, password, optional NTN).
2. Frontend calls `window.API.signup(email, password, name)` → POST `/api/v1/auth/signup`.
3. Backend checks if email already exists in `users` table. If so, returns HTTP 400.
4. Backend hashes the password with bcrypt and inserts a new `users` row.
5. Backend creates a JWT with `{user_id, email}` payload and 7-day expiry.
6. `AuthResponse` (user_id, email, full_name, token) returned to frontend.
7. Frontend stores token in localStorage, calls `onAuth(res, {isSignup: true})`.
8. App transitions to `setup` mode if `profile_extended` not in localStorage.

### 10.2 Email/Password Login

1. User fills the login form (email, password).
2. Frontend calls `window.API.login(email, password)` → POST `/api/v1/auth/login`.
3. Backend queries `users` by email. If not found or password does not match bcrypt check, returns HTTP 401.
4. Backend issues a JWT and returns `AuthResponse`.
5. Frontend stores token and transitions to `app` mode (or `setup` if profile not set up).

### 10.3 CNIC Login

1. User clicks the "CNIC / NADRA" button which expands a sub-form.
2. Frontend validates the CNIC format with regex `^\d{5}-\d{7}-\d$` before submission.
3. Calls `window.API.cnicLogin(cnic, password)` → POST `/api/v1/auth/cnic-login`.
4. Backend queries `users` by CNIC. Password verified via bcrypt. JWT issued.
5. Frontend checks if `profile_extended` exists in localStorage; if not, routes to `setup`.

### 10.4 Google OAuth

1. User clicks the "Google" button. Frontend redirects browser to `/api/v1/auth/google/login`.
2. Backend builds the Google authorization URL with `client_id`, `redirect_uri`, `scope=openid email profile` and redirects.
3. User authenticates with Google. Google redirects to `/api/v1/auth/google/callback?code=...`.
4. Backend exchanges the code for an access token via `https://oauth2.googleapis.com/token`.
5. Backend fetches user info from `https://www.googleapis.com/oauth2/v3/userinfo`.
6. Backend upserts the user in the `users` table with `auth_provider = "google"` and an empty `password_hash`.
7. Backend issues a JWT and redirects to `{GOOGLE_FRONTEND_REDIRECT}?token={jwt}`. If the user is new, appends `&is_new=1`.
8. Frontend reads `?token=` from the URL, stores in localStorage, and transitions. If `&is_new=1`, routes to `setup`.

### 10.5 Forgot Password

1. User clicks "Forgot?" on the login form. A sub-form appears for email entry.
2. Frontend calls `window.API.forgotPassword(email)` → POST `/api/v1/auth/forgot-password`.
3. Backend always returns a generic message regardless of whether the email exists (anti-enumeration).
4. If the email is registered, backend generates `secrets.token_urlsafe(32)`, inserts a `password_reset_tokens` row with a 30-minute expiry, and sends an HTML email via SMTP with a reset link: `{FRONTEND_BASE_URL}?reset_token={token}`.

### 10.6 Password Reset

1. User clicks the reset link in the email. The frontend reads `?reset_token=` from the URL.
2. App transitions to `reset_password` mode and renders `ResetPasswordScreen`.
3. User enters and confirms a new password (minimum 8 characters).
4. Frontend calls `window.API.resetPassword(token, newPassword)` → POST `/api/v1/auth/reset-password`.
5. Backend looks up the token in `password_reset_tokens` where `used = false`.
6. If not found or expired (checked against current UTC time), returns HTTP 400.
7. Backend hashes the new password, updates `users.password_hash`, and marks the token as `used = true`.
8. Frontend shows a success message and redirects to the login screen after 2 seconds.

---

## 11. All API Endpoints

### Auth (prefix: `/api/v1/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/signup` | None | Create user account |
| POST | `/login` | None | Email/password login |
| POST | `/cnic-login` | None | CNIC/password login |
| GET | `/me` | JWT | Get current user info |
| GET | `/google/login` | None | Redirect to Google OAuth |
| GET | `/google/callback` | None | Google OAuth callback handler |
| POST | `/forgot-password` | None | Request password reset email |
| POST | `/reset-password` | None | Submit new password with reset token |

### Profile (prefix: `/api/v1/profile`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | JWT | Get profile (full_name, email, phone, cnic, ntn, city, province, tax_year, created_at) |
| PUT | `/` | JWT | Update profile fields (partial update; only provided fields are changed) |

### Sessions (prefix: `/api/v1/sessions`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | JWT | List all sessions with last message preview |
| POST | `/` | JWT | Create new session |
| GET | `/{session_id}` | JWT | Get session with all messages and canvas_data |
| DELETE | `/{session_id}` | JWT | Delete session and all its messages |
| PUT | `/{session_id}` | JWT | Update session title |

### Pipeline (prefix: `/api/v1/pipeline`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/chat` | JWT | Send message through the full LangGraph pipeline; persists messages to Supabase |

### Tax Extractor (prefix: `/api/v1/extract`) — Debug

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `` (root) | None | Extract TaxpayerData from a message (standalone debug use) |

### Rule Retriever (prefix: `/api/v1/retrieve`) — Debug

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `` (root) | None | Retrieve relevant FBR sections for a TaxpayerData (standalone debug use) |

### Tax Interpreter (prefix: `/api/v1/interpret`) — Debug

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/` | None | Interpret tax situation given TaxpayerData + RetrievalResult (standalone debug use) |

### Tax Calculator (prefix: `/api/v1/calculate`) — Debug

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/` | None | Calculate tax from a TaxComputationPlan (standalone debug use) |

### Image Extractor (prefix: `/api/v1/image-extractor`)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/extract` | JWT | Upload image file (multipart/form-data), extract financial text via vision LLM |

---

## 12. Key Design Decisions

### Decision 1: LLM for Classification, Deterministic Code for Arithmetic

The most important architectural decision is the separation between the interpreter (LLM) and the calculator (pure Python). The interpreter is given retrieved FBR sections and is asked to make legal classification decisions: which income head applies, which tax regime, whether a deduction is allowed, what the cap rule is, whether this is a final or adjustable withholding. The calculator receives this structured plan and performs arithmetic only.

**Why:** LLMs are unreliable at arithmetic. They can hallucinate numbers, apply wrong rates, miss brackets, or apply rounding incorrectly. By keeping the LLM in the classification role and the Python code in the arithmetic role, the system gets the best of both: nuanced legal reasoning from the LLM and verified, reproducible numbers from deterministic code. The `computation_notes` list provides a step-by-step audit trail that can be inspected or compared against manual calculations.

### Decision 2: Tree-Index Retrieval over Vector Search

The FBR document retrieval uses a hierarchical tree index rather than a vector database or dense retrieval. The LLM reasons over the tree structure (titles and summaries) to select relevant nodes, then fetches the actual content by line range.

**Why:** The Income Tax Ordinance has a well-defined, hierarchical structure (Chapters → Parts → Divisions → Sections). Vector search would treat all sections as flat and might retrieve semantically similar but legally irrelevant sections. Tree-based reasoning respects the document's structure and allows the LLM to say "I need Division VII because this taxpayer has capital gains" rather than retrieving based on embedding similarity to the query text. It also eliminates the operational complexity of maintaining a vector store.

### Decision 3: LangGraph for Pipeline Orchestration

The multi-step pipeline is implemented as a LangGraph state machine rather than a simple sequential function call chain.

**Why:** LangGraph provides explicit conditional routing (the clarification loop that routes back to extraction), state persistence between nodes, and clean separation of each processing step into an independent async function. The graph topology is inspectable and modifiable without touching any individual node's logic. The clarification loop (followup_node → extraction_node → response_node and back) is particularly clean to express as a graph edge.

### Decision 4: No Build Frontend

The frontend loads React 18, ReactDOM, and Babel from CDN and transpiles JSX in the browser at runtime.

**Why:** This project is a research prototype and educational system. A no-build approach eliminates npm dependency management, webpack configuration, and build pipeline setup. Any developer can open `frontend/index.html` in a browser (served from any static file server) and the UI works immediately. The trade-off (slightly slower initial load, no tree-shaking) is acceptable for a tool used in individual or small-group sessions.

### Decision 5: Separate Module Settings with `pydantic-settings`

Each module (tax_extractor, rule_retriever, tax_interpreter, image_extractor, pipeline) has its own `Settings` class with a distinct env var prefix. Settings classes are cached with `@lru_cache`.

**Why:** This allows each module to be configured, tested, and deployed independently. The `RULE_RETRIEVER_LLM_MODEL` can use a strong model while `PIPELINE_ROUTER_LLM_MODEL` uses a cheap model, without any global configuration collision. The `extra="ignore"` config option means that any unrecognised `.env` variables (from other modules' prefixes) are silently ignored, preventing cross-module contamination.

### Decision 6: Canvas Data Persisted as JSONB in messages table

The full `CanvasData` blob (all four traces) is stored as JSONB in the `messages.canvas_data` column alongside each assistant message.

**Why:** This means historical sessions can be loaded and displayed with full fidelity — the extraction trace, retrieved FBR sections, interpretation decisions, and calculation steps are all preserved exactly as they were when the answer was generated. Without this, historical sessions would show only the assistant text with no supporting audit trail. The JSONB approach is simpler than normalising the trace data into separate tables.

### Decision 7: Hardcoded Rate Tables

Tax rate slabs, capital gains rates, withholding rates, minimum tax rates, and super tax slabs are defined as Python constants in `backend/tax_rules/rates/tax_year_2025_2026.py`, not fetched from a database or external source.

**Why:** Tax rates change once a year with the Finance Act. Hardcoding them provides: (a) zero latency for rate lookups during tax calculations, (b) version control over rate changes, (c) the ability to write and run deterministic unit tests against specific rate tables (as demonstrated in `test_interpreter_to_calculator.py`), and (d) no dependency on an external rate data source that could be unavailable or incorrect. Adding a new tax year requires creating one new file and adding it to `RATE_REGISTRY`.

---

## 13. Known Gaps and Future Work

### Backend

- **`backend/tax_rules/rates/__init__.py: RATE_REGISTRY`** — Only `"2025-2026"` is implemented. Adding tax years 2023-2024 and 2024-2025 would allow calculations for prior years. The calculator falls back to 2025-2026 with a warning if the year is not found.

- **`backend/tax_calculator/calculator.py: _get_table_for_head_and_schedule()`** — Property income (rental) does not have a dedicated slab table in `TaxYearRates`. Rental income taxed under the NORMAL regime falls through to `None` and produces a warning. The FBR rental income schedule should be added to `TaxYearRates` and the mapping updated.

- **`backend/tax_calculator/calculator.py`** — Company flat-rate calculation is not explicitly handled. The interpreter sets a flat rate in `reasoning`, which the calculator attempts to extract with a regex. A dedicated code path for company taxpayers using `business_company_rate` from the rate table would be more robust.

- **`backend/tax_rules/rates/tax_year_2025_2026.py: _withholding_rates`** — Only 9 withholding sections are listed. The FBR First Schedule Part III contains many more. The `lookup_withholding_rate()` function in `lookup.py` raises `ValueError` for unknown sections.

- **`backend/sessions/router.py: list_sessions()`** — Makes N+1 Supabase queries (one per session to fetch the last message). This should be replaced with a single query using `JOIN` or a Supabase RPC function.

- **`backend/pipeline/router.py`** — The `updated_at` field on the sessions table is not updated when new messages are added. Session list ordering by `updated_at` will always reflect creation time.

- **`backend/tax_extractor/extractor.py`** — No explicit AOP or company extraction templates. The extractor handles AOPs via the general taxpayer type field but has no specialised extraction for partnership share percentages or corporate balance sheet data.

### Frontend

- **`frontend/src/trace.jsx: TraceDrawer`** — The backend trace drawer is partially wired up. It renders static/mock trace data structure but is not connected to the actual LangGraph node execution traces returned in `PipelineResponse`.

- **`frontend/src/data.jsx`** — `HISTORY`, `SAMPLE_USER`, `SAMPLE_ANSWER`, and `CALENDAR` are static mock data. The calendar events (`CALENDAR`) are hardcoded and not driven by the current date or fetched from a live data source.

- **`frontend/src/structured.jsx: StructuredModal`** — The structured input form generates a JSON object that is serialised as a string and sent as the user message. The pipeline extractor then must re-parse this JSON from the message text. A dedicated structured-input endpoint that bypasses extraction would be more reliable.

- **`frontend/app.css`** — No responsive breakpoints are defined. The split-panel layout requires a minimum screen width to be usable; mobile is not supported.

- **`frontend/src/tweaks.jsx`** — The tweaks panel exists but is not wired to actually persist settings across sessions. Changes are held in local component state only.

### Infrastructure

- **`supabase_schema.sql`** — No Row Level Security (RLS) policies are defined. The application uses the service role key for all DB operations, bypassing Supabase's built-in access control. In production, RLS policies should be added so that each user can only access their own sessions and messages.

- **`backend/auth/email.py`** — The SMTP `_send()` function is run in `asyncio`'s default thread pool executor. For high-concurrency production use, a dedicated email queue (e.g., Celery with Redis) would be more appropriate.

---

## 14. Running the Project

### Prerequisites

- Python 3.11+
- A Supabase project (free tier works)
- A Groq API key (or any LiteLLM-compatible provider)
- For Google OAuth: a Google Cloud project with OAuth 2.0 credentials
- For password reset: a Gmail account with an app password, or any SMTP server

### Environment Setup

```powershell
# Clone the repository
git clone <repo_url>
cd Tax_Sathi

# Create and activate a conda environment (as used in development)
conda create -n Tax_Sathi python=3.11
conda activate Tax_Sathi

# Install backend dependencies
pip install -r backend/requirements.txt

# Copy and fill in the environment file
copy .env.example .env
# Edit .env with your Supabase URL, service role key, LLM API keys, etc.
```

### Database Setup

1. Open the Supabase dashboard for your project.
2. Go to the SQL editor.
3. Paste and run the contents of `supabase_schema.sql`.
4. If updating an existing database (not fresh), only run the ALTER TABLE statements at the bottom of the file.

### Starting the Backend

```powershell
# From the project root
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`.

**Important:** The `TreeIndex` and `ContentFetcher` singletons are loaded on first use. The first request that triggers retrieval (any tax calculation or FBR Q&A) will load `fbr_combined.md` (~23,795 lines) and `fbr_combined_structure.json` into memory. This takes 1–3 seconds on first load but is then cached for the lifetime of the process.

**File paths:** The default paths for the FBR document files are relative to the working directory from which uvicorn is launched. If you start uvicorn from a directory other than the project root, set `RULE_RETRIEVER_TREE_INDEX_PATH` and `RULE_RETRIEVER_MARKDOWN_PATH` to absolute paths in `.env`.

### Serving the Frontend

The frontend is a static directory — serve it from any HTTP server:

```powershell
# Option 1: Python built-in HTTP server (from the frontend/ directory)
cd frontend
python -m http.server 3000

# Option 2: Use VS Code Live Server or any static file server
# Point the server root to the frontend/ directory
```

Open `http://localhost:3000` in a browser.

**CORS:** The backend defaults to allowing origins `http://localhost:5173`, `http://localhost:3000`, and `http://127.0.0.1:5173`. If you serve the frontend on a different port, add the origin to `CORS_ALLOWED_ORIGINS` in `.env`.

### Google OAuth Setup

1. Create a Google Cloud project at https://console.cloud.google.com.
2. Enable the Google+ API / People API.
3. Create OAuth 2.0 credentials (Web application type).
4. Add `http://localhost:8000/api/v1/auth/google/callback` to authorized redirect URIs.
5. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_FRONTEND_REDIRECT=http://localhost:3000` in `.env`.

### Running the Tests

All tests require the working directory to be the project root.

```powershell
# Integration tests (require .env to be populated; no running server needed)
python backend/tests/test_extractor_to_retriever.py
python backend/tests/test_retriever_to_interpreter.py
python backend/tests/test_interpreter_to_calculator.py

# End-to-end test (requires the backend server to be running on port 8000)
# Terminal 1:
uvicorn backend.main:app --port 8000

# Terminal 2:
python backend/tests/test_e2e_pipeline.py
```

### Common Gotchas

- **Windows UTF-8 encoding:** If you see `UnicodeDecodeError` when loading `fbr_combined.md`, ensure Python is started with `PYTHONIOENCODING=utf-8` or the file is opened with `encoding="utf-8"` (which it is in `content_fetcher.py`). Windows systems may default to a different encoding for file I/O.

- **Groq API prefix:** LiteLLM requires the `groq/` prefix for Groq models (e.g., `groq/llama-3.3-70b-versatile`). If you switch to OpenAI, use `gpt-4o` without a prefix. The `llm_api_key` in `.env` must match the provider.

- **Supabase service role vs anon key:** The backend uses the **service role key** (`SUPABASE_SERVICE_ROLE_KEY`), not the anon key. The service role key bypasses Row Level Security. Do not expose it in client-side code.

- **LLM JSON mode:** The tax interpreter uses `response_format={"type": "json_object"}` when supported by the model. Groq's Llama models support JSON mode on most endpoints but not all. If JSON mode fails (raises an exception), the interpreter automatically retries without it and uses `_extract_json()` to parse the response.

- **First retrieval latency:** The first call to any endpoint that triggers the rule retriever will load ~23,000 lines of markdown into memory. Subsequent requests use the in-memory singleton and are fast. Expect 2–5 seconds extra on the very first request after startup.

- **Password reset SMTP:** Gmail requires an App Password if 2-factor authentication is enabled on the account. Use the app password as `SMTP_PASSWORD` in `.env`, not the main account password. `SMTP_FROM_EMAIL` must match the Gmail address used.
