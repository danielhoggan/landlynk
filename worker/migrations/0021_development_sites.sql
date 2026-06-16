-- 0021_development_sites.sql
-- Development sites from the open planning.data.gov.uk brownfield land register:
-- points (with dwelling capacity) shown within a catchment for the Find a site
-- intent, so area discovery can surface the actual buildable plots. Kept as
-- points so a catchment can select the sites that fall inside it.

BEGIN;

CREATE TABLE IF NOT EXISTS development_site (
    id            BIGSERIAL PRIMARY KEY,
    reference     TEXT,
    name          TEXT,
    hectares      DOUBLE PRECISION,
    min_dwellings INTEGER,
    max_dwellings INTEGER,
    lat           DOUBLE PRECISION,
    lng           DOUBLE PRECISION,
    geom          geometry(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_development_site_geom
    ON development_site USING GIST (geom);

COMMIT;
