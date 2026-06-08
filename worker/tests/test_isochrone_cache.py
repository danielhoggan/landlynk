"""Isochrone results are cached by coordinate and parameters so re-runs are free.

The OpenRouteService provider is exercised with a mocked httpx transport so the
request shape and response mapping are tested without touching the network.
"""

from __future__ import annotations

import httpx
import pytest

from landlynk_worker.pipeline.isochrone import (
    InMemoryIsochroneCache,
    IsochroneError,
    IsochroneParams,
    OpenRouteServiceProvider,
    get_isochrone,
)


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


# --- OpenRouteService provider (mocked) --------------------------------------

_ORS_SAMPLE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[1.0, 52.0], [1.1, 52.0], [1.1, 52.1], [1.0, 52.0]]],
            },
        }
    ],
}


def test_ors_provider_builds_request_and_extracts_geometry():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ORS_SAMPLE)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouteServiceProvider(api_key="test-key", client=client)
        params = IsochroneParams(lat=52.0, lng=1.0, drive_time_minutes=30)
        geometry = provider.fetch(params)

    assert geometry["type"] == "Polygon"
    assert captured["url"].endswith("/v2/isochrones/driving-car")
    assert captured["auth"] == "test-key"
    # ORS wants [lng, lat] and a range in seconds.
    assert captured["body"]["locations"] == [[1.0, 52.0]]
    assert captured["body"]["range"] == [1800]
    assert captured["body"]["range_type"] == "time"


def test_ors_provider_raises_on_empty_features():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"type": "FeatureCollection", "features": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouteServiceProvider(api_key="k", client=client)
        with pytest.raises(IsochroneError):
            provider.fetch(IsochroneParams(lat=52.0, lng=1.0, drive_time_minutes=30))


def test_ors_provider_self_hosted_base_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith("http://ors.internal:8080/")
        return httpx.Response(200, json=_ORS_SAMPLE)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouteServiceProvider(
            api_key="k", client=client, base_url="http://ors.internal:8080"
        )
        geometry = provider.fetch(
            IsochroneParams(lat=52.0, lng=1.0, drive_time_minutes=30)
        )
    assert geometry["type"] == "Polygon"


def test_ors_provider_retries_then_succeeds():
    # First call 503, second 200. With backoff_base=0 there is no real sleep.
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={})
        return httpx.Response(200, json=_ORS_SAMPLE)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouteServiceProvider(api_key="k", client=client, backoff_base=0)
        geometry = provider.fetch(
            IsochroneParams(lat=52.0, lng=1.0, drive_time_minutes=30)
        )
    assert geometry["type"] == "Polygon"
    assert calls["n"] == 2


def test_ors_provider_gives_up_after_retries():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = OpenRouteServiceProvider(
            api_key="k", client=client, max_retries=2, backoff_base=0
        )
        with pytest.raises(IsochroneError):
            provider.fetch(IsochroneParams(lat=52.0, lng=1.0, drive_time_minutes=30))


def test_in_memory_cache_round_trip_with_provider():
    cache = InMemoryIsochroneCache()
    provider = CountingProvider()
    params = IsochroneParams(lat=52.2, lng=1.0, drive_time_minutes=30)

    get_isochrone(params, provider, cache)
    get_isochrone(params, provider, cache)
    assert provider.calls == 1
