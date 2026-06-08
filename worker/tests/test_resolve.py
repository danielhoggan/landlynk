"""Input detection, grid-ref conversion and postcode geocoding.

Grid references resolve offline and are asserted against known points. The one
network call (postcodes.io) is mocked via an injected httpx transport, so the
mapping is tested without touching the network.
"""

from __future__ import annotations

import httpx
import pytest

from landlynk_worker.pipeline.resolve import (
    Coordinate,
    GeocodeError,
    detect_input_kind,
    geocode_postcode,
    gridref_to_coordinate,
    is_within_gb,
    parse_grid_ref,
    resolve_input,
)


def test_detects_postcode():
    assert detect_input_kind("IP14 1AA") == "postcode"
    assert detect_input_kind("ip141aa") == "postcode"


def test_detects_gridref():
    assert detect_input_kind("TM 06457 58755") == "gridref"
    assert detect_input_kind("TM0645") == "gridref"


def test_unknown_input():
    assert detect_input_kind("not an address") == "unknown"


def test_gb_bounds():
    assert is_within_gb(Coordinate(lat=52.2, lng=1.0)) is True
    assert is_within_gb(Coordinate(lat=0.0, lng=0.0)) is False  # Atlantic
    assert is_within_gb(Coordinate(lat=40.0, lng=-3.7)) is False  # Madrid


# --- Grid reference -----------------------------------------------------------


def test_parse_grid_ref_full_precision():
    assert parse_grid_ref("TM 06457 58755") == (606457, 258755)


def test_parse_grid_ref_pads_partial_refs():
    # TM0645 -> 4-digit ref, each half padded to a 100m square corner.
    assert parse_grid_ref("TM0645") == (606000, 245000)


def test_parse_grid_ref_rejects_odd_digits():
    with pytest.raises(GeocodeError):
        parse_grid_ref("TM 064 5875")


def test_gridref_to_coordinate_matches_known_point():
    # TQ 30000 80000 is central London, near Charing Cross.
    coord = gridref_to_coordinate("TQ 30000 80000")
    assert coord.lat == pytest.approx(51.504, abs=0.01)
    assert coord.lng == pytest.approx(-0.128, abs=0.01)


def test_gridref_resolve_via_dispatch():
    coord = resolve_input("TM 06457 58755")
    assert coord.lat == pytest.approx(52.188, abs=0.01)
    assert coord.lng == pytest.approx(1.019, abs=0.01)


# --- Postcode geocoding (mocked) ---------------------------------------------


def _client_returning(payload: dict, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_geocode_postcode_maps_result():
    payload = {"result": {"latitude": 52.05, "longitude": 1.03}}
    with _client_returning(payload) as client:
        coord = geocode_postcode("IP14 1AA", client)
    assert coord.lat == 52.05
    assert coord.lng == 1.03


def test_geocode_postcode_not_found():
    with _client_returning({"error": "Not found"}, status=404) as client:
        with pytest.raises(GeocodeError):
            geocode_postcode("ZZ1 1ZZ", client)


def test_geocode_postcode_outside_gb_rejected():
    payload = {"result": {"latitude": 48.85, "longitude": 2.35}}  # Paris
    with _client_returning(payload) as client:
        with pytest.raises(GeocodeError):
            geocode_postcode("IP14 1AA", client)


def test_resolve_input_rejects_garbage():
    with pytest.raises(GeocodeError):
        resolve_input("not an address")
