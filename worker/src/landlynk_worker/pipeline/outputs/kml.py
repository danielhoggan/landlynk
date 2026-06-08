"""Stage 7 output: KML for Google Earth.

Render the catchment polygon plus colour-coded area pins with info balloons,
foldered for toggling (SCOPING.md Section 7, step 7). The KML balloon is one of
the four surfaces the single Battlecard payload renders to. Pin colour follows
the priority band so the KML matches the in-app map.

KML is emitted directly as XML rather than via a third-party library, so the
worker has no fragile native build dependency. Geometry handling uses Shapely,
which is already a core dependency.

Retained as a secondary output for stakeholders who prefer Google Earth.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from shapely.geometry import shape

# KML colours are aabbggrr (alpha, blue, green, red). Map the priority bands to
# the same semantic colours used across the app.
_BAND_KML_COLOR = {
    "high": "ff59c734",  # green  #34C759
    "mid": "ff0095ff",  # orange #FF9500
    "low": "ff303bff",  # red    #FF3B30
}

_BAND_FOLDER = {"high": "High priority", "mid": "Mid priority", "low": "Low priority"}


def band_to_kml_color(band: str) -> str:
    """Return the aabbggrr KML colour for a priority band."""
    return _BAND_KML_COLOR.get(band, "ffffffff")


def _translucent(aabbggrr: str) -> str:
    """Halve the alpha of an aabbggrr colour for area fills."""
    return "80" + aabbggrr[2:]


def _dv(payload: dict, *keys: str) -> object:
    """Walk a nested Battlecard payload and return a DataValue's value, or None."""
    node: object = payload
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    if isinstance(node, dict):
        return node.get("value")
    return node


def _fmt(value: object, *, money: bool = False, pct: bool = False) -> str:
    if value is None:
        return "Not available"
    if money:
        return f"£{value:,.0f}"
    if pct:
        return f"{value:.1f}%"
    if isinstance(value, (int, float)):
        return f"{value:,.0f}"
    return str(value)


def _coords(points: list) -> str:
    """Format a coordinate sequence as KML lng,lat,0 tuples."""
    return " ".join(f"{x},{y},0" for x, y in points)


def _balloon_html(area: dict, card: dict | None) -> str:
    """Compact Battlecard balloon for an area pin. One payload, four surfaces."""
    name = escape(str(area.get("name", area.get("areaCode", ""))))
    rows = [
        f"<b>#{area.get('rank')} {name}</b>",
        f"{area.get('band', '')} priority, score {area.get('score')}",
    ]
    if card:
        ks = card.get("visualSummary", {}).get("keyStatistics", {})
        rows.append(
            "Average income: " + _fmt(_dv(ks, "averageHouseholdIncome"), money=True)
        )
        rows.append(
            "Owner occupied: " + _fmt(_dv(ks, "ownerOccupiedPercentage"), pct=True)
        )
        rows.append("Median age: " + _fmt(_dv(ks, "medianAge")))
        rows.append("Population in catchment: " + _fmt(_dv(ks, "populationCatchment")))
        positioning = card.get("pricingRationale", {}).get("positioning")
        if positioning:
            rows.append("<i>" + escape(positioning) + "</i>")
    # HTML lives inside CDATA so Google Earth renders it as a rich balloon.
    return "<![CDATA[" + "<br/>".join(rows) + "]]>"


def _polygon_placemarks(geometry: dict, color: str) -> list[str]:
    """KML Placemark XML for a Polygon or MultiPolygon geometry."""
    geom = shape(geometry)
    polygons = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    out: list[str] = []
    for poly in polygons:
        inner = "".join(
            "<innerBoundaryIs><LinearRing><coordinates>"
            f"{_coords(list(ring.coords))}"
            "</coordinates></LinearRing></innerBoundaryIs>"
            for ring in poly.interiors
        )
        out.append(
            "<Placemark><Style>"
            f"<PolyStyle><color>{color}</color></PolyStyle>"
            f"<LineStyle><color>{color}</color><width>1</width></LineStyle>"
            "</Style><Polygon>"
            "<outerBoundaryIs><LinearRing><coordinates>"
            f"{_coords(list(poly.exterior.coords))}"
            "</coordinates></LinearRing></outerBoundaryIs>"
            f"{inner}"
            "</Polygon></Placemark>"
        )
    return out


def _point_placemark(
    name: str, lng: float, lat: float, color: str, description: str
) -> str:
    return (
        f"<Placemark><name>{escape(name)}</name>"
        f"<description>{description}</description>"
        f"<Style><IconStyle><color>{color}</color></IconStyle></Style>"
        f"<Point><coordinates>{lng},{lat},0</coordinates></Point></Placemark>"
    )


def _folder(name: str, children: list[str]) -> str:
    return f"<Folder><name>{escape(name)}</name>{''.join(children)}</Folder>"


def render_catchment_kml(catchment: dict, battlecards: dict[str, dict]) -> str:
    """Render a catchment to KML: isochrone polygon plus foldered area pins.

    ``catchment`` is the stored catchment shape (isochrone geometry, and areas
    with geometry, name, band, rank and score). ``battlecards`` maps area code to
    the stored Battlecard payload for the pin balloons. Pins are foldered by
    priority band so they can be toggled in Google Earth.
    """
    dev_name = catchment.get("input", {}).get("developmentName", "Catchment")
    body: list[str] = [f"<name>{escape(f'LandLynk - {dev_name}')}</name>"]

    isochrone = catchment.get("isochrone")
    if isochrone:
        body.append(
            _folder("Drive-time catchment", _polygon_placemarks(isochrone, "3c0071e3"))
        )

    coord = catchment.get("coordinate")
    if coord:
        body.append(
            _point_placemark(dev_name, coord["lng"], coord["lat"], "ff000000", "")
        )

    # Area boundaries in one folder, pins foldered by priority band.
    boundary_placemarks: list[str] = []
    band_pins: dict[str, list[str]] = {}
    for area in catchment.get("areas", []):
        band = area.get("band", "low")
        color = band_to_kml_color(band)
        geometry = area.get("geometry")
        if geometry:
            boundary_placemarks.extend(
                _polygon_placemarks(geometry, _translucent(color))
            )
            point = shape(geometry).representative_point()
            pin = _point_placemark(
                f"#{area.get('rank')} {area.get('name', '')}",
                point.x,
                point.y,
                color,
                _balloon_html(area, battlecards.get(area.get("areaCode"))),
            )
            band_pins.setdefault(band, []).append(pin)

    if boundary_placemarks:
        body.append(_folder("Area boundaries", boundary_placemarks))
    for band in ("high", "mid", "low"):
        if band in band_pins:
            body.append(_folder(_BAND_FOLDER[band], band_pins[band]))

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        f"{''.join(body)}"
        "</Document></kml>"
    )
