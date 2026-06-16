# house-standards.md

Mediaworks engineering and output standards for this build. Binding. If a standard blocks the right thing, flag it rather than quietly breaking it.

## Stack and versions

- Next.js with the App Router. Tailwind CSS v3. Inter font for app UI.
- next-auth v4 with Azure AD SSO. SSO is the only auth path. Do not add a local password flow.
- Python for the worker. Pin dependencies. GeoPandas and Shapely for geometry, plus the chosen isochrone client.
- Postgres with PostGIS. Migrations are versioned and checked in. No schema changes outside migrations.
- Railway hosting. Web app and Python worker as separate services. Secrets via Railway environment variables, never in the repo.
- lucide-react for icons in the app UI.

## Repository layout

```
/CLAUDE.md
/PROJECT_CONTEXT.md
/SCOPING.md
/house-standards.md
/design-framework.md
/web        Next.js app (UI, API route handlers)
/worker     Python geospatial and data worker
/data       reference data loaders and seed definitions (ONS, OS, GWI)
/infra      Railway and deploy config, migrations
```

## Code conventions

- TypeScript in the web app. No implicit any. Types for the Battlecard payload live in one shared module and are the contract between worker output and UI render.
- Python: type hints on public functions, black formatting, ruff lint.
- Names say what they mean. catchment, catchment_area, battlecard match the data model in SCOPING.md Section 6.
- Pure functions for scoring and profiling. They take data in and return scores out, with no side effects, so they are testable and reproducible.
- Comments explain why, not what. The code says what.

## Testing

- Scoring logic: unit tested. Given a known area profile and config, the score and rank are deterministic and asserted.
- Spatial intersect: tested against fixture geometries with known overlaps.
- Battlecard payload: schema-validated so all four render surfaces can trust it.
- Do not ship scoring or intersect changes without tests.

## Data handling

- All reference data is open or free tier. No third-party data licences. Adding any paid source needs sign-off.
- Reference data loads through a versioned loader. Each load records source, version and date so refreshes are auditable.
- ONS suppression and rounding are handled explicitly. A suppressed cell is null, not zero. Surface data confidence in the deep-dive rather than hiding gaps.
- Isochrone results are cached by coordinate and parameters. Re-runs must not re-bill the provider.
- No personal or sensitive data in URLs, query strings or logs.

## Output and document conventions

These are firm standing Mediaworks conventions and apply to everything user-facing the build produces: generated commentary, Battlecards, exported documents and reports.

- Font: Tenorite for documents (Word, PDF, decks). Tenor Sans for HTML and web outputs, as the web-safe equivalent.
- Document headings: LandLynk green #2F6B3A, where a client brand does not override.
- No em dashes. Use a spaced hyphen or restructure the sentence.
- No Oxford commas.
- No markdown headers in generated prose deliverables.
- Client-facing Battlecards carry the client or developer brand (Hopkins, Tilia and so on) through a theme config. Brand colours are never hard-coded into the render logic.

These conventions do not apply to source code, config or the control files, which use normal code and markdown idioms.

## Security and access

- Azure AD SSO gate stays intact on every route that touches data or generates output.
- Secrets in Railway environment variables only.
- No credentials, keys or tokens committed, logged or placed in client code.
- Do not modify access controls or sharing on any resource without an explicit instruction.

## Working method

- Plan, then build. State the files you will touch for any non-trivial change.
- Match existing patterns before adding new ones.
- Small commits, one concern each.
- If a request conflicts with SCOPING.md or these standards, raise it before acting.
