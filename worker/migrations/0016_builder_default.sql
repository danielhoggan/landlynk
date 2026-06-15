-- 0016_builder_default.sql
-- White-label the app interface, not just exports. A signed-in user is pinned to
-- a builder_group (a client), which can own several brands. The interface takes
-- its brand (logo, colours, fonts) from the group's default brand, or the first
-- brand by name when none is flagged. This column marks that default brand.

BEGIN;

ALTER TABLE builder ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT false;

-- At most one default brand per group.
CREATE UNIQUE INDEX IF NOT EXISTS idx_builder_one_default
    ON builder (group_id) WHERE is_default;

COMMIT;
