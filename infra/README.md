# infra

Railway and deploy configuration plus database migrations for landlynk.

## Services

The web app and the Python worker run as separate Railway services
(house-standards.md). A Postgres with PostGIS instance backs both.

- `web` - Next.js app. Build and start from `/web`.
- `worker` - Python FastAPI worker. Build and start from `/worker`.
- Postgres with PostGIS - managed database. Apply `migrations/` in order.

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

See `migrations/README.md`. PostGIS is required; the first migration enables it.

## Layout

```
worker/railway.json   worker service build (Dockerfile) and health check
web/railway.json      web service build (Dockerfile) and health check
infra/
  migrate.py          migration runner
  migrations/         versioned SQL migrations
```
