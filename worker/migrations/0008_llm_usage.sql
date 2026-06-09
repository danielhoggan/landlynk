-- 0008_llm_usage.sql
-- Metering for AI Local Area Profile generations, managed SaaS-style. External
-- users draw from a monthly allowance pooled per builder group; internal users
-- and admins are unmetered (they get a cost confirmation in the UI instead).
-- Cached results never hit a provider, so they are never recorded or counted.

BEGIN;

-- A monthly generation allowance for the group. NULL means unlimited.
ALTER TABLE builder_group ADD COLUMN IF NOT EXISTS monthly_llm_cap INTEGER;

-- One row per actual (non-cached) LLM generation, for counting and audit.
CREATE TABLE IF NOT EXISTS llm_usage (
    id         BIGSERIAL PRIMARY KEY,
    email      TEXT,
    group_id   TEXT,
    model      TEXT,
    period     TEXT NOT NULL,  -- 'YYYY-MM', the allowance window
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_llm_usage_group_period
    ON llm_usage (group_id, period);

COMMIT;
