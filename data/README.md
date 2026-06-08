# data

Reference data loaders and seed definitions for landlynk: ONS, OS and GWI.

## Principles

- All reference data is open or free tier. No third-party data licences. Adding
  any paid source needs sign-off (house-standards.md, data handling).
- Reference data loads through a versioned loader. Each load records source,
  version and date in the `reference_load` table so refreshes are auditable.
- Never hand-edit reference tables. Always load through a loader.
- ONS suppression and rounding are handled explicitly: a suppressed cell maps to
  NULL, never zero. Data confidence is surfaced in the deep-dive, not hidden.

## Layout

```
data/
  sources.yaml         manifest of every reference dataset, provider and licence
  loaders/
    base.py            the ReferenceLoader contract (fetch, transform, load, run)
    db.py              shared Postgres writer (atomic replace plus provenance)
    transforms.py      suppression handling, age band and median age helpers
    geography.py       geo_lookup and geo_boundaries loaders
    census.py          demographics and tenure loaders
    income.py          income estimates loader
    postcodes.py       OS CodePoint Open loader
    manifest.py        reads sources.yaml into SourceSpecs
    run.py             CLI to run a load
  tests/               transform unit tests over representative source rows
```

## Datasets

See `sources.yaml`. The MVP residential path needs: geo lookup and boundaries
(ONS Open Geography Portal), census demographics and tenure (ONS Census 2021),
income estimates (ONS), and postcode lookup (OS CodePoint Open). GWI personas
enrich messaging and channel mix; confirm licence terms before embedding
persona-driven guidance in client outputs.

## Setup

```bash
cd data
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Running a load

Download the source file from the open portal (see `sources.yaml` for provider
and licence), then run the loader against the local file. The CLI reads local
files so it is unaffected by network policy or portal URL changes. Set
`DATABASE_URL` to a Postgres with PostGIS instance first.

```bash
python -m loaders.run geo_lookup --source OA_to_MSOA_to_LAD.csv
python -m loaders.run geo_boundaries --source MSOA_2021_boundaries.geojson --area-type MSOA
python -m loaders.run census_demographics --source age_single_year.csv --households-source household_composition.csv
python -m loaders.run census_tenure --source tenure.csv
python -m loaders.run income_estimates --source msoa_income.xlsx
python -m loaders.run postcode_lookup --source codepoint_open.csv
```

Each load truncates and replaces its target table in one transaction and writes
a `reference_load` row recording source, version and date.

Column labels vary between ONS releases. The loaders detect the area code column
and match value columns by substring, with the defaults set for the December
2021 census geography and NOMIS bulk exports. Override the column maps on the
loader if a later vintage renames fields, and pin the concrete version in
`sources.yaml` before each load.
