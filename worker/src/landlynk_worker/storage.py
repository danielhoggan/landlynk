"""Persistence for catchments, areas and Battlecards.

Results are written to Postgres so they survive worker restarts and are shared
across worker instances (SCOPING.md 5.2: on area click the app serves stored
data, no recompute). A ``Storage`` protocol lets the HTTP layer stay agnostic;
``InMemoryStore`` backs the unit tests and local dev, ``PostgresStore`` is the
durable production store.

The read serialisers shape stored data into the web Catchment contract
(web/src/lib/types/catchment.ts) and the Battlecard payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from .pipeline.orchestrate import CatchmentResult
from .scoring.profile import ScoringConfig
from .scoring.score import band_for_score

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool


@dataclass
class JobInput:
    kind: str
    value: str
    development_name: str


def scoring_config_to_dict(config: ScoringConfig) -> dict:
    """Serialise the scoring config stored with a catchment for reproducibility."""
    return {
        "weights": config.weights,
        "priceBand": {"from": config.price_band.frm, "to": config.price_band.to},
        "bedRange": config.bed_range,
        "overlapThreshold": config.overlap_threshold,
        "driveTimeMinutes": config.drive_time_minutes,
        "affordabilityMultiple": config.affordability_multiple,
        "tenurePreference": config.tenure_preference,
        "agePreference": config.age_preference,
        "scaleSaturation": config.scale_saturation,
    }


def _serialise_areas_from_result(result: CatchmentResult) -> list[dict]:
    return [
        {
            "areaCode": a.area_code,
            "areaType": a.area_type,
            "name": a.name,
            "proportionInside": round(a.proportion_inside, 4),
            "score": round(a.score.total, 4),
            "band": a.score.band,
            "rank": a.rank,
            "geometry": a.geometry,
        }
        for a in result.areas
    ]


class Storage(Protocol):
    def create_job(
        self, catchment_id: str, job: JobInput, config: ScoringConfig, created_by: str
    ) -> None: ...
    def mark_status(
        self, catchment_id: str, status: str, error: str | None = None
    ) -> None: ...
    def save_result(
        self, catchment_id: str, result: CatchmentResult, config: ScoringConfig
    ) -> None: ...
    def get_catchment(self, catchment_id: str) -> dict | None: ...
    def get_battlecard(self, catchment_id: str, area_code: str) -> dict | None: ...
    def list_catchments(self, limit: int = 100) -> list[dict]: ...


@dataclass
class _MemRecord:
    job: JobInput
    status: str = "queued"
    error: str | None = None
    result: CatchmentResult | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class InMemoryStore:
    """Process-local store for tests and single-process dev."""

    def __init__(self) -> None:
        self._records: dict[str, _MemRecord] = {}

    def create_job(
        self, catchment_id: str, job: JobInput, config: ScoringConfig, created_by: str
    ) -> None:
        self._records[catchment_id] = _MemRecord(job=job)

    def mark_status(
        self, catchment_id: str, status: str, error: str | None = None
    ) -> None:
        record = self._records[catchment_id]
        record.status = status
        record.error = error

    def save_result(
        self, catchment_id: str, result: CatchmentResult, config: ScoringConfig
    ) -> None:
        record = self._records[catchment_id]
        record.result = result
        record.status = "complete"

    def get_catchment(self, catchment_id: str) -> dict | None:
        record = self._records.get(catchment_id)
        if record is None:
            return None
        result = record.result
        return {
            "id": catchment_id,
            "input": {
                "kind": record.job.kind,
                "value": record.job.value,
                "developmentName": record.job.development_name,
            },
            "coordinate": (
                None
                if result is None
                else {"lat": result.coordinate.lat, "lng": result.coordinate.lng}
            ),
            "isochrone": None if result is None else result.isochrone,
            "status": record.status,
            "areas": [] if result is None else _serialise_areas_from_result(result),
            "error": record.error,
        }

    def get_battlecard(self, catchment_id: str, area_code: str) -> dict | None:
        record = self._records.get(catchment_id)
        if record is None or record.result is None:
            return None
        card = record.result.battlecards.get(area_code)
        return None if card is None else card.model_dump(by_alias=True)

    def list_catchments(self, limit: int = 100) -> list[dict]:
        items = [
            {
                "id": cid,
                "developmentName": r.job.development_name,
                "inputValue": r.job.value,
                "status": r.status,
                "areaCount": len(r.result.areas) if r.result else 0,
                "createdAt": r.created_at,
            }
            for cid, r in self._records.items()
        ]
        items.sort(key=lambda i: i["createdAt"], reverse=True)
        return items[:limit]


class PostgresStore:
    """Durable store backed by Postgres with PostGIS.

    Coordinates and isochrone polygons are written as geometry; area geometry is
    not duplicated here, it is read back from geo_boundaries on demand. Cannot be
    exercised in the offline unit tests; InMemoryStore covers the serialisation
    contract.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def create_job(
        self, catchment_id: str, job: JobInput, config: ScoringConfig, created_by: str
    ) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO catchment "
                "(id, input_kind, input_value, development_name, config, status, created_by) "
                "VALUES (%s, %s, %s, %s, %s, 'queued', %s)",
                [
                    catchment_id,
                    job.kind,
                    job.value,
                    job.development_name,
                    json.dumps(scoring_config_to_dict(config)),
                    created_by,
                ],
            )

    def mark_status(
        self, catchment_id: str, status: str, error: str | None = None
    ) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE catchment SET status = %s, error = %s WHERE id = %s",
                [status, error, catchment_id],
            )

    def save_result(
        self, catchment_id: str, result: CatchmentResult, config: ScoringConfig
    ) -> None:
        with self._pool.connection() as conn, conn.transaction():
            conn.execute(
                "UPDATE catchment SET "
                "coordinate = ST_SetSRID(ST_MakePoint(%s, %s), 4326), "
                "isochrone = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), "
                "status = 'complete' WHERE id = %s",
                [
                    result.coordinate.lng,
                    result.coordinate.lat,
                    json.dumps(result.isochrone),
                    catchment_id,
                ],
            )
            conn.execute(
                "DELETE FROM catchment_area WHERE catchment_id = %s", [catchment_id]
            )
            conn.execute(
                "DELETE FROM battlecard WHERE catchment_id = %s", [catchment_id]
            )
            for area in result.areas:
                conn.execute(
                    "INSERT INTO catchment_area "
                    "(catchment_id, area_code, area_type, proportion_inside, priority_score, rank) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    [
                        catchment_id,
                        area.area_code,
                        area.area_type,
                        area.proportion_inside,
                        area.score.total,
                        area.rank,
                    ],
                )
                card = result.battlecards[area.area_code]
                conn.execute(
                    "INSERT INTO battlecard "
                    "(catchment_id, area_code, schema_version, payload) "
                    "VALUES (%s, %s, %s, %s)",
                    [
                        catchment_id,
                        area.area_code,
                        card.schema_version,
                        json.dumps(card.model_dump(by_alias=True)),
                    ],
                )

    def get_catchment(self, catchment_id: str) -> dict | None:
        with self._pool.connection() as conn:
            head = conn.execute(
                "SELECT input_kind, input_value, development_name, status, error, "
                "ST_X(coordinate) AS lng, ST_Y(coordinate) AS lat, "
                "ST_AsGeoJSON(isochrone) AS isochrone "
                "FROM catchment WHERE id = %s",
                [catchment_id],
            ).fetchone()
            if head is None:
                return None
            kind, value, dev_name, status, error, lng, lat, isochrone = head

            area_rows = conn.execute(
                "SELECT ca.area_code, ca.area_type, gb.area_name, "
                "ca.proportion_inside, ca.priority_score, ca.rank, "
                "ST_AsGeoJSON(gb.geom) AS geom "
                "FROM catchment_area ca "
                "LEFT JOIN geo_boundaries gb ON gb.area_code = ca.area_code "
                "WHERE ca.catchment_id = %s ORDER BY ca.rank",
                [catchment_id],
            ).fetchall()

        areas = [
            {
                "areaCode": code,
                "areaType": a_type,
                "name": name or code,
                "proportionInside": float(prop),
                "score": float(score),
                "band": band_for_score(float(score)),
                "rank": rank,
                "geometry": json.loads(geom) if geom else None,
            }
            for (code, a_type, name, prop, score, rank, geom) in area_rows
        ]
        return {
            "id": catchment_id,
            "input": {"kind": kind, "value": value, "developmentName": dev_name},
            "coordinate": None if lat is None else {"lat": lat, "lng": lng},
            "isochrone": json.loads(isochrone) if isochrone else None,
            "status": status,
            "areas": areas,
            "error": error,
        }

    def get_battlecard(self, catchment_id: str, area_code: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT payload FROM battlecard WHERE catchment_id = %s AND area_code = %s",
                [catchment_id, area_code],
            ).fetchone()
        return row[0] if row else None

    def list_catchments(self, limit: int = 100) -> list[dict]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT c.id, c.development_name, c.input_value, c.status, "
                "c.created_at, count(ca.area_code) AS area_count "
                "FROM catchment c "
                "LEFT JOIN catchment_area ca ON ca.catchment_id = c.id "
                "GROUP BY c.id ORDER BY c.created_at DESC LIMIT %s",
                [limit],
            ).fetchall()
        return [
            {
                "id": str(cid),
                "developmentName": dev_name,
                "inputValue": value,
                "status": status,
                "areaCount": area_count,
                "createdAt": created_at.isoformat() if created_at else None,
            }
            for (cid, dev_name, value, status, created_at, area_count) in rows
        ]
