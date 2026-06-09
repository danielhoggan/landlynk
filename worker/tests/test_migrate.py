"""The bundled migrations are discoverable by the runner.

The actual apply needs a database and is exercised on deploy (Railway
pre-deploy command); here we assert the SQL ships with the package and is found,
so a deploy will not fail to locate it.
"""

from __future__ import annotations

from landlynk_worker.migrate import MIGRATIONS_DIR


def test_migrations_dir_ships_with_the_package():
    assert MIGRATIONS_DIR.is_dir()
    names = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))
    assert names == [
        "0001_init.sql",
        "0002_isochrone_cache.sql",
        "0003_house_prices.sql",
        "0004_reference_loads.sql",
        "0005_users_sharing_archive.sql",
        "0006_ai_enrichment.sql",
        "0007_builder_profiles.sql",
        "0008_llm_usage.sql",
    ]


def test_first_migration_enables_postgis():
    sql = (MIGRATIONS_DIR / "0001_init.sql").read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
    assert "CREATE TABLE IF NOT EXISTS catchment" in sql
