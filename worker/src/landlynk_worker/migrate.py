"""Apply database migrations, idempotently, from within the worker image.

Runs as a Railway pre-deploy command (`python -m landlynk_worker.migrate`) so the
schema is created and kept current automatically on every deploy. The migration
SQL ships in the worker image under ``worker/migrations`` and is the single
source of truth for the schema (house-standards.md: no schema changes outside
migrations).

Each .sql file is applied in filename order, recorded in schema_migrations, and
skipped if already applied. The connection uses autocommit so each file controls
its own transaction via the BEGIN/COMMIT it contains.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .config import settings

if TYPE_CHECKING:
    import psycopg

# worker/src/landlynk_worker/migrate.py -> parents[2] == worker/ ; the same
# resolution holds in the image (/app/src/landlynk_worker -> /app/migrations).
MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _applied(conn: psycopg.Connection) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    return {row[0] for row in conn.execute("SELECT filename FROM schema_migrations")}


def run(database_url: str | None = None) -> int:
    import psycopg

    url = database_url or settings.database_url
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print(f"No migrations found in {MIGRATIONS_DIR}", file=sys.stderr)
        return 0

    with psycopg.connect(url, autocommit=True) as conn:
        done = _applied(conn)
        pending = [f for f in sql_files if f.name not in done]
        if not pending:
            print("Database is up to date")
            return 0
        for path in pending:
            print(f"Applying {path.name}...")
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)", [path.name]
            )
        print(f"Applied {len(pending)} migration(s)")
    return len(pending)


if __name__ == "__main__":
    run()
