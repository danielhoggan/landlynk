"""Live competitor-developments overlay from PlanIt (planit.org.uk).

PlanIt aggregates UK planning applications nationally, so the competitor layer
needs no per-authority upload or stored dataset: we query it per catchment by
bounding box and keep the residential applications that fall inside the
catchment polygon. Best effort, so any network or parse failure yields no
competitor sites rather than breaking the overlay.
"""

from __future__ import annotations

import logging
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
        size = str(props.get("app_size", "")).lower()
        text = " ".join(
            str(props.get(k, "")) for k in ("description", "app_type", "name")
        ).lower()
        if size != "large" and not any(k in text for k in _RESIDENTIAL):
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


def fetch_competitor_sites(
    geometry: dict | None,
    base_url: str,
    lookback_days: int,
    limit: int = 400,
) -> list[dict]:
    """Residential planning applications inside the catchment, from PlanIt."""
    if not geometry:
        return []
    try:
        poly = shape(geometry)
    except Exception:
        return []
    minx, miny, maxx, maxy = poly.bounds  # lng_min, lat_min, lng_max, lat_max
    # PlanIt bbox is sw_lat,sw_lng,ne_lat,ne_lng.
    params = {
        "bbox": f"{miny},{minx},{maxy},{maxx}",
        "pg_sz": min(limit, 400),
        "start_date": (date.today() - timedelta(days=lookback_days)).isoformat(),
    }
    url = f"{base_url.rstrip('/')}/api/applics/geojson"
    try:
        with httpx.Client(
            timeout=20.0, headers={"User-Agent": "LandLynk/1.0 (+catchment overlay)"}
        ) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # pragma: no cover - network path, best effort
        log.warning("PlanIt fetch failed: %s", exc)
        return []
    return _residential_sites_from_geojson(data, poly)[:limit]
