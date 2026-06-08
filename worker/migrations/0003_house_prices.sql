-- 0003_house_prices.sql
-- Local house prices by area, for the house-builder use case: what homes sell
-- for locally is the core of site appraisal and scheme pricing. Source is ONS
-- House Price Statistics for Small Areas (HPSSA), median price paid by MSOA,
-- Open Government Licence. Suppressed cells are NULL, never zero.

BEGIN;

CREATE TABLE IF NOT EXISTS house_prices (
    area_code    TEXT NOT NULL,
    area_type    TEXT NOT NULL CHECK (area_type IN ('MSOA', 'LA')),
    median_price NUMERIC,
    PRIMARY KEY (area_code)
);

COMMIT;
