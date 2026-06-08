# LandLynk - Scoping Document

Working title: LandLynk (confirmed). Formerly the Geographic Intelligence Engine (GIE).

Owner: Dan Hoggan (CTO)
Status: Draft for scoping review
Prepared: 2025-2026 methodology, productised June 2026

---

## 1. Summary

We have a working, mostly manual methodology that turns open ONS geography data into evidence-based marketing strategy for a specific place. It currently produces a one-page Battlecard and an optional KML layer for Google Earth. Applied to date on Tilia and Hopkins new-build developments and on PfP Leisure centre catchments.

This document scopes the productisation of that methodology into a repeatable platform that does two things the manual workflow does not:

1. Removes the single manual bottleneck (translating a smappen drive-time catchment into MSOA or LA codes) by automating geocode to isochrone to spatial intersect.
2. Adds Step 6 as an actionable product: an interactive map of the catchment where every prioritised area is scored, ranked and clickable, and clicking an area surfaces its full Battlecard and deep-dive analysis on demand.

The reference output for what a single area must produce is the Abbots Vale Battlecard (three pages: one visual summary, two commentary pages). The product must generate that quality of output automatically, per area, at scale.

---

## 2. Current methodology (as-is)

Six steps, retained as the spine of the product.

01 Catchment. smappen.com 30-minute drive-time around the development postcode. Boundary matched to MSOA or LA codes by visual inspection. Manual.

02 Define. Set the LA codes and/or MSOA codes that define the study area.

03 Ingest. Pull ONS Census 2021 (population, age bands, tenure mix, household type) plus ONS income estimates for matched geographies.

04 Analyse. Profile the audience: median vs mean income, ownership vs rental split, family structure, age skew. Flag strategic signals.

05 Strategise. Generate the Battlecard: positioning, pricing rationale, channel mix, key messages, sales enablement, tailored to the local profile.

06 Visualise. Export KML for Google Earth: colour-coded pins by category, rich info balloons, folder structure for toggling layers.

Data is open public source only, so there are no third-party data licences to manage. Analysis is reproducible, auditable and refreshable when ONS publishes new releases.

---

## 3. What we are building (to-be)

Two changes to the methodology, both already foreshadowed in the source material.

### 3.1 Automate Steps 01 and 02

Replace the smappen manual step entirely. Given a development postcode or an OS National Grid reference, the pipeline:

- Geocodes to a WGS84 lat/long. postcodes.io for postcodes (free). OS Transformation API or the open-source osgb library for grid references, so the workflow is identical whether or not a postcode exists. New developments often have no postcode yet, so grid-ref support is not optional.
- Generates a 30-minute drive-time isochrone via TravelTime or OpenRouteService (both have free tiers), removing the smappen web UI.
- Spatially intersects the polygon against ONS MSOA or LA boundary GeoJSON (ONS Open Geography Portal) using GeoPandas or Shapely.
- Returns the matched MSOA or LA codes, weighted by the proportion of each area inside the drive-time zone.

This turns a 15 to 30 minute visual task into a sub-second automated lookup, and makes the whole catchment definition repeatable at scale.

### 3.2 Step 6 as an actionable product (the headline ask)

Today Step 6 is a static KML export. The product reframes Step 6 as an interactive, browser-based deliverable:

- An interactive map of the catchment. The drive-time polygon is drawn as an overlay. Every MSOA (or LA) inside it is rendered as a clickable region, colour-coded by priority.
- On-location breakdowns. Each area carries a compact summary of the key signals that matter for targeting: addressable population, income fit to product price band, tenure mix, age skew, household type, priority score and rank.
- Click to deep-dive. Clicking any area opens its full Battlecard and deep-dive analysis in a side drawer or panel: the same content quality as the Abbots Vale reference, generated automatically from that area's data.
- Prioritisation. Areas are ranked so the user sees where to focus campaign spend and sales effort first, not just a flat colour map.

The KML export is retained as a secondary output for stakeholders who prefer Google Earth. The auto-generated PPTX or PDF Battlecard is retained for sales enablement and client-facing decks.

---

## 4. Users and use

Primary user: internal strategy, planning and client delivery teams who today run the manual workflow.

Secondary user: client-facing teams who present Battlecards and maps in pitches and reviews.

Future user: clients themselves via a white-labelled portal (out of MVP scope, noted in Section 10).

Core job to be done: "Give me a postcode or grid ref for a development, and show me which areas around it to target, why, and what to say to each, in a form I can present today."

---

## 5. Architecture

The product follows the established Mediaworks pattern: a Next.js front end, a Python worker for heavy processing, Postgres for storage, Railway for hosting, Azure AD SSO for access. Geospatial work is the heavy lifting here, so it lives in the Python worker, not the Node process.

### 5.1 Components

- Web app (Next.js, Tailwind v3, next-auth v4 Azure AD SSO). The interactive map, area ranking, Battlecard drawer, export controls. Hosted on Railway.
- API layer (Next.js route handlers). Thin. Auth, job submission, reads from Postgres, triggers worker jobs, serves generated outputs.
- Geospatial worker (Python, Railway). Geocode, isochrone, spatial intersect, ONS data join, scoring and prioritisation, Battlecard data assembly, KML and PPTX generation. Long-running jobs run here, not in API request cycles.
- Database (Postgres with PostGIS). Boundary geometries, ONS reference tables, generated catchments and Battlecards, job state. PostGIS is the key extension for spatial joins. pgvector is optional, only if we later add semantic matching of areas to GWI personas.
- Reference data store. ONS Census 2021, ONS income estimates, OS CodePoint Open, ONS geography lookups, MSOA and LA boundary GeoJSON, GWI personas with channel preferences. Loaded into Postgres as seed and reference tables via a versioned loader so refreshes are auditable.

### 5.2 Request flow

1. User submits a development postcode or OS grid ref in the web app.
2. API creates a catchment job and hands it to the Python worker.
3. Worker geocodes, builds the isochrone, intersects against boundaries, returns matched and weighted area codes.
4. Worker joins ONS data for each matched area, runs the profiling and scoring logic, and assembles per-area Battlecard data.
5. Results persist to Postgres. The web app renders the map, ranking and clickable areas.
6. On area click, the app serves that area's Battlecard and deep-dive from stored data. No recompute needed.
7. User exports: in-app PDF or PPTX Battlecard per area, KML catchment layer for Google Earth, or a combined deck.

### 5.3 External services

- postcodes.io. Postcode to lat/long. Free.
- OS Transformation API or osgb library. Grid ref to lat/long.
- TravelTime API or OpenRouteService. Drive-time isochrone. Free tiers, evaluate rate limits in Phase 1.
- ONS Open Geography Portal. Boundary GeoJSON. Open.

All external dependencies are open or free-tier. No data licences. If a paid tier is later needed for isochrone volume, that is a known and bounded cost flagged in Section 9.

---

## 6. Data model (first cut)

Reference tables (loaded, versioned, read-only at runtime):

- `geo_lookup`. Hierarchical linkage Output Area to MSOA to LA. From ONS lookup tables.
- `geo_boundaries`. MSOA and LA geometries (PostGIS geometry column) from ONS boundary GeoJSON.
- `census_demographics`. Population, age bands, household type by area, ONS Census 2021.
- `census_tenure`. Owns outright, owns with mortgage, social rented, private rented by area.
- `income_estimates`. Median and mean household income by MSOA and LA, ONS.
- `postcode_lookup`. Postcode to coordinate, OS CodePoint Open.
- `gwi_personas`. Persona definitions with channel preferences, for messaging and channel mix.

Working tables (written per run):

- `catchment`. One row per analysis: input postcode or grid ref, resolved coordinate, isochrone polygon, parameters (drive-time minutes, product price band, bed range), created by, created at.
- `catchment_area`. One row per matched area in a catchment: area code, area type (MSOA or LA), proportion inside isochrone, priority score, rank.
- `battlecard`. Generated Battlecard payload per catchment area: key stats, audience and messaging blocks, demographic commentary, income commentary, tenure commentary, chart data. Stored as structured JSON so the same payload drives the in-app render, the PDF or PPTX export and the KML balloon.

Storing the Battlecard as a single structured payload per area is the key design decision: one source of truth renders to four surfaces (web drawer, PDF, PPTX, KML balloon).

---

## 7. Pipeline stages (worker detail)

1. Resolve input. Detect postcode vs grid ref. Geocode accordingly. Validate the coordinate falls within GB.
2. Isochrone. Call the chosen isochrone API for a 30-minute drive-time polygon. Cache by coordinate and parameters so re-runs are free.
3. Intersect. PostGIS spatial query: which MSOA or LA geometries overlap the polygon, and what proportion of each falls inside. Discard areas below a configurable overlap threshold to avoid noise from clipped edges.
4. Join. For each retained area, pull demographics, tenure and income from the reference tables.
5. Profile and score. Compute the strategic signals (Section 8) and a priority score per area.
6. Assemble Battlecard. Build the structured payload per area: stats, charts, audience and messaging, three commentary blocks. The commentary is templated from the signals, not free-written, so output is consistent and auditable. Phase 2 may add an LLM pass to sharpen prose, gated behind a review step.
7. Outputs. Render KML (catchment polygon plus colour-coded area pins with info balloons, foldered for toggling) and prepare data for PDF and PPTX export.

---

## 8. Prioritisation and scoring

This is what makes Step 6 actionable rather than decorative. Each area gets a priority score so the map ranks where to target first. The score is a transparent weighted blend, tuned per project, of:

- Income fit. How well the area's median and mean household income matches the development's price band. The Abbots Vale logic is the model: a narrow income spread with no households above 70k argues for mid-market positioning, not luxury. The score rewards alignment, not just high income.
- Tenure signal. Private rented share indicates a first-time buyer pipeline. Outright ownership indicates downsizer potential. Mortgaged ownership indicates second-stepper progression. The score weights these against the product's target audiences.
- Age skew. Match of the area's age profile to the product. 18 to 34 for first-time buyer pipeline, 35 to 54 for family second steppers, 65 plus for downsizers.
- Addressable scale. Population and household counts inside the catchment, weighted by the proportion of the area inside the drive-time zone.
- Household type. Family composition matching the bed range and product mix.

Weights are configurable per project because a 2 to 5 bed family development and a downsizer-focused scheme prioritise different signals. The scoring config is stored with the catchment so any ranking is reproducible and explainable. Every area's deep-dive shows why it scored as it did.

---

## 9. Battlecard output specification

Derived from the Abbots Vale reference. Three surfaces share one payload.

Page 1, visual summary:
- Header: development name, town, postcode, strapline and lifestyle pillars.
- Key statistics block: bed range, average household income, owner-occupied percentage, price from, median age, population catchment.
- Target audience and messaging: primary, secondary, tertiary audiences with message lines.
- The development and location: feature bullets.
- Three charts: age demographics (banded bar), household income (bar plus mean, median, lowest LA, highest LA callouts), housing tenure (donut: owns outright, owns with mortgage, social rented, private rented).
- Catchment map panel and developer logo.

Page 2, audience messaging overview and demographic commentary. Prose blocks per audience tier with channels and message lines, plus demographic commentary by age cohort.

Page 3, household income commentary and tenure commentary. Prose blocks interpreting the income profile and tenure mix with positioning implications.

Brand theming is per client. The app shell uses the Mediaworks and Apple light or dark systems (see design-framework.md). Client-facing Battlecard exports carry the developer brand (Hopkins navy and gold, Tilia, and so on) via a theme config, not hard-coded.

---

## 10. Phasing

Phase 1, MVP. The end-to-end automated path for a single postcode or grid ref: geocode, isochrone, intersect, ONS join, scoring, interactive map with clickable ranked areas, in-app Battlecard deep-dive, PDF export. MSOA level. Residential use case (Tilia and Hopkins) as the proving ground.

Phase 2, outputs and polish. PPTX export to the client brand template, KML catchment layer export, templated commentary refinement, LA-level support for leisure use cases (PfP Leisure pattern).

Phase 3, scale and breadth. Scheduled ONS refresh pipeline. Expanded data layers (IMD deprivation, broadband coverage, transport access, planning data). LLM-assisted commentary behind a review gate.

Phase 4, productisation. White-labelled client-facing portal delivering outputs directly to client teams. Sector templates for retail site selection, health service planning, local authority communications and public consultation, since the methodology is geography-agnostic and sector-flexible.

---

## 11. Dependencies, risks and open questions

Dependencies:
- ONS Census 2021, income estimates, boundary GeoJSON, geography lookups. Open.
- OS CodePoint Open, OS Transformation API for grid refs.
- Isochrone provider (TravelTime or OpenRouteService).
- GWI personas with channel preferences. Confirm licence terms for embedding persona-driven channel guidance in client outputs.

Risks:
- Isochrone free-tier rate limits may not survive batch use. Mitigation: cache aggressively by coordinate and parameters, evaluate paid tier cost in Phase 1.
- Edge clipping. Areas partly inside the catchment need a sensible overlap threshold or results get noisy. Mitigation: configurable threshold plus proportion weighting.
- Commentary quality at scale. Templated commentary risks reading generic across many areas. Mitigation: signal-driven templates first, optional LLM refinement with human review in Phase 3.
- ONS small-area suppression and rounding. Some MSOA cells are suppressed or rounded. Mitigation: handle nulls explicitly, surface confidence in the deep-dive.

Open questions for Dan:
- Working name and final branding for the engine. Resolved: working name is LandLynk.
- MSOA only for MVP, or LA from day one given the PfP Leisure use case.
- Isochrone provider preference (TravelTime vs OpenRouteService) and whether a paid tier is acceptable. Provisional: OpenRouteService hosted free tier for MVP, behind a pluggable provider seam so we can move to self-hosted ORS or Valhalla for scale without changing the pipeline. Revisit if the free-tier quota constrains batch use.
- Whether PPTX export to client brand templates is MVP or Phase 2.
- Whether the GWI persona layer is in MVP scoring or added later.

---

## 12. Success criteria

- Catchment definition drops from a 15 to 30 minute manual task to a sub-second automated lookup.
- A user can go from a postcode or grid ref to a ranked, clickable catchment map with per-area deep-dives in a single session, no GIS expertise required.
- Generated Battlecards match the Abbots Vale reference for completeness and presentation quality.
- Every priority ranking is reproducible and explainable from stored config and data.
- Outputs are refreshable when ONS publishes new releases, with versioned, auditable reference data.
