"""Place facts around a searched location, from OpenStreetMap's Overpass API.

The Place setting pack needs street-level texture the area statistics do not
carry: which buses stop nearby and where they run, the closest restaurants and
pubs, the nearest railway station with a walk or drive estimate, shops,
schools, pharmacies, parks and named cycle routes. All of it lives in
OpenStreetMap, which is free and needs no key, so this is a factual fetch, not
a GenAI job.

The public Overpass instances rate-limit and time out on heavy scans, so the
fetch is split into small sequential queries (cheap node scans, bus route
relations, way-mapped amenities, cycle relations), each tried across mirrors
and each optional beyond the first: partial data degrades a section, never the
pack. The result is persisted per run, so the cost is paid once.

Walk and drive times are estimated from straight-line distance (12 min/km
walk, about 2 min/km urban drive) and labelled approximate; real timetable
times need licensed feeds, so bus routes carry their destinations instead of
invented minutes. Parsing is pure and unit tested offline.
"""

from __future__ import annotations

import logging
import math
import time

import httpx

log = logging.getLogger(__name__)

OVERPASS_MIRRORS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

_UA = {"User-Agent": "LandLynk/1.0 (geographic intelligence engine)"}

_EATERY_TYPES = ("restaurant", "cafe", "pub", "fast_food", "bar")


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


def _run_query(
    query: str,
    client: httpx.Client | None = None,
    deadline: float | None = None,
) -> dict:
    """POST one Overpass query, trying each mirror until one answers.

    The deadline (time.monotonic()) bounds the whole attempt: each mirror gets
    at most the remaining budget, and no mirror is tried with under 4 seconds
    left. The mirrors rate-limit per IP, so failures are normal; the caller
    decides which queries are required and which degrade.
    """
    last: Exception | None = None
    for base in OVERPASS_MIRRORS:
        remaining = (deadline - time.monotonic()) if deadline else 15.0
        if remaining < 4:
            break
        timeout = min(15.0, remaining)
        try:
            if client is not None:
                resp = client.post(base, data={"data": query})
            else:
                with httpx.Client(timeout=timeout, headers=_UA) as owned:
                    resp = owned.post(base, data={"data": query})
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # pragma: no cover - network path
            log.warning("Overpass mirror failed (%s): %s", base, exc)
            last = exc
    raise last or RuntimeError("No Overpass mirror answered in the time budget")


def _walk_drive(distance_km: float) -> tuple[int, int]:
    """Approximate walk and drive minutes from straight-line distance."""
    return max(1, round(distance_km * 12)), max(2, round(distance_km * 2))


def _coord(element: dict) -> tuple[float, float] | None:
    """The element's coordinate: nodes carry lat/lon, ways carry a center."""
    lat = element.get("lat")
    lng = element.get("lon")
    if lat is None or lng is None:
        center = element.get("center") or {}
        lat, lng = center.get("lat"), center.get("lon")
    if lat is None or lng is None:
        return None
    return float(lat), float(lng)


def _named(elements: list, lat: float, lng: float, match) -> list[dict]:  # noqa: ANN001
    """Named places matching a predicate, deduped by name, nearest first."""
    out: list[dict] = []
    seen: set = set()
    for e in elements:
        tags = e.get("tags") or {}
        kind = match(tags)
        if not kind or not tags.get("name"):
            continue
        coord = _coord(e)
        if coord is None:
            continue
        key = tags["name"].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "name": tags["name"].strip(),
                "type": kind,
                "distanceM": round(_haversine_m(lat, lng, *coord)),
            }
        )
    out.sort(key=lambda s: s["distanceM"])
    return out


def parse_place_nodes(elements: list, lat: float, lng: float) -> dict:
    """Transit, eateries, shops, schools, health and parks from Overpass
    elements (nodes or ways with centers). Pure, unit tested offline."""
    stops: list[dict] = []
    stations: list[dict] = []
    for e in elements:
        tags = e.get("tags") or {}
        coord = _coord(e)
        if coord is None:
            continue
        dist = _haversine_m(lat, lng, *coord)
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
            metro = tags.get("station") in ("light_rail", "subway")
            stations.append(
                {
                    "name": tags.get("name") or "Station",
                    "distanceKm": round(km, 1),
                    "walkMinutes": walk,
                    "driveMinutes": drive,
                    "metro": metro,
                }
            )

    stops.sort(key=lambda s: s["distanceM"])
    stations.sort(key=lambda s: s["distanceKm"])
    # Dedupe same-name stops (paired shelters either side of the road).
    seen: set = set()
    unique_stops = []
    for s in stops:
        if s["name"] in seen:
            continue
        seen.add(s["name"])
        unique_stops.append(s)

    def eatery(tags: dict) -> str | None:
        return tags.get("amenity") if tags.get("amenity") in _EATERY_TYPES else None

    def shop(tags: dict) -> str | None:
        return (
            tags.get("shop")
            if tags.get("shop") in ("supermarket", "convenience")
            else None
        )

    def school(tags: dict) -> str | None:
        return "school" if tags.get("amenity") == "school" else None

    def health(tags: dict) -> str | None:
        return (
            tags.get("amenity")
            if tags.get("amenity") in ("doctors", "pharmacy", "dentist")
            else None
        )

    def park(tags: dict) -> str | None:
        if tags.get("leisure") in ("park", "nature_reserve"):
            return "park"
        if tags.get("leisure") in ("fitness_centre", "sports_centre"):
            return "leisure"
        return None

    eateries = _named(elements, lat, lng, eatery)
    # Re-walk once for cuisine, cheap and keeps _named generic.
    cuisines = {
        (t.get("name") or "").strip().lower(): (t.get("cuisine") or "")
        .replace(";", ", ")
        for e in elements
        if (t := e.get("tags") or {}).get("amenity") in _EATERY_TYPES
    }
    for item in eateries:
        item["cuisine"] = cuisines.get(item["name"].lower()) or None

    # Nearest station leads regardless of kind: a Metro stop 1.6 km away
    # matters more to a buyer than a mainline station 6 km out. The metro
    # label tells them apart, and the nearest heavy-rail station is always
    # included in the follow-ups when it is not the lead.
    primary = stations[0] if stations else None
    others = [s for s in stations if s is not primary]
    if primary is not None and primary["metro"]:
        first_rail = next((s for s in others if not s["metro"]), None)
        if first_rail is not None:
            others = [
                s for s in others[:2] if s is not first_rail
            ] + [first_rail]
    return {
        "station": primary,
        "otherStations": others[:3],
        "busStops": unique_stops[:6],
        "busRoutes": sorted(
            {r for s in stops for r in s["routes"]}, key=lambda r: (len(r), r)
        )[:16],
        "restaurants": eateries[:12],
        "shops": _named(elements, lat, lng, shop)[:8],
        "schools": _named(elements, lat, lng, school)[:8],
        "health": _named(elements, lat, lng, health)[:8],
        "parks": _named(elements, lat, lng, park)[:8],
    }


def parse_bus_relations(elements: list) -> list[dict]:
    """Bus services from route relations: route number and destinations.

    Grouped by ref (each direction is its own relation), so "21" carries both
    ends of the route. Pure, unit tested offline.
    """
    by_ref: dict[str, list[str]] = {}
    for e in elements:
        tags = e.get("tags") or {}
        if tags.get("route") != "bus":
            continue
        ref = (tags.get("ref") or "").strip()
        if not ref:
            continue
        dest = (tags.get("to") or tags.get("name") or "").strip()
        dests = by_ref.setdefault(ref, [])
        if dest and dest not in dests:
            dests.append(dest)
    return [
        {"ref": ref, "destinations": dests[:2]}
        for ref, dests in sorted(by_ref.items(), key=lambda kv: (len(kv[0]), kv[0]))
    ][:12]


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
    lat: float,
    lng: float,
    client: httpx.Client | None = None,
    budget_s: float = 35.0,
) -> dict:
    """The factual place profile around a pin, inside a hard time budget.

    The first query is required; every later one is best effort, so a
    rate-limited mirror thins a section rather than failing the pack, and the
    budget guarantees the caller (a web request holding a spinner) gets an
    answer in bounded time. Typical happy path is a few seconds; the record is
    persisted per run, so the cost is paid once."""
    nodes_q = f"""[out:json][timeout:20];
(
  node(around:900,{lat},{lng})[highway=bus_stop];
  node(around:8000,{lat},{lng})[railway=station];
  node(around:3000,{lat},{lng})[amenity~"^(restaurant|cafe|pub|fast_food|bar)$"][name];
  node(around:2000,{lat},{lng})[shop~"^(supermarket|convenience)$"][name];
  node(around:2000,{lat},{lng})[amenity~"^(school|doctors|pharmacy|dentist)$"][name];
  node(around:1500,{lat},{lng})[leisure~"^(park|nature_reserve|fitness_centre|sports_centre)$"][name];
);
out 400;"""
    ways_q = f"""[out:json][timeout:20];
(
  way(around:2000,{lat},{lng})[shop=supermarket][name];
  way(around:2000,{lat},{lng})[amenity=school][name];
  way(around:1500,{lat},{lng})[leisure~"^(park|nature_reserve|fitness_centre|sports_centre)$"][name];
);
out tags center 200;"""
    bus_q = f"""[out:json][timeout:20];
relation(around:900,{lat},{lng})[route=bus];
out tags 60;"""
    cycles_q = f"""[out:json][timeout:20];
relation(around:3000,{lat},{lng})[route=bicycle];
out tags 30;"""

    deadline = time.monotonic() + budget_s

    def optional(query: str) -> list:
        if deadline - time.monotonic() < 4:
            return []
        try:
            return _run_query(query, client, deadline).get("elements", [])
        except Exception:
            return []

    elements = _run_query(nodes_q, client, deadline).get("elements", [])
    # Schools, supermarkets and parks are usually mapped as ways (areas), so
    # this second scan is what fills Daily life; degrade quietly if it fails.
    ways = optional(ways_q)
    if not ways:
        log.warning("Overpass ways scan failed; daily-life sections thinner")
    facts = parse_place_nodes(elements + ways, lat, lng)
    facts["busServices"] = parse_bus_relations(optional(bus_q))
    if facts["busServices"]:
        # Relation refs are authoritative; stop tags are the fallback.
        facts["busRoutes"] = [s["ref"] for s in facts["busServices"]]
    facts["cycleRoutes"] = parse_cycle_relations(optional(cycles_q))
    return facts
