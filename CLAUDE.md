# CLAUDE.md

Operating contract for Claude Code on this repository. Read this first, then PROJECT_CONTEXT.md, then house-standards.md and design-framework.md before writing code.

## What this is

The Geographic Intelligence Engine. A platform that turns a development postcode or OS grid reference into a ranked, clickable catchment map with auto-generated Battlecards and deep-dive analysis per area. Full product definition is in SCOPING.md. Domain background is in PROJECT_CONTEXT.md.

## Control files

This repo uses the standard Mediaworks four-file control pattern. Keep them current as the source of truth.

- CLAUDE.md (this file). How to work in the repo.
- PROJECT_CONTEXT.md. What we are building and why. Domain and product context.
- house-standards.md. Engineering standards, stack versions, output and document conventions.
- design-framework.md. UI and output design system.

SCOPING.md is the scoping document and sits alongside these. If a change contradicts SCOPING.md, stop and flag it rather than drifting.

## Tech stack (do not substitute without sign-off)

- Front end: Next.js, Tailwind CSS v3, next-auth v4 with Azure AD SSO. Inter font for the app UI.
- Worker: Python for all geospatial and data processing (GeoPandas, Shapely, PostGIS queries, isochrone calls, output generation).
- Database: Postgres with PostGIS. pgvector only if persona semantic matching is added later.
- Hosting: Railway. Web app and Python worker as separate services.
- Map: open-source web mapping (MapLibre GL or Leaflet). No licensed map tiles or data.

Full version pinning and rationale in house-standards.md. Do not introduce a different framework, ORM, auth library or paid data source without explicit approval.

## Architecture rules

- Heavy work runs in the Python worker, never in a Next.js API request cycle. Geocode, isochrone, spatial intersect, scoring and output generation are all worker jobs.
- API route handlers are thin: auth, job submission, reads, serving outputs.
- One Battlecard payload per area is the single source of truth. It renders to four surfaces (web drawer, PDF, PPTX, KML balloon). Never fork the data per surface.
- All external data sources must be open or free tier. No third-party data licences. Flag it before adding any paid source.
- Reference data (ONS, OS, GWI) is loaded via a versioned, auditable loader. Never hand-edit reference tables.

## How to work here

- Plan before building. For any non-trivial change, state the plan and the files you will touch, then proceed.
- Match existing patterns. Read neighbouring code before adding new code. Consistency beats cleverness.
- Small, reviewable commits. One concern per commit.
- Tests for the scoring logic and the spatial intersect are not optional. These are the parts that must be reproducible and explainable.
- Cache isochrone calls by coordinate and parameters. Re-runs must not re-bill the provider.
- Handle ONS suppression and nulls explicitly. Never silently coerce a suppressed cell to zero.

## Output and prose conventions

These apply to anything user-facing or document-like the build produces (generated commentary, exports, reports), not to source code.

- Font: Tenorite for documents. Tenor Sans for HTML and web outputs.
- Headings in generated documents: Royal Blue #4169E1.
- No em dashes. No Oxford commas. No markdown headers in generated prose deliverables.

Code files, config and these control files use normal markdown and code conventions.

## Guardrails

- Do not commit secrets, API keys or tokens. Use Railway environment variables.
- Do not store personal or sensitive data in URLs or query strings.
- Do not weaken the Azure AD SSO gate.
- Do not add an external dependency, change the stack or alter the scoring weights default without flagging it.
- If a request conflicts with SCOPING.md or these standards, surface the conflict and ask before proceeding.
