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
from .scoring.score import relative_band

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool


@dataclass
class JobInput:
    kind: str
    value: str
    development_name: str


def _user_row(row: tuple) -> dict:
    return {
        "email": row[0],
        "name": row[1],
        "role": row[2],
        "builderGroupId": row[3] if len(row) > 3 else None,
    }


def _profile_row(row: tuple) -> dict:
    """Map a builder_profile row (first 10 columns) to the API shape."""
    return {
        "id": row[0],
        "builderId": row[1],
        "name": row[2],
        "segment": row[3],
        "bedRange": row[4],
        "priceFrom": float(row[5]) if row[5] is not None else None,
        "priceTo": float(row[6]) if row[6] is not None else None,
        "strapline": row[7],
        "pillars": row[8] or [],
        "features": row[9] or [],
    }


def scoring_config_to_dict(config: ScoringConfig) -> dict:
    """Serialise the scoring config stored with a catchment for reproducibility."""
    return {
        "weights": config.weights,
        "priceBand": {"from": config.price_band.frm, "to": config.price_band.to},
        "bedRange": config.bed_range,
        "overlapThreshold": config.overlap_threshold,
        "driveTimeMinutes": config.drive_time_minutes,
        "catchmentMode": config.catchment_mode,
        "radiusKm": config.radius_km,
        "segment": config.segment,
        "brandHeading": config.brand_heading,
        "affordabilityMultiple": config.affordability_multiple,
        "tenurePreference": config.tenure_preference,
        "agePreference": config.age_preference,
        "scaleSaturation": config.scale_saturation,
    }


def _area_metrics(payload: dict | None) -> dict | None:
    """Compact per-area metrics for map tooltips and client-side filtering.

    Pulled from the stored Battlecard payload so the catchment response carries
    enough to drive hover info and signal filters without fetching every card.
    """
    if not payload:
        return None
    vs = payload.get("visualSummary") or {}
    ks = vs.get("keyStatistics") or {}
    tenure = (vs.get("charts") or {}).get("housingTenure") or {}
    ctx = payload.get("catchmentContext") or {}

    def val(d: dict | None) -> float | None:
        return (d or {}).get("value")

    return {
        "income": val(ks.get("averageHouseholdIncome")),
        "housePrice": val(ks.get("medianHousePrice")),
        "ownerOccupied": val(ks.get("ownerOccupiedPercentage")),
        "medianAge": val(ks.get("medianAge")),
        "familyShare": val(ks.get("familyHouseholdShare")),
        "privateRented": val(tenure.get("privateRented")),
        "ownsOutright": val(tenure.get("ownsOutright")),
        "incomeIndex": val(ctx.get("incomeIndex")),
    }


def _serialise_areas_from_result(result: CatchmentResult) -> list[dict]:
    total = len(result.areas)
    return [
        {
            "areaCode": a.area_code,
            "areaType": a.area_type,
            "name": a.name,
            "proportionInside": round(a.proportion_inside, 4),
            "score": round(a.score.total, 4),
            "band": relative_band(a.rank, total),
            "rank": a.rank,
            "geometry": a.geometry,
            "metrics": _area_metrics(
                result.battlecards[a.area_code].model_dump(by_alias=True)
                if a.area_code in result.battlecards
                else None
            ),
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
    def list_catchments(
        self,
        viewer_email: str | None,
        is_admin: bool,
        archived: bool = False,
        limit: int = 100,
    ) -> list[dict]: ...
    def delete_catchment(self, catchment_id: str) -> bool: ...
    def get_owner(self, catchment_id: str) -> str | None: ...
    def can_access(
        self, catchment_id: str, viewer_email: str | None, is_admin: bool
    ) -> bool: ...
    def set_archived(self, catchment_id: str, archived: bool) -> bool: ...
    def add_shares(self, catchment_id: str, emails: list[str]) -> None: ...
    def remove_share(self, catchment_id: str, email: str) -> bool: ...
    def list_shares(self, catchment_id: str) -> list[str]: ...

    # User directory and per-account settings.
    def upsert_user(self, email: str, name: str | None, admin: bool) -> dict: ...
    def get_user(self, email: str) -> dict | None: ...
    def list_users(self) -> list[dict]: ...
    def set_role(self, email: str, role: str) -> bool: ...
    def set_user_group(self, email: str, group_id: str | None) -> bool: ...

    # Builder org model: groups, brands and saved targeting profiles.
    def create_builder_group(self, group_id: str, name: str) -> None: ...
    def list_builder_groups(self) -> list[dict]: ...
    def delete_builder_group(self, group_id: str) -> bool: ...
    def create_builder(
        self, builder_id: str, group_id: str, name: str, theme_heading: str
    ) -> None: ...
    def list_builders(self, group_id: str | None = None) -> list[dict]: ...
    def delete_builder(self, builder_id: str) -> bool: ...
    def upsert_builder_profile(self, profile: dict) -> None: ...
    def get_builder_profile(self, profile_id: str) -> dict | None: ...
    def delete_builder_profile(self, profile_id: str) -> bool: ...
    def list_builder_profiles(self, group_id: str | None = None) -> list[dict]: ...
    def get_settings(self, email: str) -> dict | None: ...
    def save_settings(self, email: str, settings: dict) -> None: ...

    # Global app config (e.g. the default AI model) and the area-profile cache.
    def get_config(self, key: str) -> dict | None: ...
    def set_config(self, key: str, value: dict) -> None: ...
    def get_area_profile(self, cache_key: str) -> dict | None: ...
    def save_area_profile(self, cache_key: str, model: str, payload: dict) -> None: ...


@dataclass
class _MemRecord:
    job: JobInput
    status: str = "queued"
    error: str | None = None
    result: CatchmentResult | None = None
    config: dict | None = None
    owner: str | None = None
    archived: bool = False
    shared_with: set[str] = field(default_factory=set)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def _summary(cid: str, r: _MemRecord, viewer_email: str | None) -> dict:
    return {
        "id": cid,
        "developmentName": r.job.development_name,
        "inputValue": r.job.value,
        "status": r.status,
        "areaCount": len(r.result.areas) if r.result else 0,
        "createdAt": r.created_at,
        "owner": r.owner,
        "shared": bool(r.owner and viewer_email and r.owner != viewer_email),
        "archived": r.archived,
    }


class InMemoryStore:
    """Process-local store for tests and single-process dev."""

    def __init__(self) -> None:
        self._records: dict[str, _MemRecord] = {}
        self._users: dict[str, dict] = {}
        self._settings: dict[str, dict] = {}
        self._config: dict[str, dict] = {}
        self._area_profiles: dict[str, dict] = {}
        self._groups: dict[str, dict] = {}
        self._builders: dict[str, dict] = {}
        self._profiles: dict[str, dict] = {}

    def create_job(
        self, catchment_id: str, job: JobInput, config: ScoringConfig, created_by: str
    ) -> None:
        self._records[catchment_id] = _MemRecord(
            job=job,
            config=scoring_config_to_dict(config),
            owner=created_by if created_by != "system" else None,
        )

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
                "config": record.config,
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

    def _visible(self, r: _MemRecord, viewer_email: str | None, is_admin: bool) -> bool:
        if is_admin:
            return True
        if viewer_email is None:
            return False
        return r.owner == viewer_email or viewer_email in r.shared_with

    def list_catchments(
        self,
        viewer_email: str | None,
        is_admin: bool,
        archived: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        items = [
            _summary(cid, r, viewer_email)
            for cid, r in self._records.items()
            if r.archived == archived and self._visible(r, viewer_email, is_admin)
        ]
        items.sort(key=lambda i: i["createdAt"], reverse=True)
        return items[:limit]

    def delete_catchment(self, catchment_id: str) -> bool:
        return self._records.pop(catchment_id, None) is not None

    def get_owner(self, catchment_id: str) -> str | None:
        record = self._records.get(catchment_id)
        return record.owner if record else None

    def can_access(
        self, catchment_id: str, viewer_email: str | None, is_admin: bool
    ) -> bool:
        record = self._records.get(catchment_id)
        return record is not None and self._visible(record, viewer_email, is_admin)

    def set_archived(self, catchment_id: str, archived: bool) -> bool:
        record = self._records.get(catchment_id)
        if record is None:
            return False
        record.archived = archived
        return True

    def add_shares(self, catchment_id: str, emails: list[str]) -> None:
        record = self._records.get(catchment_id)
        if record is not None:
            record.shared_with.update(e.strip().lower() for e in emails if e.strip())

    def remove_share(self, catchment_id: str, email: str) -> bool:
        record = self._records.get(catchment_id)
        if record is None or email.lower() not in record.shared_with:
            return False
        record.shared_with.discard(email.lower())
        return True

    def list_shares(self, catchment_id: str) -> list[str]:
        record = self._records.get(catchment_id)
        return sorted(record.shared_with) if record else []

    def upsert_user(self, email: str, name: str | None, admin: bool) -> dict:
        email = email.lower()
        existing = self._users.get(email)
        role = "admin" if admin else (existing or {}).get("role", "internal-user")
        user = {
            "email": email,
            "name": name or (existing or {}).get("name"),
            "role": role,
            "builderGroupId": (existing or {}).get("builderGroupId"),
        }
        self._users[email] = user
        return user

    def get_user(self, email: str) -> dict | None:
        return self._users.get(email.lower())

    def list_users(self) -> list[dict]:
        return sorted(self._users.values(), key=lambda u: u["email"])

    def set_role(self, email: str, role: str) -> bool:
        user = self._users.get(email.lower())
        if user is None:
            return False
        user["role"] = role
        return True

    def set_user_group(self, email: str, group_id: str | None) -> bool:
        user = self._users.get(email.lower())
        if user is None:
            return False
        user["builderGroupId"] = group_id
        return True

    # --- builder org model ---
    def create_builder_group(self, group_id: str, name: str) -> None:
        self._groups[group_id] = {"id": group_id, "name": name}

    def list_builder_groups(self) -> list[dict]:
        return sorted(self._groups.values(), key=lambda g: g["name"])

    def delete_builder_group(self, group_id: str) -> bool:
        existed = self._groups.pop(group_id, None) is not None
        for b in [b for b in self._builders.values() if b["groupId"] == group_id]:
            self.delete_builder(b["id"])
        return existed

    def create_builder(
        self, builder_id: str, group_id: str, name: str, theme_heading: str
    ) -> None:
        self._builders[builder_id] = {
            "id": builder_id,
            "groupId": group_id,
            "name": name,
            "themeHeading": theme_heading,
        }

    def list_builders(self, group_id: str | None = None) -> list[dict]:
        builders = self._builders.values()
        if group_id is not None:
            builders = [b for b in builders if b["groupId"] == group_id]
        return sorted(builders, key=lambda b: b["name"])

    def delete_builder(self, builder_id: str) -> bool:
        existed = self._builders.pop(builder_id, None) is not None
        for p in [p for p in self._profiles.values() if p["builderId"] == builder_id]:
            self._profiles.pop(p["id"], None)
        return existed

    def upsert_builder_profile(self, profile: dict) -> None:
        self._profiles[profile["id"]] = profile

    def get_builder_profile(self, profile_id: str) -> dict | None:
        return self._profiles.get(profile_id)

    def delete_builder_profile(self, profile_id: str) -> bool:
        return self._profiles.pop(profile_id, None) is not None

    def list_builder_profiles(self, group_id: str | None = None) -> list[dict]:
        """Profiles enriched with brand and group; scoped to a group if given."""
        out = []
        for p in self._profiles.values():
            builder = self._builders.get(p["builderId"])
            if builder is None:
                continue
            if group_id is not None and builder["groupId"] != group_id:
                continue
            group = self._groups.get(builder["groupId"], {})
            out.append(
                {
                    **p,
                    "builderName": builder["name"],
                    "themeHeading": builder["themeHeading"],
                    "groupId": builder["groupId"],
                    "groupName": group.get("name", ""),
                }
            )
        return sorted(out, key=lambda p: (p["groupName"], p["builderName"], p["name"]))

    def get_settings(self, email: str) -> dict | None:
        return self._settings.get(email.lower())

    def save_settings(self, email: str, settings: dict) -> None:
        self._settings[email.lower()] = settings

    def get_config(self, key: str) -> dict | None:
        return self._config.get(key)

    def set_config(self, key: str, value: dict) -> None:
        self._config[key] = value

    def get_area_profile(self, cache_key: str) -> dict | None:
        return self._area_profiles.get(cache_key)

    def save_area_profile(self, cache_key: str, model: str, payload: dict) -> None:
        self._area_profiles[cache_key] = {"model": model, **payload}


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
        owner = None if created_by == "system" else created_by
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO catchment "
                "(id, input_kind, input_value, development_name, config, status, "
                "created_by, owner_email) "
                "VALUES (%s, %s, %s, %s, %s, 'queued', %s, %s)",
                [
                    catchment_id,
                    job.kind,
                    job.value,
                    job.development_name,
                    json.dumps(scoring_config_to_dict(config)),
                    created_by,
                    owner,
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
                "ST_AsGeoJSON(isochrone) AS isochrone, config "
                "FROM catchment WHERE id = %s",
                [catchment_id],
            ).fetchone()
            if head is None:
                return None
            kind, value, dev_name, status, error, lng, lat, isochrone, config = head

            area_rows = conn.execute(
                "SELECT ca.area_code, ca.area_type, gb.area_name, "
                "ca.proportion_inside, ca.priority_score, ca.rank, "
                "ST_AsGeoJSON(gb.geom) AS geom, b.payload "
                "FROM catchment_area ca "
                "LEFT JOIN geo_boundaries gb ON gb.area_code = ca.area_code "
                "LEFT JOIN battlecard b ON b.catchment_id = ca.catchment_id "
                "AND b.area_code = ca.area_code "
                "WHERE ca.catchment_id = %s ORDER BY ca.rank",
                [catchment_id],
            ).fetchall()

        total = len(area_rows)
        areas = [
            {
                "areaCode": code,
                "areaType": a_type,
                "name": name or code,
                "proportionInside": float(prop),
                "score": float(score),
                "band": relative_band(rank, total),
                "rank": rank,
                "geometry": json.loads(geom) if geom else None,
                "metrics": _area_metrics(payload),
            }
            for (code, a_type, name, prop, score, rank, geom, payload) in area_rows
        ]
        return {
            "id": catchment_id,
            "input": {
                "kind": kind,
                "value": value,
                "developmentName": dev_name,
                "config": config,
            },
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

    def delete_catchment(self, catchment_id: str) -> bool:
        # catchment_area and battlecard cascade via their foreign keys.
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM catchment WHERE id = %s", [catchment_id])
            return cur.rowcount > 0

    def list_catchments(
        self,
        viewer_email: str | None,
        is_admin: bool,
        archived: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        where = ["c.archived_at IS NOT NULL" if archived else "c.archived_at IS NULL"]
        params: list = []
        if not is_admin:
            # Own catchments plus any shared explicitly with the viewer.
            where.append(
                "(c.owner_email = %s OR EXISTS (SELECT 1 FROM catchment_share s "
                "WHERE s.catchment_id = c.id AND s.shared_with_email = %s))"
            )
            params.extend([viewer_email, viewer_email])
        params.append(limit)
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT c.id, c.development_name, c.input_value, c.status, "
                "c.created_at, c.owner_email, count(ca.area_code) AS area_count "
                "FROM catchment c "
                "LEFT JOIN catchment_area ca ON ca.catchment_id = c.id "
                f"WHERE {' AND '.join(where)} "
                "GROUP BY c.id ORDER BY c.created_at DESC LIMIT %s",
                params,
            ).fetchall()
        return [
            {
                "id": str(cid),
                "developmentName": dev_name,
                "inputValue": value,
                "status": status,
                "areaCount": area_count,
                "createdAt": created_at.isoformat() if created_at else None,
                "owner": owner,
                "shared": bool(owner and viewer_email and owner != viewer_email),
                "archived": archived,
            }
            for (cid, dev_name, value, status, created_at, owner, area_count) in rows
        ]

    def get_owner(self, catchment_id: str) -> str | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT owner_email FROM catchment WHERE id = %s", [catchment_id]
            ).fetchone()
        return row[0] if row else None

    def can_access(
        self, catchment_id: str, viewer_email: str | None, is_admin: bool
    ) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT owner_email FROM catchment WHERE id = %s", [catchment_id]
            ).fetchone()
            if row is None:
                return False
            if is_admin:
                return True
            owner = row[0]
            if owner is not None and owner == viewer_email:
                return True
            share = conn.execute(
                "SELECT 1 FROM catchment_share WHERE catchment_id = %s "
                "AND shared_with_email = %s",
                [catchment_id, viewer_email],
            ).fetchone()
            return share is not None

    def set_archived(self, catchment_id: str, archived: bool) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE catchment SET archived_at = %s WHERE id = %s",
                [datetime.now(UTC) if archived else None, catchment_id],
            )
            return cur.rowcount > 0

    def add_shares(self, catchment_id: str, emails: list[str]) -> None:
        with self._pool.connection() as conn:
            for email in emails:
                clean = email.strip().lower()
                if not clean:
                    continue
                conn.execute(
                    "INSERT INTO catchment_share (catchment_id, shared_with_email) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    [catchment_id, clean],
                )

    def remove_share(self, catchment_id: str, email: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "DELETE FROM catchment_share WHERE catchment_id = %s "
                "AND shared_with_email = %s",
                [catchment_id, email.lower()],
            )
            return cur.rowcount > 0

    def list_shares(self, catchment_id: str) -> list[str]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT shared_with_email FROM catchment_share "
                "WHERE catchment_id = %s ORDER BY shared_with_email",
                [catchment_id],
            ).fetchall()
        return [r[0] for r in rows]

    def upsert_user(self, email: str, name: str | None, admin: bool) -> dict:
        email = email.lower()
        with self._pool.connection() as conn:
            if admin:
                conn.execute(
                    "INSERT INTO app_user (email, name, role) VALUES (%s, %s, 'admin') "
                    "ON CONFLICT (email) DO UPDATE SET "
                    "name = COALESCE(EXCLUDED.name, app_user.name), "
                    "role = 'admin', updated_at = now()",
                    [email, name],
                )
            else:
                conn.execute(
                    "INSERT INTO app_user (email, name) VALUES (%s, %s) "
                    "ON CONFLICT (email) DO UPDATE SET "
                    "name = COALESCE(EXCLUDED.name, app_user.name), updated_at = now()",
                    [email, name],
                )
            row = conn.execute(
                "SELECT email, name, role, builder_group_id FROM app_user "
                "WHERE email = %s",
                [email],
            ).fetchone()
        return _user_row(row)

    def get_user(self, email: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT email, name, role, builder_group_id FROM app_user "
                "WHERE email = %s",
                [email.lower()],
            ).fetchone()
        return None if row is None else _user_row(row)

    def list_users(self) -> list[dict]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT email, name, role, builder_group_id FROM app_user "
                "ORDER BY email"
            ).fetchall()
        return [_user_row(r) for r in rows]

    def set_role(self, email: str, role: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE app_user SET role = %s, updated_at = now() WHERE email = %s",
                [role, email.lower()],
            )
            return cur.rowcount > 0

    def set_user_group(self, email: str, group_id: str | None) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "UPDATE app_user SET builder_group_id = %s, updated_at = now() "
                "WHERE email = %s",
                [group_id, email.lower()],
            )
            return cur.rowcount > 0

    def create_builder_group(self, group_id: str, name: str) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO builder_group (id, name) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
                [group_id, name],
            )

    def list_builder_groups(self) -> list[dict]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT id, name FROM builder_group ORDER BY name"
            ).fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]

    def delete_builder_group(self, group_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM builder_group WHERE id = %s", [group_id])
            return cur.rowcount > 0

    def create_builder(
        self, builder_id: str, group_id: str, name: str, theme_heading: str
    ) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO builder (id, group_id, name, theme_heading) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET "
                "name = EXCLUDED.name, theme_heading = EXCLUDED.theme_heading",
                [builder_id, group_id, name, theme_heading],
            )

    def list_builders(self, group_id: str | None = None) -> list[dict]:
        sql = "SELECT id, group_id, name, theme_heading FROM builder"
        params: list = []
        if group_id is not None:
            sql += " WHERE group_id = %s"
            params.append(group_id)
        sql += " ORDER BY name"
        with self._pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            {"id": r[0], "groupId": r[1], "name": r[2], "themeHeading": r[3]}
            for r in rows
        ]

    def delete_builder(self, builder_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute("DELETE FROM builder WHERE id = %s", [builder_id])
            return cur.rowcount > 0

    def upsert_builder_profile(self, profile: dict) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO builder_profile (id, builder_id, name, segment, "
                "bed_range, price_from, price_to, strapline, pillars, features) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO UPDATE SET builder_id = EXCLUDED.builder_id, "
                "name = EXCLUDED.name, segment = EXCLUDED.segment, "
                "bed_range = EXCLUDED.bed_range, price_from = EXCLUDED.price_from, "
                "price_to = EXCLUDED.price_to, strapline = EXCLUDED.strapline, "
                "pillars = EXCLUDED.pillars, features = EXCLUDED.features",
                [
                    profile["id"],
                    profile["builderId"],
                    profile["name"],
                    profile.get("segment"),
                    profile.get("bedRange"),
                    profile.get("priceFrom"),
                    profile.get("priceTo"),
                    profile.get("strapline"),
                    json.dumps(profile.get("pillars", [])),
                    json.dumps(profile.get("features", [])),
                ],
            )

    def get_builder_profile(self, profile_id: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT id, builder_id, name, segment, bed_range, price_from, "
                "price_to, strapline, pillars, features FROM builder_profile "
                "WHERE id = %s",
                [profile_id],
            ).fetchone()
        return None if row is None else _profile_row(row)

    def delete_builder_profile(self, profile_id: str) -> bool:
        with self._pool.connection() as conn:
            cur = conn.execute(
                "DELETE FROM builder_profile WHERE id = %s", [profile_id]
            )
            return cur.rowcount > 0

    def list_builder_profiles(self, group_id: str | None = None) -> list[dict]:
        sql = (
            "SELECT p.id, p.builder_id, p.name, p.segment, p.bed_range, "
            "p.price_from, p.price_to, p.strapline, p.pillars, p.features, "
            "b.name, b.theme_heading, b.group_id, g.name "
            "FROM builder_profile p JOIN builder b ON p.builder_id = b.id "
            "JOIN builder_group g ON b.group_id = g.id"
        )
        params: list = []
        if group_id is not None:
            sql += " WHERE b.group_id = %s"
            params.append(group_id)
        sql += " ORDER BY g.name, b.name, p.name"
        with self._pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [
            {
                **_profile_row(r[:10]),
                "builderName": r[10],
                "themeHeading": r[11],
                "groupId": r[12],
                "groupName": r[13],
            }
            for r in rows
        ]

    def get_settings(self, email: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT settings FROM user_settings WHERE email = %s", [email.lower()]
            ).fetchone()
        return row[0] if row else None

    def save_settings(self, email: str, settings: dict) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO user_settings (email, settings) VALUES (%s, %s) "
                "ON CONFLICT (email) DO UPDATE SET settings = EXCLUDED.settings, "
                "updated_at = now()",
                [email.lower(), json.dumps(settings)],
            )

    def get_config(self, key: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_config WHERE key = %s", [key]
            ).fetchone()
        return row[0] if row else None

    def set_config(self, key: str, value: dict) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO app_config (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "
                "updated_at = now()",
                [key, json.dumps(value)],
            )

    def get_area_profile(self, cache_key: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT model, payload FROM area_profile_cache WHERE cache_key = %s",
                [cache_key],
            ).fetchone()
        return None if row is None else {"model": row[0], **row[1]}

    def save_area_profile(self, cache_key: str, model: str, payload: dict) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO area_profile_cache (cache_key, model, payload) "
                "VALUES (%s, %s, %s) ON CONFLICT (cache_key) DO UPDATE SET "
                "model = EXCLUDED.model, payload = EXCLUDED.payload, created_at = now()",
                [cache_key, model, json.dumps(payload)],
            )
