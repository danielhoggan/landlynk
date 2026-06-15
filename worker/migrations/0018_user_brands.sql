-- 0018_user_brands.sql
-- Assign users to brands (many-to-many), so one user (e.g. an agency CMO) can
-- access several brands across groups and switch the active brand in the app.
-- Industry moves onto the brand (each brand its own sector, since a user can now
-- span brands), and the admin "default brand" flag is removed: the active brand
-- is the user's choice, defaulting to the first alphabetically.

BEGIN;

-- Per-brand industry; seed from the group's industry where one was set.
ALTER TABLE builder ADD COLUMN IF NOT EXISTS industry TEXT;
UPDATE builder b SET industry = g.industry
    FROM builder_group g
    WHERE b.group_id = g.id AND g.industry IS NOT NULL AND b.industry IS NULL;

-- Explicit brand grants. A user may also hold a whole-group grant
-- (app_user.builder_group_id) which covers all of that group's brands.
CREATE TABLE IF NOT EXISTS user_brand (
    email    TEXT NOT NULL,
    brand_id TEXT NOT NULL REFERENCES builder (id) ON DELETE CASCADE,
    PRIMARY KEY (email, brand_id)
);
CREATE INDEX IF NOT EXISTS idx_user_brand_email ON user_brand (email);

-- The active brand is chosen by the user now, so the admin default is gone.
DROP INDEX IF EXISTS idx_builder_one_default;
ALTER TABLE builder DROP COLUMN IF EXISTS is_default;

COMMIT;
