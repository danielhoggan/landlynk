"""Live competitor-developments overlay from PlanIt (planit.org.uk).

PlanIt aggregates UK planning applications nationally, so the competitor layer
needs no per-authority upload or stored dataset: we query it per catchment by
bounding box and keep the residential applications that fall inside the
catchment polygon. Best effort, so any network or parse failure yields no
competitor sites rather than breaking the overlay.
"""

from __future__ import annotations

import concurrent.futures as cf
import logging
import math
from datetime import date, timedelta

import httpx
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

log = logging.getLogger(__name__)

# Keywords that mark a residential scheme, so the overlay shows housing
# competition rather than every application (signs, extensions and the like).
_RESIDENTIAL = (
    "dwelling",
    "residential",
    "homes",
    "houses",
    "flats",
    "apartment",
)


def _residential_sites_from_geojson(data: dict, poly: BaseGeometry) -> list[dict]:
    """Parse a PlanIt GeoJSON response into residential competitor sites inside
    the catchment polygon. Pure, so it is unit tested without the network."""
    features = data.get("features") if isinstance(data, dict) else None
    if not features:
        return []
    sites: list[dict] = []
    for f in features:
        geom = f.get("geometry")
        if not geom:
            continue
        try:
            g = shape(geom)
            pt = g if g.geom_type == "Point" else g.centroid
        except Exception:
            continue
        if not poly.contains(Point(pt.x, pt.y)):
            continue
        props = f.get("properties") or {}
        text = " ".join(
            str(props.get(k, "")) for k in ("description", "app_type", "name")
        ).lower()
        if not any(k in text for k in _RESIDENTIAL):
            continue
        name = (
            props.get("address")
            or props.get("description")
            or props.get("name")
            or "Planning application"
        )
        sites.append(
            {
                "reference": props.get("reference")
                or props.get("uid")
                or props.get("name"),
                "name": str(name).strip()[:120] or "Planning application",
                "lat": float(pt.y),
                "lng": float(pt.x),
            }
        )
    return sites


def _tiles(
    bounds: tuple[float, float, float, float],
    target: float = 0.4,
    max_tiles: int = 12,
) -> list[tuple[float, float, float, float]]:
    """Split a bounding box into ~target-degree tiles (capped), so each PlanIt
    query covers a small enough area to return fast. A catchment-sized bbox in
    one request times out the national data source; tiles do not."""
    minx, miny, maxx, maxy = bounds
    ncols = max(1, math.ceil((maxx - minx) / target))
    nrows = max(1, math.ceil((maxy - miny) / target))
    while ncols * nrows > max_tiles:
        if ncols >= nrows and ncols > 1:
            ncols -= 1
        elif nrows > 1:
            nrows -= 1
        else:
            break
    dx = (maxx - minx) / ncols
    dy = (maxy - miny) / nrows
    return [
        (minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy)
        for i in range(ncols)
        for j in range(nrows)
    ]


def fetch_competitor_sites(
    geometry: dict | None,
    base_url: str,
    lookback_days: int,
    limit: int = 400,
) -> list[dict]:
    """Residential planning applications inside the catchment, live from PlanIt.

    Queries major and medium schemes over a recent window, tiled across the
    catchment and run in parallel so a large catchment does not time out the
    data source. Best effort: failures yield no competitor sites.
    """
    if not geometry:
        return []
    try:
        poly = shape(geometry)
    except Exception:
        return []
    if poly.is_empty or not all(math.isfinite(v) for v in poly.bounds):
        return []
    start_date = (date.today() - timedelta(days=lookback_days)).isoformat()
    url = f"{base_url.rstrip('/')}/api/applics/geojson"

    def fetch_tile(tile: tuple[float, float, float, float]) -> dict:
        # PlanIt bbox is west,south,east,north (lng,lat,lng,lat).
        params = {
            "bbox": f"{tile[0]},{tile[1]},{tile[2]},{tile[3]}",
            "pg_sz": 150,
            "app_size": "Large,Medium",
            "start_date": start_date,
        }
        try:
            with httpx.Client(
                timeout=25.0, headers={"User-Agent": "LandLynk/1.0 (+catchment)"}
            ) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:  # pragma: no cover - network path
            log.warning("PlanIt tile fetch failed: %s", exc)
            return {}

    tiles = _tiles(poly.bounds)
    seen: set = set()
    out: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=min(6, len(tiles))) as pool:
        for data in pool.map(fetch_tile, tiles):
            for site in _residential_sites_from_geojson(data, poly):
                key = site.get("reference") or (
                    round(site["lat"], 5),
                    round(site["lng"], 5),
                )
                if key in seen:
                    continue
                seen.add(key)
                out.append(site)
                if len(out) >= limit:
                    return out
    return out


def planit_diagnostic(base_url: str, lookback_days: int) -> dict:
    """Probe PlanIt with a known UK bbox and report what comes back, so an admin
    can tell a deploy/network problem from an empty result without a catchment."""
    geom = {
        "type": "Polygon",
        "coordinates": [
            [[-1.8, 54.85], [-1.8, 55.05], [-1.4, 55.05], [-1.4, 54.85], [-1.8, 54.85]]
        ],
    }
    poly = shape(geom)
    minx, miny, maxx, maxy = poly.bounds
    params = {
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "pg_sz": 50,
        "start_date": (date.today() - timedelta(days=lookback_days)).isoformat(),
    }
    url = f"{base_url.rstrip('/')}/api/applics/geojson"
    try:
        with httpx.Client(
            timeout=20.0, headers={"User-Agent": "LandLynk/1.0"}
        ) as client:
            resp = client.get(url, params=params)
            status = resp.status_code
            preview = resp.text[:200]
            resp.raise_for_status()
            data = resp.json()
        total = len(data.get("features", []) if isinstance(data, dict) else [])
        residential = _residential_sites_from_geojson(data, poly)
        return {
            "ok": True,
            "requestUrl": str(resp.url),
            "status": status,
            "totalFeatures": total,
            "residential": len(residential),
            "sample": [s["name"] for s in residential[:3]],
            "bodyPreview": preview,
        }
    except Exception as exc:  # pragma: no cover - network path
        return {"ok": False, "requestUrl": url, "error": str(exc)}
