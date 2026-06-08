"""Stage 2: drive-time isochrone.

Call the chosen isochrone provider for a drive-time polygon. Results are cached
by coordinate and parameters so re-runs are free and never re-bill the provider
(CLAUDE.md; SCOPING.md 11 risk mitigation).

The default provider is OpenRouteService (open, OSM-based, free tier), wired
behind a pluggable seam so a self-hosted ORS or Valhalla, or TravelTime, can be
dropped in without changing the rest of the pipeline (SCOPING.md Section 11).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import httpx

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool


@dataclass(frozen=True)
class IsochroneParams:
    lat: float
    lng: float
    drive_time_minutes: int
    profile: str = "driving-car"

    def cache_key(self) -> str:
        """Stable key for caching. Coordinates rounded to ~11m precision.

        Rounding means trivially different coordinates for the same site reuse
        one cached isochrone instead of re-billing the provider.
        """
        return (
            f"{self.profile}:{self.drive_time_minutes}:"
            f"{round(self.lat, 4)}:{round(self.lng, 4)}"
        )


class IsochroneCache(Protocol):
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, geojson: dict) -> None: ...


class IsochroneProvider(Protocol):
    def fetch(self, params: IsochroneParams) -> dict: ...


def get_isochrone(
    params: IsochroneParams,
    provider: IsochroneProvider,
    cache: IsochroneCache,
) -> dict:
    """Return a GeoJSON isochrone polygon, from cache when available.

    The cache is consulted first; on a miss the provider is called and the
    result stored before returning.
    """
    key = params.cache_key()
    cached = cache.get(key)
    if cached is not None:
        return cached
    geojson = provider.fetch(params)
    cache.set(key, geojson)
    return geojson


class IsochroneError(Exception):
    """Raised when a provider cannot return an isochrone."""


class InMemoryIsochroneCache:
    """Process-local cache. Fine for a single worker run or dev.

    Production uses a durable cache (Postgres) so the saving survives restarts;
    both satisfy the IsochroneCache protocol.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        return self._store.get(key)

    def set(self, key: str, geojson: dict) -> None:
        self._store[key] = geojson


class PostgresIsochroneCache:
    """Durable cache in the isochrone_cache table.

    Shared across worker instances and restarts, so a coordinate is only ever
    billed once. Satisfies the IsochroneCache protocol.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def get(self, key: str) -> dict | None:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT geojson FROM isochrone_cache WHERE cache_key = %s", [key]
            ).fetchone()
        return row[0] if row else None

    def set(self, key: str, geojson: dict) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO isochrone_cache (cache_key, geojson) VALUES (%s, %s) "
                "ON CONFLICT (cache_key) DO UPDATE SET geojson = EXCLUDED.geojson",
                [key, json.dumps(geojson)],
            )


class OpenRouteServiceProvider:
    """OpenRouteService isochrones. OSM-based, open, free tier, no data licence.

    The httpx client is injected so it is mocked in tests and points at the
    hosted or a self-hosted ORS in production. Set ``base_url`` to a self-hosted
    instance to remove the free-tier quota without other changes.
    """

    def __init__(
        self,
        api_key: str,
        client: httpx.Client,
        base_url: str = "https://api.openrouteservice.org",
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._base_url = base_url.rstrip("/")

    def fetch(self, params: IsochroneParams) -> dict:
        """Return the isochrone geometry as a GeoJSON geometry dict.

        ORS returns a FeatureCollection; we take the first feature's geometry,
        which is the drive-time polygon for the requested range.
        """
        url = f"{self._base_url}/v2/isochrones/{params.profile}"
        body = {
            "locations": [[params.lng, params.lat]],
            "range": [params.drive_time_minutes * 60],  # seconds
            "range_type": "time",
        }
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        resp = self._client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        features = resp.json().get("features") or []
        if not features:
            raise IsochroneError("OpenRouteService returned no isochrone feature")
        geometry = features[0].get("geometry")
        if not geometry:
            raise IsochroneError("OpenRouteService feature had no geometry")
        return geometry
