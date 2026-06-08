"""Postgres writer shared by every reference loader.

Each load replaces the target table and records provenance in reference_load in
one transaction, so a refresh is atomic and auditable. Geometry columns are
written from GeoJSON via PostGIS functions, declared per table.

This module needs a live Postgres with PostGIS. It is exercised when you run a
load, not in the pure transform unit tests.
"""

from __future__ import annotations

from typing import Any

import psycopg

# Columns that must be written through a PostGIS function rather than as a plain
# value. The placeholder %s receives the GeoJSON string for that column.
_GEOMETRY_SQL: dict[str, str] = {
    "geom_boundary": "ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))",
}


class ReferenceDB:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def replace_table(
        self,
        table: str,
        columns: tuple[str, ...],
        rows: list[dict],
        source: str,
        version: str,
        geometry_columns: dict[str, str] | None = None,
    ) -> int:
        """Truncate ``table`` and insert ``rows``, then record the load.

        ``geometry_columns`` maps a column name to the SQL expression that wraps
        its placeholder (for PostGIS geometry). All in one transaction.
        """
        geometry_columns = geometry_columns or {}
        col_list = ", ".join(columns)
        placeholders = ", ".join(geometry_columns.get(col, "%s") for col in columns)
        insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE {table}")
                for row in rows:
                    cur.execute(insert_sql, [row.get(col) for col in columns])
                cur.execute(
                    "INSERT INTO reference_load (table_name, source, source_version) "
                    "VALUES (%s, %s, %s)",
                    [table, source, version],
                )
            conn.commit()
        return len(rows)

    def execute(self, sql: str, params: list[Any] | None = None) -> None:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or [])
            conn.commit()
