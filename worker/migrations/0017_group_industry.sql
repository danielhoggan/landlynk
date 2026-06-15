-- 0017_group_industry.sql
-- Capture each client group's industry so the app can tailor explanatory content
-- (e.g. the How it works page) to that company's sector rather than showing the
-- generic, all-sectors version.

BEGIN;

ALTER TABLE builder_group ADD COLUMN IF NOT EXISTS industry TEXT;

COMMIT;
