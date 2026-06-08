"""Stage 2: drive-time isochrone.

Call the chosen isochrone provider (OpenRouteService or TravelTime, both free
tier) for a drive-time polygon. Results are cached by coordinate and parameters
so re-runs are free and never re-bill the provider (CLAUDE.md; SCOPING.md 11
risk mitigation).

This module defines the cache key contract and a pluggable provider seam. The
network call itself is wired in implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
