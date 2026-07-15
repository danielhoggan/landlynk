"""Place facts around a searched location, from OpenStreetMap's Overpass API.

The Place setting pack needs street-level texture the area statistics do not
carry: which buses stop nearby and where they go, the closest restaurants and
pubs, the nearest railway station with a walk or drive estimate, and any named
cycle routes. All of it lives in OpenStreetMap, which is free and needs no key,
so this is one fast factual fetch, not a GenAI job. Two small queries (heavy
relation scans split from cheap node scans) keep Overpass under its timeout,
and mirrors are tried in turn because the public instances rate-limit.

Walk and drive times are estimated from straight-line distance (12 min/km walk,
about 2 min/km urban drive) and labelled approximate; real timetable times need
licensed feeds. Parsing is pure and unit tested offline.
"""

from __future__ import annotations

import logging
import math

import httpx

log = logging.getLogger(__name__)

OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

_UA = {"User-Agent": "LandLynk/1.0 (geographic intelligence engine)"}


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return 6_371_000 * 2 * math.asin(math.sqrt(a))


def _run_query(query: str, client: httpx.Client | None = None) -> dict:
    """POST one Overpass query, trying each mirror until one answers."""
    last: Exception | None = None
    for base in OVERPASS_MIRRORS:
        try:
            if client is not None:
                resp = client.post(base, data={"data": query})
            else:
                with httpx.Client(timeout=30.0, headers=_UA) as owned:
                    resp = owned.post(base, data={"data": query})
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # pragma: no cover - network path
            log.warning("Overpass mirror failed (%s): %s", base, exc)
            last = exc
    raise last or RuntimeError("No Overpass mirror answered")


def _walk_drive(distance_km: float) -> tuple[int, int]:
    """Approximate walk and drive minutes from straight-line distance."""
    return max(1, round(distance_km * 12)), max(2, round(distance_km * 2))


def parse_place_nodes(elements: list, lat: float, lng: float) -> dict:
    """Bus stops (with route refs), eateries and stations from Overpass nodes.

    Pure, so it is unit tested offline. Distances are from the searched pin.
    """
    stops: list[dict] = []
    eateries: list[dict] = []
    stations: list[dict] = []
    for e in elements:
        tags = e.get("tags") or {}
        elat, elng = e.get("lat"), e.get("lon")
        if elat is None or elng is None:
            continue
        dist = _haversine_m(lat, lng, float(elat), float(elng))
        if tags.get("highway") == "bus_stop":
            routes = [
                r.strip()
                for r in (tags.get("route_ref") or "").split(";")
                if r.strip()
            ]
            stops.append(
                {
                    "name": tags.get("name") or "Bus stop",
                    "distanceM": round(dist),
                    "routes": routes,
                }
            )
        elif tags.get("railway") == "station":
            km = dist / 1000
            walk, drive = _walk_drive(km)
            stations.append(
                {
                    "name": tags.get("name") or "Station",
                    "distanceKm": round(km, 1),
                    "walkMinutes": walk,
                    "driveMinutes": drive,
                }
            )
        elif tags.get("amenity") in ("restaurant", "cafe", "pub"):
            if not tags.get("name"):
                continue
            eateries.append(
                {
                    "name": tags["name"],
                    "type": tags["amenity"],
                    "cuisine": (tags.get("cuisine") or "").replace(";", ", ")
                    or None,
                    "distanceM": round(dist),
                }
            )

    stops.sort(key=lambda s: s["distanceM"])
    eateries.sort(key=lambda s: s["distanceM"])
    stations.sort(key=lambda s: s["distanceKm"])
    # Distinct route numbers across nearby stops, numeric-ish sort for reading.
    routes = sorted(
        {r for s in stops for r in s["routes"]},
        key=lambda r: (len(r), r),
    )
    # Dedupe same-name stops (paired shelters either side of the road).
    seen: set = set()
    unique_stops = []
    for s in stops:
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        unique_stops.append(s)
    return {
        "station": stations[0] if stations else None,
        "otherStations": stations[1:3],
        "busStops": unique_stops[:6],
        "busRoutes": routes[:16],
        "restaurants": eateries[:10],
    }


def parse_cycle_relations(elements: list) -> list[dict]:
    """Named or numbered cycle routes from Overpass relations. Pure."""
    routes: list[dict] = []
    seen: set = set()
    for e in elements:
        tags = e.get("tags") or {}
        if tags.get("route") != "bicycle":
            continue
        ref = (tags.get("ref") or "").strip() or None
        name = (tags.get("name") or "").strip() or None
        if not ref and not name:
            continue
        key = (ref, name)
        if key in seen:
            continue
        seen.add(key)
        routes.append({"ref": ref, "name": name})
    return routes[:6]


def fetch_place_facts(
    lat: float, lng: float, client: httpx.Client | None = None
) -> dict:
    """The factual place profile around a pin: transit, eateries, cycling."""
    nodes_q = f"""[out:json][timeout:20];
(
  node(around:900,{lat},{lng})[highway=bus_stop];
  node(around:1500,{lat},{lng})[amenity~"^(restaurant|cafe|pub)$"];
  node(around:8000,{lat},{lng})[railway=station][station!=subway];
);
out 300;"""
    cycles_q = f"""[out:json][timeout:20];
relation(around:3000,{lat},{lng})[route=bicycle];
out tags 30;"""
    facts = parse_place_nodes(
        _run_query(nodes_q, client).get("elements", []), lat, lng
    )
    try:
        facts["cycleRoutes"] = parse_cycle_relations(
            _run_query(cycles_q, client).get("elements", [])
        )
    except Exception:  # cycling is a nice-to-have; never fail the pack on it
        facts["cycleRoutes"] = []
    return facts
