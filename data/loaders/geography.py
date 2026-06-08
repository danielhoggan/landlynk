"""Geography loaders: OA to MSOA to LA lookup, and MSOA/LA boundaries.

Sources are the ONS Open Geography Portal (Open Government Licence). The lookup
is a CSV; the boundaries are GeoJSON FeatureCollections. Geometry is written to
PostGIS from each feature's GeoJSON via the shared DB writer.
"""

from __future__ import annotations

import csv
import json

from .base import ReferenceLoader

# ONS column names default to the December 2021 census geography fields. Override
# on the instance if a later vintage renames them.
DEFAULT_LOOKUP_COLUMNS = {
    "oa": "OA21CD",
    "msoa": "MSOA21CD",
    "msoa_name": "MSOA21NM",
    "la": "LAD21CD",
    "la_name": "LAD21NM",
}

DEFAULT_BOUNDARY_KEYS = {
    "MSOA": {"code": "MSOA21CD", "name": "MSOA21NM"},
    "LA": {"code": "LAD21CD", "name": "LAD21NM"},
}


class GeoLookupLoader(ReferenceLoader):
    target_table = "geo_lookup"
    columns = ("oa_code", "msoa_code", "la_code", "msoa_name", "la_name")

    def __init__(self, *args, column_map: dict | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.column_map = column_map or DEFAULT_LOOKUP_COLUMNS

    def fetch(self) -> list[dict]:
        with open(self.source, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))

    def transform(self, raw: list[dict]) -> list[dict]:
        cm = self.column_map
        seen: set[str] = set()
        rows: list[dict] = []
        for record in raw:
            oa = (record.get(cm["oa"]) or "").strip()
            if not oa or oa in seen:
                continue
            seen.add(oa)
            rows.append(
                {
                    "oa_code": oa,
                    "msoa_code": (record.get(cm["msoa"]) or "").strip(),
                    "la_code": (record.get(cm["la"]) or "").strip(),
                    "msoa_name": (record.get(cm["msoa_name"]) or "").strip() or None,
                    "la_name": (record.get(cm["la_name"]) or "").strip() or None,
                }
            )
        return rows


class BoundariesLoader(ReferenceLoader):
    target_table = "geo_boundaries"
    columns = ("area_code", "area_type", "area_name", "geom")
    geometry_columns = {"geom": "ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"}

    def __init__(
        self, *args, area_type: str = "MSOA", keys: dict | None = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        if area_type not in ("MSOA", "LA"):
            raise ValueError(f"area_type must be MSOA or LA, got {area_type}")
        self.area_type = area_type
        self.keys = keys or DEFAULT_BOUNDARY_KEYS[area_type]

    def fetch(self) -> dict:
        with open(self.source, encoding="utf-8") as fh:
            return json.load(fh)

    def transform(self, raw: dict) -> list[dict]:
        features = raw.get("features") or []
        rows: list[dict] = []
        for feature in features:
            props = feature.get("properties") or {}
            geometry = feature.get("geometry")
            code = (props.get(self.keys["code"]) or "").strip()
            if not code or geometry is None:
                continue
            rows.append(
                {
                    "area_code": code,
                    "area_type": self.area_type,
                    "area_name": (props.get(self.keys["name"]) or "").strip() or None,
                    # Serialised so PostGIS ST_GeomFromGeoJSON can parse it.
                    "geom": json.dumps(geometry),
                }
            )
        return rows
