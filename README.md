# landlynk

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

Phase 1 (MVP) scaffold. MSOA level, residential use case. See SCOPING.md Section 10
for phasing. Each subdirectory has its own README with setup detail.
