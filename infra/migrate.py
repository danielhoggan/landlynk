"""Apply database migrations in order, idempotently.

Reads the .sql files in infra/migrations and applies any not yet recorded in the
schema_migrations table, each in its own transaction, in filename order.
Migrations are forward-only (house-standards.md).

Usage:
    DATABASE_URL=postgresql://... python infra/migrate.py

Run this once after provisioning the database and again after each deploy that
adds a migration. Needs psycopg (pip install "psycopg[binary]").
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def applied_migrations(conn: psycopg.Connection) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    rows = conn.execute("SELECT filename FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Set DATABASE_URL", file=sys.stderr)
        return 1

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        print("No migrations found")
        return 0

    # Autocommit so each migration file controls its own transaction via the
    # BEGIN/COMMIT it contains; the runner records each applied file separately.
    with psycopg.connect(database_url, autocommit=True) as conn:
        done = applied_migrations(conn)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
