"""Input detection and GB validation are pure and tested without network."""

from __future__ import annotations

from landlynk_worker.pipeline.resolve import (
    Coordinate,
    detect_input_kind,
    is_within_gb,
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
