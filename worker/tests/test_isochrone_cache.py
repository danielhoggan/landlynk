"""Isochrone results are cached by coordinate and parameters so re-runs are free."""

from __future__ import annotations

from landlynk_worker.pipeline.isochrone import IsochroneParams, get_isochrone


class DictCache:
    def __init__(self) -> None:
        self.store: dict[str, dict] = {}

    def get(self, key: str) -> dict | None:
        return self.store.get(key)

    def set(self, key: str, geojson: dict) -> None:
        self.store[key] = geojson


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, params: IsochroneParams) -> dict:
        self.calls += 1
        return {"type": "Polygon", "coordinates": []}


def test_cache_key_is_stable_with_coordinate_rounding():
    a = IsochroneParams(lat=52.20001, lng=1.00001, drive_time_minutes=30)
    b = IsochroneParams(lat=52.20002, lng=1.00002, drive_time_minutes=30)
    assert a.cache_key() == b.cache_key()


def test_cache_key_varies_with_drive_time():
    a = IsochroneParams(lat=52.2, lng=1.0, drive_time_minutes=30)
    b = IsochroneParams(lat=52.2, lng=1.0, drive_time_minutes=45)
    assert a.cache_key() != b.cache_key()


def test_provider_called_once_then_served_from_cache():
    cache = DictCache()
    provider = CountingProvider()
    params = IsochroneParams(lat=52.2, lng=1.0, drive_time_minutes=30)

    first = get_isochrone(params, provider, cache)
    second = get_isochrone(params, provider, cache)

    assert first == second
    assert provider.calls == 1  # second call served from cache, no re-bill
