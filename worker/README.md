# worker

The Python geospatial and data worker for landlynk. Geocode, isochrone, spatial
intersect, ONS join, scoring and Battlecard assembly, plus KML and document
output. Heavy work runs here, never in a Next.js request cycle.

## Stack

- Python 3.11+, GeoPandas and Shapely for geometry.
- FastAPI for the HTTP surface the web API layer calls.
- Postgres with PostGIS via SQLAlchemy and GeoAlchemy2.
- pydantic for the Battlecard payload schema and settings.
- black formatting, ruff lint, pytest.

## Setup

```bash
cd worker
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
ruff check src tests
black --check src tests
```

Run the service locally:

```bash
uvicorn landlynk_worker.app:app --reload
```

## Pipeline

```
src/landlynk_worker/
  pipeline/
    resolve.py     1. input to WGS84 coordinate (postcode or grid ref)
    isochrone.py   2. drive-time polygon, cached by coordinate and parameters
    intersect.py   3. boundary overlap and proportion inside (reference impl)
    join.py        4. ONS demographics, tenure, income to AreaProfile
    outputs/kml.py 7. KML for Google Earth
  scoring/         5. pure, tested prioritisation
  battlecard/      6. the Battlecard payload schema (mirrors the TS contract)
```

## What is wired vs stubbed

The pure, reproducible cores are implemented and tested: scoring, spatial
intersect, isochrone caching, input detection, Battlecard schema validation.

Stubbed until external services and the database are connected: live geocoding,
the isochrone provider call, Postgres reads and writes, the job runner, and the
PDF, PPTX and full KML rendering. These raise `NotImplementedError` with a note.

## Tests

Scoring and spatial intersect are the parts that must be reproducible and
explainable, so they are unit tested and not shipped without tests. The
Battlecard payload is schema-validated so all four render surfaces can trust it.
