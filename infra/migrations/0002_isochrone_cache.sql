-- 0002_isochrone_cache.sql
-- Durable isochrone cache. Results are cached by coordinate and parameters so
-- re-runs never re-bill the provider (CLAUDE.md; SCOPING.md 11). A process-local
-- cache is lost on restart and not shared across worker instances, so the cache
-- is persisted here.

BEGIN;

CREATE TABLE IF NOT EXISTS isochrone_cache (
    cache_key  TEXT PRIMARY KEY,
    geojson    JSONB       NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
