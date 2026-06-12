"""Static catchment map for exports: the catchment over an OpenStreetMap basemap.

The in-app map uses vector tiles, but exports need a raster image. We stitch
OpenStreetMap raster tiles for the catchment's bounding box and draw the
catchment polygon and a location marker over them, giving the surrounding
context the bare silhouette lacked.

OSM tiles are open (ODbL); usage carries an attribution requirement and a fair
use policy, so we send a descriptive User-Agent, keep volume low (one small
thumbnail per export) and cache results. Everything is best effort: any network
or rendering problem returns None and the caller falls back to the vector
silhouette, so an export never fails on the map.
"""

from __future__ import annotations

import io
import math

import httpx

from .mapshape import largest_ring

# Composed maps cached by bounding box and size, so repeated exports of the same
# catchment do not refetch tiles (and stay within OSM fair use).
_CACHE: dict[tuple, bytes | None] = {}

_TILE = 256
_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_HEADERS = {"User-Agent": "LandLynk/1.0 (geographic intelligence engine)"}
_FILL = (201, 162, 75, 90)  # gold, translucent
_OUTLINE = (10, 31, 68, 230)  # navy


def _lonlat_to_px(lon: float, lat: float, z: int) -> tuple[float, float]:
    n = 2**z
    x = (lon + 180.0) / 360.0 * n * _TILE
    lat_r = math.radians(lat)
    y = (1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * n * _TILE
    return x, y


def _pick_zoom(
    minlon: float,
    minlat: float,
    maxlon: float,
    maxlat: float,
    width: int,
    height: int,
) -> int:
    """Largest zoom where the bounding box still fits the image, with margin."""
    for z in range(13, 3, -1):
        x0, y1 = _lonlat_to_px(minlon, maxlat, z)
        x1, y0 = _lonlat_to_px(maxlon, minlat, z)
        if (x1 - x0) <= width * 0.9 and (y1 - y0) <= height * 0.9:
            return z
    return 4


def catchment_png(
    geometry: dict | None,
    lat: float | None = None,
    lng: float | None = None,
    width: int = 620,
    height: int = 460,
) -> bytes | None:
    """Render the catchment over an OSM basemap as PNG bytes, or None on failure."""
    ring = largest_ring(geometry)
    if len(ring) < 3:
        return None
    key = (
        round(min(p[0] for p in ring), 4),
        round(min(p[1] for p in ring), 4),
        round(max(p[0] for p in ring), 4),
        round(max(p[1] for p in ring), 4),
        width,
        height,
    )
    if key in _CACHE:
        return _CACHE[key]
    try:
        png = _render(geometry, lat, lng, width, height)
    except Exception:  # network, tile or draw failure: caller uses the silhouette
        png = None
    _CACHE[key] = png
    return png


def _render(
    geometry: dict,
    lat: float | None,
    lng: float | None,
    width: int,
    height: int,
) -> bytes | None:
    from PIL import Image, ImageDraw

    ring = largest_ring(geometry)
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    minlon, maxlon = min(lons), max(lons)
    minlat, maxlat = min(lats), max(lats)
    z = _pick_zoom(minlon, minlat, maxlon, maxlat, width, height)

    cx, cy = _lonlat_to_px((minlon + maxlon) / 2, (minlat + maxlat) / 2, z)
    origin_x = cx - width / 2
    origin_y = cy - height / 2

    canvas = Image.new("RGBA", (width, height), (233, 231, 225, 255))
    tx0 = int(origin_x // _TILE)
    ty0 = int(origin_y // _TILE)
    tx1 = int((origin_x + width) // _TILE)
    ty1 = int((origin_y + height) // _TILE)
    n = 2**z
    with httpx.Client(timeout=5.0, headers=_HEADERS) as client:
        for tx in range(tx0, tx1 + 1):
            for ty in range(ty0, ty1 + 1):
                if not (0 <= tx < n and 0 <= ty < n):
                    continue
                resp = client.get(_TILE_URL.format(z=z, x=tx, y=ty))
                if resp.status_code != 200:
                    return None
                tile = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                canvas.paste(
                    tile, (tx * _TILE - int(origin_x), ty * _TILE - int(origin_y))
                )

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    pts = []
    for lon, plat in ring:
        px, py = _lonlat_to_px(lon, plat, z)
        pts.append((px - origin_x, py - origin_y))
    draw.polygon(pts, fill=_FILL, outline=_OUTLINE)
    if lat is not None and lng is not None:
        mx, my = _lonlat_to_px(lng, lat, z)
        mx -= origin_x
        my -= origin_y
        r = 6
        draw.ellipse(
            [mx - r, my - r, mx + r, my + r], fill=(10, 31, 68, 255), outline="white"
        )

    out = Image.alpha_composite(canvas, overlay).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()
