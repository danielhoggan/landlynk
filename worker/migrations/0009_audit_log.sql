-- 0009_audit_log.sql
-- A full audit trail of meaningful actions for the admin Audits tab: who did
-- what, when, to which target, any cost incurred, and what was created or
-- deleted. Append only; queried with date, user, action and cost filters.

BEGIN;

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_email TEXT,
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   TEXT,
    detail      JSONB,
    cost        NUMERIC NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor_email);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log (action);

COMMIT;
