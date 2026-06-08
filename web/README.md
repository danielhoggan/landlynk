# web

The Next.js front end for landlynk: the interactive catchment map, area ranking,
Battlecard drawer and export controls. Thin API route handlers submit jobs to
the Python worker and read results. No heavy geospatial work runs here.

## Stack

- Next.js (App Router), TypeScript, Tailwind CSS v3.
- next-auth v4 with Azure AD SSO. SSO is the only auth path.
- lucide-react icons. Inter for app UI, Tenor Sans for web outputs.
- MapLibre GL for the open-source map (no licensed tiles).

## Setup

```bash
cd web
npm install
cp .env.example .env.local   # fill in Azure AD and worker URL
npm run dev
```

## Scripts

- `npm run dev` - local dev server.
- `npm run build` - production build.
- `npm run lint` - eslint.
- `npm run typecheck` - tsc with no emit.

## Layout

```
src/
  app/                      App Router pages and API route handlers
    api/auth/[...nextauth]  next-auth Azure AD handler
    api/catchments/...      thin job submission and read endpoints
  components/
    shell/                  Mediaworks/Apple app shell (top bar, drawer, tabs, theme)
    map/                    catchment map (MapLibre seam)
    battlecard/             on-location summary, deep-dive drawer, score explainer
  lib/
    types/                  the Battlecard payload and catchment contracts
    theme/                  client brand themes for exports
```

## Key contracts

`src/lib/types/battlecard.ts` is the single source of truth for one area's
output and renders to four surfaces. It must stay in sync with the worker's
pydantic models and the shared JSON schema.
