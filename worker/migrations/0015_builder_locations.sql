-- 0015_builder_locations.sql
-- A brand's best / target locations (postcodes of known-good developments or
-- areas). Used to weight scoring toward areas that resemble them (a lookalike
-- signal), so a brand can rank a new catchment against where it already does
-- well.

BEGIN;

ALTER TABLE builder
    ADD COLUMN IF NOT EXISTS target_locations JSONB NOT NULL DEFAULT '[]';

COMMIT;
