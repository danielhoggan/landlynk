-- 0013_postcodes.sql
-- ONS Postcode Directory centroids (postcode to coordinate). Used to geocode
-- NHS hospital postcodes from the ODS API, which carries postcodes but not
-- coordinates. Kept as a plain lookup so it can geocode other postcode-only
-- sources later too.

BEGIN;

CREATE TABLE IF NOT EXISTS postcode_centroid (
    postcode TEXT PRIMARY KEY,  -- normalised: uppercase, no spaces
    lat      DOUBLE PRECISION NOT NULL,
    lng      DOUBLE PRECISION NOT NULL
);

COMMIT;
