-- 0004_reference_loads.sql
-- Reference load status, persisted. The previous status was process-local, so a
-- worker redeploy reset it to empty even though the loaded data survives in its
-- tables (on the database volume). The app then showed every dataset as not
-- loaded, prompting a needless re-load. Recording status here keeps it across
-- restarts and gives the load an auditable record (CLAUDE.md: versioned,
-- auditable loader).

BEGIN;

CREATE TABLE IF NOT EXISTS reference_loads (
    dataset    TEXT PRIMARY KEY,
    status     TEXT        NOT NULL,
    rows       INTEGER,
    error      TEXT,
    area_type  TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
