# infra

Railway and deploy configuration plus database migrations for landlynk.

## Services

The web app and the Python worker run as separate Railway services
(house-standards.md). A Postgres with PostGIS instance backs both.

- `web` - Next.js app. Build and start from `/web`.
- `worker` - Python FastAPI worker. Build and start from `/worker`.
- Postgres with PostGIS - managed database. Apply `migrations/` in order.

## Secrets

All secrets are Railway environment variables, never committed. See
`web/.env.example` and the worker settings (`WORKER_` prefixed env vars) for the
required keys: Azure AD SSO credentials, the isochrone provider API key and the
database URL.

## Migrations

See `migrations/README.md`. PostGIS is required; the first migration enables it.

## Layout

```
infra/
  railway.json        service and build configuration
  migrations/         versioned SQL migrations
```
