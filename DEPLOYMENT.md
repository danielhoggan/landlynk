# Deployment runbook

How to stand LandLynk up on Railway with Azure AD SSO. Pairs with the action
checklists in TODO_DAN.md (your tasks) and TODO_CLAUDE.md (build tasks).

## Architecture recap

Three Railway services plus a database:

- `web` - Next.js app, built from `web/Dockerfile`. The user-facing UI and the
  thin API routes. Behind Azure AD SSO.
- `worker` - Python FastAPI service, built from `worker/Dockerfile`. Runs the
  geocode, isochrone, intersect, score, assemble pipeline and serves results.
- Postgres with PostGIS - managed database plugin, backs both.

The web app never talks to the database directly. It proxies to the worker via
`WORKER_BASE_URL`; the worker owns all data access.

## 1. Database

PostGIS is required. Railway's plain managed Postgres does NOT ship the PostGIS
extension (`CREATE EXTENSION postgis` fails with "not available"), so use a
PostGIS image, not the vanilla Postgres plugin.

1. Deploy a PostGIS database. Easiest is a Railway PostGIS template, or deploy
   the `postgis/postgis` Docker image as a service with a volume mounted at
   `/var/lib/postgresql/data` and `PGDATA=/var/lib/postgresql/data/pgdata`.
2. Point the worker's `WORKER_DATABASE_URL` at it (use the private
   `*.railway.internal` host for the worker).
3. Migrations run automatically. The worker's Railway pre-deploy command
   (`python -m landlynk_worker.migrate`, set in `worker/railway.json`) applies
   `worker/migrations/*.sql` in order on every deploy, idempotently, and the
   first migration enables PostGIS. No manual step is needed.

To run migrations by hand against a database (optional), from `worker/` with
`WORKER_DATABASE_URL` set: `python -m landlynk_worker.migrate`.

## 2. Reference data

Load the open reference data once (and on each ONS refresh). See `data/README.md`
for the exact commands. Summary, run from `data/` with `DATABASE_URL` set:

```
python -m loaders.run geo_boundaries --source MSOA_2021.geojson --area-type MSOA
python -m loaders.run geo_lookup --source OA_to_MSOA_to_LAD.csv
python -m loaders.run census_demographics --source age.csv --households-source households.csv
python -m loaders.run census_tenure --source tenure.csv
python -m loaders.run income_estimates --source msoa_income.xlsx
python -m loaders.run postcode_lookup --source codepoint_open.csv
```

## 3. Worker service

In the Railway service settings, set **Root Directory = `worker`**. This is
required: Railway reads `worker/railway.json` and `worker/Dockerfile` from there.
Without it the builder analyses the repo root and fails. `worker/railway.json`
already pins the Dockerfile builder and the `/health` check.

Environment variables (all prefixed `WORKER_`):

| Variable | Required | Notes |
|---|---|---|
| `WORKER_DATABASE_URL` | yes | Postgres with PostGIS connection string |
| `WORKER_ISOCHRONE_API_KEY` | yes | OpenRouteService API key (free tier) |
| `WORKER_ISOCHRONE_PROVIDER` | no | defaults to `openrouteservice` |
| `WORKER_ISOCHRONE_BASE_URL` | no | set to a self-hosted ORS or Valhalla URL |
| `WORKER_PERSIST_RESULTS` | no | defaults to `true` |
| `WORKER_DEFAULT_DRIVE_TIME_MINUTES` | no | defaults to `30` |

Health check: `GET /health`.

## 4. Web service

In the Railway service settings, set **Root Directory = `web`**. Railway then
reads `web/railway.json` and `web/Dockerfile`. `web/railway.json` pins the
Dockerfile builder and the `/signin` health check.

Environment variables:

| Variable | Required | Notes |
|---|---|---|
| `NEXTAUTH_URL` | yes | the public web URL, e.g. `https://landlynk.up.railway.app` |
| `NEXTAUTH_SECRET` | yes | `openssl rand -base64 32` |
| `AZURE_AD_CLIENT_ID` | yes | from the Azure App Registration |
| `AZURE_AD_CLIENT_SECRET` | yes | from the Azure App Registration |
| `AZURE_AD_TENANT_ID` | yes | the Mediaworks tenant id |
| `WORKER_BASE_URL` | yes | the worker service internal URL |

The web app does not need `DATABASE_URL`.

## 5. Azure App Registration

1. Register an application in Entra ID (Azure AD).
2. Add a Web redirect URI: `${NEXTAUTH_URL}/api/auth/callback/azure-ad`.
3. Create a client secret. Copy the id, secret and tenant id into the web env.
4. Grant the default delegated `User.Read` permission (sign-in and profile).

## 6. Smoke test

1. Visit the web URL. You should be redirected to `/signin` and through Azure AD.
2. Paste a Suffolk postcode (or grid ref), submit, and watch the status move
   through to complete.
3. The map should render the isochrone and ranked areas. Click an area for the
   deep-dive, and export the PDF.

If the worker logs a geocode or isochrone error, check the ORS key and that the
reference data loaded. If the map is empty, the boundaries table is likely not
loaded for the area type requested.
