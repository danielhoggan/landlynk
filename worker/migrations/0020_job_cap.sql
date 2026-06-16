-- 0020_job_cap.sql
-- A monthly catchment-run allowance per builder group, alongside the AI cap.
-- Like the AI allowance it is pooled per group, resets on the 1st, and blocks
-- external users once spent (internal users and admins are unmetered).
--
-- job_usage is an append-only log of runs. Counting this log (not the live
-- catchment rows) means deleting or archiving a catchment never reduces the
-- month's run tally, so the allowance cannot be reclaimed by tidying up.

BEGIN;

-- A monthly run allowance for the group. NULL means unlimited.
ALTER TABLE builder_group ADD COLUMN IF NOT EXISTS monthly_job_cap INTEGER;

-- One row per catchment run submitted, for counting and audit.
CREATE TABLE IF NOT EXISTS job_usage (
    id           BIGSERIAL PRIMARY KEY,
    email        TEXT,
    group_id     TEXT,
    catchment_id TEXT,
    period       TEXT NOT NULL,  -- 'YYYY-MM', the allowance window
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_job_usage_group_period
    ON job_usage (group_id, period);

COMMIT;
