-- 0012_hospitals.sql
-- Hospital locations (points) for distance-to-nearest-hospital per MSOA, and a
-- per-provider NHS waiting-times table for nearest-A&E context. Hospitals are
-- kept as points so both the per-MSOA distance and the nearest-to-development
-- lookup can use them.

BEGIN;

CREATE TABLE IF NOT EXISTS hospital (
    id         BIGSERIAL PRIMARY KEY,
    name       TEXT,
    org_code   TEXT,
    lat        DOUBLE PRECISION,
    lng        DOUBLE PRECISION,
    geom       geometry(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_hospital_geom ON hospital USING GIST (geom);

-- Per-provider waiting times (A&E four-hour performance, RTT median weeks),
-- refreshed monthly. Keyed by NHS organisation (provider) code.
CREATE TABLE IF NOT EXISTS nhs_waiting (
    org_code      TEXT PRIMARY KEY,
    provider_name TEXT,
    ae_4hr_pct    DOUBLE PRECISION,
    rtt_weeks     DOUBLE PRECISION,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
