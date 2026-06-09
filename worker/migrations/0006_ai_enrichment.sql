-- 0006_ai_enrichment.sql
-- Global app config (key/value) and a cache for AI-generated Local Area
-- Profiles. app_config holds settings that are not per user, such as the default
-- AI model an admin selects. area_profile_cache stores generated descriptions
-- and amenities keyed by the area set and model, so the same lookup never
-- re-bills the LLM provider (CLAUDE.md: cache external calls, never re-bill).

BEGIN;

CREATE TABLE IF NOT EXISTS app_config (
    key        TEXT PRIMARY KEY,
    value      JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS area_profile_cache (
    cache_key  TEXT PRIMARY KEY,
    model      TEXT NOT NULL,
    payload    JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
