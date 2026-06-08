"""Stage 1: resolve input to a WGS84 coordinate.

Detect postcode vs OS grid reference and geocode accordingly. postcodes.io for
postcodes (free), the osgb library or OS Transformation API for grid references,
so the workflow is identical whether or not a postcode exists. New developments
often have no postcode yet, so grid-ref support is not optional (SCOPING.md 3.1).

Validate the resolved coordinate falls within GB.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# UK postcode pattern (loose). Grid refs are two letters then digits.
_POSTCODE_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)
_GRIDREF_RE = re.compile(r"^[A-Z]{2}\s*\d{2,10}(\s*\d{2,10})?$", re.IGNORECASE)

# Rough GB bounding box for validation.
_GB_BBOX = (-8.65, 49.86, 1.77, 60.86)  # min_lng, min_lat, max_lng, max_lat


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


def resolve_input(raw: str) -> Coordinate:  # pragma: no cover - needs network
    """Geocode raw input to a coordinate. Wired to providers in implementation.

    Raises NotImplementedError until the geocoding providers are connected. The
    detection and validation helpers above are unit tested independently.
    """
    raise NotImplementedError(
        "Geocoding providers (postcodes.io, osgb) are not yet wired. "
        "Use detect_input_kind and is_within_gb for the pure parts."
    )
