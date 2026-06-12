-- 0011_area_metrics.sql
-- A generic, long-format store for additional area data points (green space,
-- deprivation, crime and so on). One row per area per metric, so a new public
-- dataset is just a new loader writing new metric_keys, with no schema change.
-- Surfaced as Local context on the Battlecard, not (yet) in the ranking.

BEGIN;

CREATE TABLE IF NOT EXISTS area_metric (
    area_code   TEXT NOT NULL,
    area_type   TEXT NOT NULL,
    metric_key  TEXT NOT NULL,
    value       DOUBLE PRECISION,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (area_code, area_type, metric_key)
);
CREATE INDEX IF NOT EXISTS idx_area_metric_area ON area_metric (area_code, area_type);

COMMIT;
