"""Stage 7 output: KML for Google Earth.

Render the catchment polygon plus colour-coded area pins with info balloons,
foldered for toggling (SCOPING.md Section 7, step 7). The KML balloon is one of
the four surfaces the single Battlecard payload renders to. Pin colour follows
the priority band so the KML matches the in-app map.

Retained as a secondary output for stakeholders who prefer Google Earth.
"""

from __future__ import annotations

# KML colours are aabbggrr (alpha, blue, green, red). Map the priority bands to
# the same semantic colours used across the app.
_BAND_KML_COLOR = {
    "high": "ff59c734",  # green  #34C759
    "mid": "ff0095ff",  # orange #FF9500
    "low": "ff303bff",  # red    #FF3B30
}


def band_to_kml_color(band: str) -> str:
    """Return the aabbggrr KML colour for a priority band."""
    return _BAND_KML_COLOR.get(band, "ffffffff")
