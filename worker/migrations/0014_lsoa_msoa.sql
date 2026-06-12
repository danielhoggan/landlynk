-- 0014_lsoa_msoa.sql
-- LSOA (2011) to MSOA (2011) lookup, built from the ONS Postcode Directory when
-- postcodes are loaded. Lets the IMD loader aggregate LSOA-level deprivation to
-- MSOA without a separate lookup file.

BEGIN;

CREATE TABLE IF NOT EXISTS lsoa_msoa (
    lsoa TEXT PRIMARY KEY,
    msoa TEXT NOT NULL
);

COMMIT;
