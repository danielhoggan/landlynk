"""Vector map thumbnail from a catchment geometry.

We cannot use licensed map tiles (open data only), but we already hold the
GeoJSON for each area and the whole catchment. So the Battlecard "map" is a
simple vector outline of that shape, scaled to fit a box. No basemap, no tiles,
no licence. Rendered natively by each export (freeform in PPTX, polygon in PDF).
"""

from __future__ import annotations


def largest_ring(geometry: dict | None) -> list[tuple[float, float]]:
    """The outer ring with the most points across a Polygon or MultiPolygon."""
    if not geometry:
        return []
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    rings: list = []
    if gtype == "Polygon":
        rings = coords
    elif gtype == "MultiPolygon":
        for poly in coords:
            rings.extend(poly)
    else:
        return []
    if not rings:
        return []
    ring = max(rings, key=len)
    return [(float(p[0]), float(p[1])) for p in ring if len(p) >= 2]


def fit_ring(
    geometry: dict | None,
    width: float,
    height: float,
    pad: float = 2.0,
    y_down: bool = False,
) -> list[tuple[float, float]]:
    """Scale the largest ring to fit width x height, aspect preserved, centred.

    y_down=True for screen/EMU coordinates (origin top-left, as in PPTX); False
    for PDF user space (origin bottom-left).
    """
    ring = largest_ring(geometry)
    if len(ring) < 3:
        return []
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    gw = (maxx - minx) or 1e-9
    gh = (maxy - miny) or 1e-9
    aw = width - 2 * pad
    ah = height - 2 * pad
    scale = min(aw / gw, ah / gh)
    ox = pad + (aw - gw * scale) / 2
    oy = pad + (ah - gh * scale) / 2
    points: list[tuple[float, float]] = []
    for x, y in ring:
        px = ox + (x - minx) * scale
        py = oy + (maxy - y) * scale if y_down else oy + (y - miny) * scale
        points.append((px, py))
    return points
