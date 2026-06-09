-- 0010_brand_theme.sql
-- Richer brand theming: primary, secondary and accent colours, a list of web
-- fonts for the brand, and the stored logo path. theme_heading stays as the
-- primary colour (already used by exports); the new columns extend it.

BEGIN;

ALTER TABLE builder ADD COLUMN IF NOT EXISTS theme_secondary TEXT;
ALTER TABLE builder ADD COLUMN IF NOT EXISTS theme_accent TEXT;
ALTER TABLE builder ADD COLUMN IF NOT EXISTS fonts JSONB NOT NULL DEFAULT '[]';
ALTER TABLE builder ADD COLUMN IF NOT EXISTS logo_path TEXT;

COMMIT;
