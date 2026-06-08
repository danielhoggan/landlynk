# Claude to-do list

Build tasks to get LandLynk production-ready. Checked items are done and on the
branch. Unchecked items are what I will keep building while you handle Railway,
the App Registration and the variables.

## Done

- [x] Geocoding: postcode (postcodes.io) and OS grid ref (pyproj), GB validation.
- [x] Isochrone: OpenRouteService provider, pluggable for self-hosted ORS/Valhalla.
- [x] Spatial intersect with overlap threshold and proportion weighting.
- [x] ONS/OS reference loaders: boundaries, lookup, demographics, tenure, income,
      postcodes, with suppression handling and provenance.
- [x] Transparent, explainable scoring.
- [x] Battlecard assembly with signal-driven commentary (house prose conventions).
- [x] Pipeline orchestrator, end to end, fully unit tested offline.
- [x] Worker job API (submit, poll, read) with background runner.
- [x] Interactive MapLibre map, ranking list, submit-poll-deepdive flow.
- [x] Durable persistence (catchment, areas, Battlecards) in Postgres.
- [x] Durable Postgres isochrone cache and connection pooling.
- [x] PDF Battlecard export (worker renderer plus web download).
- [x] SSO middleware gate on every route, sign-in page.
- [x] Dockerfiles, Next standalone output, migration runner, Railway config.
- [x] Deployment runbook (DEPLOYMENT.md).

## Building next (no dependency on your tasks)

- [ ] Development brief form: capture town, strapline, lifestyle pillars, feature
      bullets, price band and bed range on submission, so the Battlecard header
      and scoring use the real scheme rather than defaults. (Highest impact on
      output quality.)
- [ ] Scoring config panel: expose weights, price band, bed range and overlap
      threshold in the UI, persisted with the catchment.
- [ ] Render the three Battlecard charts in the web drawer (age bar, income bar
      with callouts, tenure donut) to match the Abbots Vale visual summary.
- [ ] History page: list past catchments from the database, reopen one without
      recompute. (Nav link exists but is currently a dead route.)
- [ ] Battlecards and Settings pages behind the existing nav links.
- [ ] Loading, empty and error states across the map and drawer.

## Building next (Phase 2 scope, after MVP proven)

- [ ] KML export: full catchment polygon plus foldered, colour-coded area pins
      with Battlecard info balloons (the colour helper exists; the writer does not).
- [ ] PPTX export to the client brand template.
- [ ] LA-level support for the leisure use case (PfP pattern).
- [ ] GWI persona channel enrichment in audience messaging (pending your licence
      confirmation).

## Needs an input from you, then I finish it

- [ ] Embed Tenorite in the PDF/PPTX once you share the font file (Helvetica
      fallback is in place).
- [ ] Validate the loaders and end-to-end run against real ONS data once the
      database is up; fix any column-mapping mismatches from the actual files.
- [ ] Confirm MSOA-only vs LA-from-day-one so I scope the boundary loading.

## Engineering hardening (will pick up as we stabilise)

- [ ] Integration test of PostgresStore and the loaders against a real PostGIS
      (testcontainers or a CI database), to complement the offline unit tests.
- [ ] Replace the OSM raster basemap with an open vector style for production.
- [ ] Structured logging and error reporting in the worker pipeline.
- [ ] Rate-limit handling and backoff for the isochrone provider.
