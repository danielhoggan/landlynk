"""Reference data reads for the pipeline.

Defines the ``ReferenceData`` protocol the orchestrator depends on, plus a
Postgres implementation backed by the loaded reference tables and PostGIS. The
protocol lets the orchestration be unit tested with an in-memory fake, while
production reads from the database.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from ..scoring.profile import AreaProfile
from .intersect import AreaGeometry, area_geometry_from_geojson
from .join import build_area_profile

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool


@dataclass(frozen=True)
class AreaReference:
    """An area's profile plus its display name, ready for scoring and assembly."""

    profile: AreaProfile
    name: str


class ReferenceData(Protocol):
    def candidate_area_geometries(
        self, isochrone: dict, area_type: str
    ) -> list[AreaGeometry]:
        """Areas whose geometry intersects the isochrone bounding region."""
        ...

    def area_reference(
        self, area_code: str, area_type: str, proportion_inside: float
    ) -> AreaReference:
        """Build the profile and name for one area from the reference tables."""
        ...


class PostgresReferenceData:
    """Reads boundaries and reference tables from Postgres with PostGIS.

    Spatial candidate selection is delegated to PostGIS (ST_Intersects against a
    GiST index), which is far faster than scanning every boundary. The fine
    proportion-inside calculation then runs in the tested shapely intersect.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        # Connection pool, owned by the caller. Reusing pooled connections
        # avoids opening a new connection per query.
        self._pool = pool

    def candidate_area_geometries(
        self, isochrone: dict, area_type: str
    ) -> list[AreaGeometry]:
        sql = (
            "SELECT area_code, area_type, ST_AsGeoJSON(geom) "
            "FROM geo_boundaries "
            "WHERE area_type = %s "
            "AND ST_Intersects(geom, ST_GeomFromGeoJSON(%s))"
        )
        geojson = json.dumps(isochrone)
        out: list[AreaGeometry] = []
        with self._pool.connection() as conn:
            for area_code, a_type, geom_json in conn.execute(sql, [area_type, geojson]):
                out.append(
                    area_geometry_from_geojson(area_code, a_type, json.loads(geom_json))
                )
        return out

    def area_reference(
        self, area_code: str, area_type: str, proportion_inside: float
    ) -> AreaReference:
        # One pooled connection serves all reads for the area.
        with self._pool.connection() as conn:
            demographics = _one(conn, "census_demographics", area_code)
            tenure = _one(conn, "census_tenure", area_code)
            income = _one(conn, "income_estimates", area_code)
            name = _area_name(conn, area_code)
        profile = build_area_profile(
            area_code=area_code,
            area_type=area_type,
            proportion_inside=proportion_inside,
            demographics_row=demographics,
            tenure_row=tenure,
            income_row=income,
        )
        return AreaReference(profile=profile, name=name or area_code)


def _one(conn, table: str, area_code: str) -> dict:  # pragma: no cover - needs DB
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT * FROM {table} WHERE area_code = %s", [area_code])
        return cur.fetchone() or {}


def _area_name(conn, area_code: str) -> str | None:  # pragma: no cover - needs DB
    row = conn.execute(
        "SELECT area_name FROM geo_boundaries WHERE area_code = %s", [area_code]
    ).fetchone()
    return row[0] if row else None
