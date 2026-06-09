-- 0005_users_sharing_archive.sql
-- User accounts, roles, per-catchment ownership, sharing, archiving and
-- per-account settings. History becomes private to its owner (plus anyone it is
-- shared with); admins see everything. Deleting is admin only; everyone else
-- archives, which hides a run without destroying it (an archived area shows
-- them). Settings move from the browser to the account so they follow the user.

BEGIN;

-- Directory of known users, upserted on first authenticated request. Role
-- governs permissions: admins delete and manage roles; users archive only.
CREATE TABLE IF NOT EXISTS app_user (
    email      TEXT PRIMARY KEY,
    name       TEXT,
    role       TEXT NOT NULL DEFAULT 'internal-user'
               CHECK (role IN ('admin', 'internal-user', 'external-user')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Per-account settings (default assumptions, LA toggle). JSONB so the shape can
-- evolve with the form without a migration each time.
CREATE TABLE IF NOT EXISTS user_settings (
    email      TEXT PRIMARY KEY REFERENCES app_user (email) ON DELETE CASCADE,
    settings   JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ownership and archive state on the catchment. owner_email is the creator;
-- legacy rows (owner NULL) are visible to admins only.
ALTER TABLE catchment ADD COLUMN IF NOT EXISTS owner_email TEXT;
ALTER TABLE catchment ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_catchment_owner ON catchment (owner_email);

-- Explicit shares: a catchment visible to another user's history.
CREATE TABLE IF NOT EXISTS catchment_share (
    catchment_id     UUID NOT NULL REFERENCES catchment (id) ON DELETE CASCADE,
    shared_with_email TEXT NOT NULL,
    shared_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (catchment_id, shared_with_email)
);
CREATE INDEX IF NOT EXISTS idx_share_user ON catchment_share (shared_with_email);

COMMIT;
