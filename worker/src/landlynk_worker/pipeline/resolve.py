"""Stage 1: resolve input to a WGS84 coordinate.

Detect postcode vs OS grid reference and geocode accordingly. postcodes.io for
postcodes (free, no key), pyproj for OS grid references, so the workflow is
identical whether or not a postcode exists. New developments often have no
postcode yet, so grid-ref support is not optional (SCOPING.md 3.1).

The grid-ref parsing and the postcode response mapping are pure and unit
tested. The one network call (postcodes.io) is injected as an httpx client so
it can be mocked in tests and pointed at the live service in production.

Validate the resolved coordinate falls within GB.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from pyproj import Transformer

# UK postcode pattern (loose). Grid refs are two letters then digits.
_POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)
_GRIDREF_RE = re.compile(r"^[A-Z]{2}\s*\d{2,10}(\s*\d{2,10})?$", re.IGNORECASE)

# Rough GB bounding box for validation.
_GB_BBOX = (-8.65, 49.86, 1.77, 60.86)  # min_lng, min_lat, max_lng, max_lat

_POSTCODES_IO = "https://api.postcodes.io"

# OS grid letters, with 'I' omitted. Used to resolve the 100km square origin.
_GRID_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"

# Reused transformer: British National Grid (EPSG:27700) to WGS84 (EPSG:4326).
# always_xy means we pass (easting, northing) and receive (lng, lat).
_BNG_TO_WGS84 = Transformer.from_crs(27700, 4326, always_xy=True)


class GeocodeError(Exception):
    """Raised when an input cannot be resolved to a GB coordinate."""


@dataclass(frozen=True)
class Coordinate:
    lat: float
    lng: float


def detect_input_kind(raw: str) -> str:
    """Return "postcode", "gridref" or "unknown" for a raw input string."""
    value = raw.strip()
    if _POSTCODE_RE.match(value):
        return "postcode"
    if _GRIDREF_RE.match(value):
        return "gridref"
    return "unknown"


def is_within_gb(coord: Coordinate) -> bool:
    min_lng, min_lat, max_lng, max_lat = _GB_BBOX
    return min_lat <= coord.lat <= max_lat and min_lng <= coord.lng <= max_lng


# --- Grid reference (pure, offline) ------------------------------------------


def _square_origin(letters: str) -> tuple[int, int]:
    """Return the (easting, northing) origin in metres for a two-letter square."""
    l1, l2 = letters[0].upper(), letters[1].upper()
    if l1 not in _GRID_LETTERS or l2 not in _GRID_LETTERS:
        raise GeocodeError(f"Invalid grid square letters: {letters}")
    a = ord(l1) - ord("A")
    a -= 1 if a > 7 else 0  # skip the omitted 'I'
    b = ord(l2) - ord("A")
    b -= 1 if b > 7 else 0
    e = ((a - 2) % 5) * 5 + (b % 5)
    n = (19 - (a // 5) * 5) - (b // 5)
    return e * 100_000, n * 100_000


def parse_grid_ref(raw: str) -> tuple[int, int]:
    """Parse an OS grid reference to absolute (easting, northing) in metres.

    Accepts forms like "TM0645", "TM 06457 58755" and "TM064587". The numeric
    part must be an even number of digits, split evenly into easting and
    northing, each padded to a full 5-digit (1 metre) resolution.
    """
    value = raw.strip().upper()
    if len(value) < 2 or not value[:2].isalpha():
        raise GeocodeError(f"Not a grid reference: {raw}")
    letters = value[:2]
    digits = re.sub(r"\s+", "", value[2:])
    if not digits.isdigit() or len(digits) == 0 or len(digits) % 2 != 0:
        raise GeocodeError(f"Grid reference needs an even number of digits: {raw}")

    half = len(digits) // 2
    if half > 5:
        raise GeocodeError(f"Grid reference too precise: {raw}")
    e_digits, n_digits = digits[:half], digits[half:]
    # Pad each part to 5 digits so partial refs resolve to the square's corner.
    easting_offset = int(e_digits.ljust(5, "0"))
    northing_offset = int(n_digits.ljust(5, "0"))

    e0, n0 = _square_origin(letters)
    return e0 + easting_offset, n0 + northing_offset


def gridref_to_coordinate(raw: str) -> Coordinate:
    """Convert an OS grid reference to a WGS84 coordinate, offline via pyproj."""
    easting, northing = parse_grid_ref(raw)
    lng, lat = _BNG_TO_WGS84.transform(easting, northing)
    coord = Coordinate(lat=round(lat, 6), lng=round(lng, 6))
    if not is_within_gb(coord):
        raise GeocodeError(f"Grid reference resolved outside GB: {raw}")
    return coord


# --- Postcode (network, injectable client) -----------------------------------


def geocode_postcode(postcode: str, client: httpx.Client) -> Coordinate:
    """Geocode a postcode via postcodes.io. Free, no key.

    The httpx client is injected so tests mock it and production points it at
    the live service. No personal data is involved; a postcode is not personal.
    """
    normalised = re.sub(r"\s+", "", postcode).upper()
    resp = client.get(f"{_POSTCODES_IO}/postcodes/{normalised}")
    if resp.status_code == 404:
        raise GeocodeError(f"Postcode not found: {postcode}")
    resp.raise_for_status()
    result = resp.json().get("result") or {}
    lat, lng = result.get("latitude"), result.get("longitude")
    if lat is None or lng is None:
        raise GeocodeError(f"Postcode has no coordinate: {postcode}")
    coord = Coordinate(lat=float(lat), lng=float(lng))
    if not is_within_gb(coord):
        raise GeocodeError(f"Postcode resolved outside GB: {postcode}")
    return coord


def resolve_input(raw: str, client: httpx.Client | None = None) -> Coordinate:
    """Geocode raw input to a coordinate, dispatching on detected kind.

    Grid references resolve offline. Postcodes need an httpx client; one is
    created if not supplied.
    """
    kind = detect_input_kind(raw)
    if kind == "gridref":
        return gridref_to_coordinate(raw)
    if kind == "postcode":
        if client is None:
            with httpx.Client(timeout=10.0) as owned:
                return geocode_postcode(raw, owned)
        return geocode_postcode(raw, client)
    raise GeocodeError(f"Unrecognised input, not a postcode or grid reference: {raw}")
