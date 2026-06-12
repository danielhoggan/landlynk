"""Static catchment map: compositing with a stubbed tile, and offline fallback."""

from __future__ import annotations

import io

import httpx
from PIL import Image

from landlynk_worker.battlecard import staticmap_render as sm

_POLY = {
    "type": "Polygon",
    "coordinates": [
        [[-3.6, 50.7], [-3.4, 50.75], [-3.3, 50.7], [-3.5, 50.6], [-3.6, 50.7]]
    ],
}


def _fake_tile() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (220, 220, 210)).save(buf, format="PNG")
    return buf.getvalue()


def test_catchment_png_composites_with_tiles(monkeypatch):
    sm._CACHE.clear()
    tile = _fake_tile()

    class FakeResp:
        status_code = 200
        content = tile

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            return FakeResp()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    png = sm.catchment_png(_POLY, 50.7, -3.5, width=300, height=220)
    assert png is not None
    img = Image.open(io.BytesIO(png))
    assert img.size == (300, 220)


def test_catchment_png_none_without_tiles(monkeypatch):
    sm._CACHE.clear()

    class Boom:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "Client", Boom)
    assert sm.catchment_png(_POLY, 50.7, -3.5) is None


def test_catchment_png_none_for_empty_geometry():
    assert sm.catchment_png({"type": "Polygon", "coordinates": []}) is None
