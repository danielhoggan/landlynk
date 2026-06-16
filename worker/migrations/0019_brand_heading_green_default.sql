-- 0019_brand_heading_green_default.sql
-- Switch the default brand heading colour from Royal Blue to the LandLynk green,
-- so a brand created without an explicit colour, and any export that falls back
-- to the default, carries the LandLynk green rather than blue. Existing brands
-- that chose a colour are left untouched; only the column default changes.

BEGIN;

ALTER TABLE builder ALTER COLUMN theme_heading SET DEFAULT '#2F6B3A';

COMMIT;
