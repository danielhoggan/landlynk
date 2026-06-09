-- 0007_builder_profiles.sql
-- Builder profiles: the org model for client house builders. A builder_group is
-- a client (e.g. a plc) that owns one or more brand entities (builder). Each
-- brand has one or more profiles: a saved targeting preset (audience segment,
-- product beds and price, brand theme and default messaging). External users
-- are pinned to a group and may only use that group's profiles; internal users
-- and admins use any. The profile fills the catchment brief in one click.

BEGIN;

CREATE TABLE IF NOT EXISTS builder_group (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS builder (
    id            TEXT PRIMARY KEY,
    group_id      TEXT NOT NULL REFERENCES builder_group (id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    theme_heading TEXT NOT NULL DEFAULT '#4169E1',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_builder_group ON builder (group_id);

CREATE TABLE IF NOT EXISTS builder_profile (
    id         TEXT PRIMARY KEY,
    builder_id TEXT NOT NULL REFERENCES builder (id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    segment    TEXT,
    bed_range  TEXT,
    price_from NUMERIC,
    price_to   NUMERIC,
    strapline  TEXT,
    pillars    JSONB NOT NULL DEFAULT '[]',
    features   JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_profile_builder ON builder_profile (builder_id);

-- External users are scoped to a single group. NULL means unscoped (internal).
ALTER TABLE app_user ADD COLUMN IF NOT EXISTS builder_group_id TEXT
    REFERENCES builder_group (id) ON DELETE SET NULL;

COMMIT;
