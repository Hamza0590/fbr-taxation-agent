-- Tax Sathi — Supabase schema reference
-- Run this SQL in the Supabase SQL editor to initialise the database.
-- When adding columns to an existing DB, use the ALTER TABLE statements at the bottom.

-- ── Extension ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── users ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name     TEXT,
    phone         TEXT,
    cnic          TEXT UNIQUE,
    ntn           TEXT,
    city          TEXT,
    province      TEXT,
    tax_year      TEXT,
    auth_provider TEXT DEFAULT 'email',
    created_at    TIMESTAMPTZ DEFAULT now()
);

-- ── sessions ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT DEFAULT 'New Chat',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ── messages ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT CHECK (role IN ('user', 'assistant')),
    content     TEXT,
    canvas_data JSONB,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- ── password_reset_tokens ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON password_reset_tokens(token);

-- ── Migrations — run these on an existing DB ─────────────────────────────────
-- Gap 1A: Google OAuth support
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_provider TEXT DEFAULT 'email';
-- Gap 1B: CNIC login support
ALTER TABLE users ADD COLUMN IF NOT EXISTS cnic TEXT UNIQUE;
