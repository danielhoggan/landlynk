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
- [x] Battlecard charts in the web drawer (age bar, income bar with callouts,
      tenure donut).
- [x] Expanded Battlecard beyond the reference card, all data-derived: pricing
      rationale (implied affordable price vs scheme price), addressable segment
      sizes (FTB pipeline, downsizer pool, family households), catchment context
      (income index, share of catchment population) and explicit data
      confidence. Wired through the schema, assembler, web drawer and PDF.

## Building next (no dependency on your tasks)

- [x] Development brief form: capture town, strapline, lifestyle pillars, feature
      bullets, price band and bed range on submission, so the Battlecard header
      and scoring use the real scheme rather than defaults.
- [x] Battlecard charts in the web drawer (age bar, income bar with callouts,
      tenure donut).
- [x] Expanded Battlecard content (pricing, addressable segments, catchment
      context, data confidence).
- [x] Scoring config panel: expose weights, price band, bed range and overlap
      threshold in the UI, persisted with the catchment.
- [x] History page: list past catchments from the database, reopen one without
      recompute via /?catchment=<id>.
- [x] Settings page (account, default scoring weights, sign out) and tidied nav
      (Battlecards open from inside a catchment, so the dead link was removed).
- [x] Loading and empty states across the ranking list and Battlecard drawer.

## Building next (Phase 2 scope, after MVP proven)

- [x] Server-side ONS auto-loader: the worker downloads boundaries (ONS ArcGIS),
      census and income and loads PostGIS itself. Triggered from the in-app
      Reference data page with status polling. No local commands.
- [x] LandLynk logo (themeable wordmark), standard nav, and a How it Works page
      (purpose, value, user flow, real use cases). Removed Mediaworks references.
- [x] KML export: catchment polygon plus foldered, colour-coded area pins with
      Battlecard info balloons, emitted as XML (no native build dependency).
      Worker endpoint and web download wired.
- [x] PPTX export to the client brand template (worker renderer, endpoint and
      web download). Brand heading colour themeable.
- [x] LA-level support: area-level selector on the catchment form and the
      Reference data loader (the pipeline already threaded area_type through).
- [ ] GWI persona channel enrichment in audience messaging (pending your licence
      confirmation).

## Needs an input from you, then I finish it

- [ ] Embed Tenorite in the PDF/PPTX once you share the font file (Helvetica
      fallback is in place).
- [ ] Validate the loaders and end-to-end run against real ONS data once the
      database is up; fix any column-mapping mismatches from the actual files.
- [ ] Confirm MSOA-only vs LA-from-day-one so I scope the boundary loading.

## Engineering hardening (will pick up as we stabilise)

- [x] Integration test of PostgresStore against a real PostGIS, gated on
      WORKER_TEST_DATABASE_URL (skips without a database), for CI.
- [x] Open vector basemap (OpenFreeMap, no key) replacing OSM raster; override
      with NEXT_PUBLIC_MAP_STYLE.
- [x] Structured logging in the worker pipeline and job runner.
- [x] Rate-limit handling and backoff for the isochrone provider.
