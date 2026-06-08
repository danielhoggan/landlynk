# infra

Railway and deploy configuration plus database migrations for landlynk.

## Services

The web app and the Python worker run as separate Railway services
(house-standards.md). A PostGIS database backs both.

- `web` - Next.js app. Build and start from `/web`.
- `worker` - Python FastAPI worker. Build and start from `/worker`.
- PostGIS database - use a PostGIS image (e.g. a Railway PostGIS template or the
  `postgis/postgis` Docker image). Railway's plain managed Postgres does not have
  the PostGIS extension and will fail the first migration.

### Critical: per-service Root Directory and config

Railway reads `railway.json` from each service's **Root Directory**, not from a
central file. For this monorepo you must, in the Railway dashboard, set the
Root Directory of each service:

- `worker` service Root Directory = `worker` (uses `worker/railway.json` and
  `worker/Dockerfile`).
- `web` service Root Directory = `web` (uses `web/railway.json` and
  `web/Dockerfile`).

Without the Root Directory set, Railway's builder analyses the repo root, finds
no single app and the build fails. Each `railway.json` pins the Dockerfile
builder and a health check.

## Secrets

All secrets are Railway environment variables, never committed. See
`web/.env.example` and the worker settings (`WORKER_` prefixed env vars) for the
required keys: Azure AD SSO credentials, the isochrone provider API key and the
database URL.

## Migrations

The schema lives in `worker/migrations/` and is bundled into the worker image.
The worker applies it automatically on every deploy via its Railway pre-deploy
command (`python -m landlynk_worker.migrate`, set in `worker/railway.json`),
idempotently. The first migration enables PostGIS. No manual step is required;
to run by hand, from `worker/` with `WORKER_DATABASE_URL` set run
`python -m landlynk_worker.migrate`.

## Layout

```
worker/railway.json     worker build (Dockerfile), pre-deploy migrate, health check
web/railway.json        web build (Dockerfile) and health check
worker/migrations/      versioned SQL migrations (bundled into the worker image)
infra/                  this readme
```
