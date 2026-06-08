# migrations

Versioned, checked-in SQL migrations for the landlynk Postgres database. No
schema changes happen outside migrations (house-standards.md).

## Convention

- Files are numbered and named: `NNNN_short_description.sql`.
- Each migration is wrapped in a single transaction.
- Migrations are forward-only and never edited once merged. To change schema,
  add a new migration.

## Applying

Apply in order against the target database. For example:

```bash
psql "$DATABASE_URL" -f migrations/0001_init.sql
```

PostGIS must be available on the instance. `0001_init.sql` enables the extension.

## Migrations

- `0001_init.sql` - PostGIS extension, reference tables (geo lookup and
  boundaries, census demographics and tenure, income estimates, postcode lookup,
  GWI personas), working tables (catchment, catchment_area, battlecard) and the
  reference_load provenance table.
