# LandLynk

The Geographic Intelligence Engine. A platform that turns a development postcode
or OS grid reference into a ranked, clickable catchment map with auto-generated
Battlecards and deep-dive analysis per area.

## Documentation

Read these in order before working in the repo:

1. [CLAUDE.md](./CLAUDE.md) - operating contract for working in this repo.
2. [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) - what we are building and why.
3. [house-standards.md](./house-standards.md) - engineering standards and stack.
4. [design-framework.md](./design-framework.md) - UI and output design system.
5. [SCOPING.md](./SCOPING.md) - full product scope and phasing.

## Repository layout

```
/web     Next.js app (UI, API route handlers)
/worker  Python geospatial and data worker
/data    reference data loaders and seed definitions (ONS, OS, GWI)
/infra   Railway and deploy config, migrations
```

## Status

Phase 1 (MVP). MSOA level, residential use case. The end-to-end pipeline is
implemented and unit tested: geocode (postcode and OS grid ref), drive-time
isochrone (OpenRouteService, cached), spatial intersect, ONS join, transparent
scoring, Battlecard assembly, the worker job API, and the interactive MapLibre
map with ranked clickable areas and per-area deep-dive. See SCOPING.md Section 10
for phasing. Each subdirectory has its own README with setup detail.

## Running it live

The code runs end to end; a live run needs three things the build cannot supply
itself:

1. An OpenRouteService API key (free tier). Set `WORKER_ISOCHRONE_API_KEY`.
2. A PostGIS database (a PostGIS image, not plain Postgres). Set
   `WORKER_DATABASE_URL`. The worker auto-applies `worker/migrations/` on deploy;
   then load the reference data with the loaders in `data/` (see `data/README.md`).
3. Azure AD SSO credentials for the web app (see `web/.env.example`).

With those set, run the worker (`uvicorn landlynk_worker.app:app`) and the web
app (`npm run dev`), point `WORKER_BASE_URL` at the worker, paste a postcode and
the ranked catchment map renders.

## Tests

```bash
cd worker && pip install -r requirements-dev.txt && pytest   # pipeline, scoring, API
cd data   && pip install -r requirements-dev.txt && pytest   # loader transforms
cd web    && npm install && npm run build                    # typecheck and build
```
