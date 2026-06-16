-- 0022_site_source_type.sql
-- Tag development sites by source so the brownfield land register and Local Plan
-- housing allocations can share one table and be shown and filtered separately.
-- Existing rows are brownfield.

BEGIN;

ALTER TABLE development_site
    ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'brownfield';

COMMIT;
