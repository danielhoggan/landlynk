-- 0001_init.sql
-- Initial schema for landlynk. Postgres with PostGIS.
-- Migrations are versioned and checked in. No schema changes outside migrations
-- (house-standards.md). This mirrors the data model in SCOPING.md Section 6.

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

-- Provenance for the versioned reference data loader. Each load records source,
-- version and date so refreshes are auditable (house-standards.md, data handling).
CREATE TABLE IF NOT EXISTS reference_load (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_name   TEXT        NOT NULL,
    source       TEXT        NOT NULL,
    source_version TEXT      NOT NULL,
    loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Reference tables. Loaded, versioned, read-only at runtime.
-- -----------------------------------------------------------------------------

-- Hierarchical linkage Output Area to MSOA to LA, from ONS lookup tables.
CREATE TABLE IF NOT EXISTS geo_lookup (
    oa_code   TEXT NOT NULL,
    msoa_code TEXT NOT NULL,
    la_code   TEXT NOT NULL,
    msoa_name TEXT,
    la_name   TEXT,
    PRIMARY KEY (oa_code)
);
CREATE INDEX IF NOT EXISTS idx_geo_lookup_msoa ON geo_lookup (msoa_code);
CREATE INDEX IF NOT EXISTS idx_geo_lookup_la ON geo_lookup (la_code);

-- MSOA and LA geometries from ONS boundary GeoJSON. PostGIS geometry column.
CREATE TABLE IF NOT EXISTS geo_boundaries (
    area_code TEXT NOT NULL,
    area_type TEXT NOT NULL CHECK (area_type IN ('MSOA', 'LA')),
    area_name TEXT,
    geom      geometry(MultiPolygon, 4326) NOT NULL,
    PRIMARY KEY (area_code)
);
CREATE INDEX IF NOT EXISTS idx_geo_boundaries_geom ON geo_boundaries USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_geo_boundaries_type ON geo_boundaries (area_type);

-- Population, age bands and household type by area, ONS Census 2021.
-- Suppressed cells are stored as NULL, never zero.
CREATE TABLE IF NOT EXISTS census_demographics (
    area_code             TEXT NOT NULL,
    area_type             TEXT NOT NULL CHECK (area_type IN ('MSOA', 'LA')),
    population            INTEGER,
    households            INTEGER,
    age_0_15              NUMERIC,
    age_16_34             NUMERIC,
    age_35_54             NUMERIC,
    age_55_74             NUMERIC,
    age_75_plus           NUMERIC,
    median_age            NUMERIC,
    family_household_share NUMERIC,
    PRIMARY KEY (area_code)
);

-- Tenure split by area, ONS Census 2021. Shares as proportions 0..1.
CREATE TABLE IF NOT EXISTS census_tenure (
    area_code          TEXT NOT NULL,
    area_type          TEXT NOT NULL CHECK (area_type IN ('MSOA', 'LA')),
    owns_outright      NUMERIC,
    owns_with_mortgage NUMERIC,
    social_rented      NUMERIC,
    private_rented     NUMERIC,
    PRIMARY KEY (area_code)
);

-- Median and mean household income by MSOA and LA, ONS.
CREATE TABLE IF NOT EXISTS income_estimates (
    area_code     TEXT NOT NULL,
    area_type     TEXT NOT NULL CHECK (area_type IN ('MSOA', 'LA')),
    median_income NUMERIC,
    mean_income   NUMERIC,
    PRIMARY KEY (area_code)
);

-- Postcode to coordinate, OS CodePoint Open.
CREATE TABLE IF NOT EXISTS postcode_lookup (
    postcode TEXT NOT NULL,
    geom     geometry(Point, 4326) NOT NULL,
    PRIMARY KEY (postcode)
);
CREATE INDEX IF NOT EXISTS idx_postcode_lookup_geom ON postcode_lookup USING GIST (geom);

-- Persona definitions with channel preferences, for messaging and channel mix.
CREATE TABLE IF NOT EXISTS gwi_personas (
    persona_id TEXT NOT NULL,
    name       TEXT NOT NULL,
    definition JSONB NOT NULL,
    channels   JSONB NOT NULL,
    PRIMARY KEY (persona_id)
);

-- -----------------------------------------------------------------------------
-- Working tables. Written per run.
-- -----------------------------------------------------------------------------

-- One row per analysis.
CREATE TABLE IF NOT EXISTS catchment (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_kind      TEXT NOT NULL CHECK (input_kind IN ('postcode', 'gridref')),
    input_value     TEXT NOT NULL,
    development_name TEXT NOT NULL,
    coordinate      geometry(Point, 4326),
    isochrone       geometry(MultiPolygon, 4326),
    -- Scoring config and parameters stored with the catchment so any ranking is
    -- reproducible and explainable (SCOPING.md Section 8).
    config          JSONB NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
    error           TEXT,
    created_by      TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_catchment_created_by ON catchment (created_by);

-- One row per matched area in a catchment.
CREATE TABLE IF NOT EXISTS catchment_area (
    catchment_id      UUID NOT NULL REFERENCES catchment (id) ON DELETE CASCADE,
    area_code         TEXT NOT NULL,
    area_type         TEXT NOT NULL CHECK (area_type IN ('MSOA', 'LA')),
    proportion_inside NUMERIC NOT NULL,
    priority_score    NUMERIC NOT NULL,
    rank              INTEGER NOT NULL,
    PRIMARY KEY (catchment_id, area_code)
);
CREATE INDEX IF NOT EXISTS idx_catchment_area_rank ON catchment_area (catchment_id, rank);

-- Generated Battlecard payload per catchment area. Stored as structured JSON so
-- the same payload drives the in-app render, the PDF or PPTX export and the KML
-- balloon (SCOPING.md Section 6).
CREATE TABLE IF NOT EXISTS battlecard (
    catchment_id   UUID NOT NULL REFERENCES catchment (id) ON DELETE CASCADE,
    area_code      TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload        JSONB NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (catchment_id, area_code)
);

COMMIT;
