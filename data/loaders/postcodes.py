"""Postcode loader: OS CodePoint Open.

Source is OS CodePoint Open (Open Government Licence), a set of CSV files of
postcode centroids in British National Grid eastings and northings. Each is
converted to a WGS84 point with pyproj and written to PostGIS. CodePoint Open
ships without a header; the first columns are postcode, quality, easting,
northing.
"""

from __future__ import annotations

import csv
import json

from pyproj import Transformer

from .base import ReferenceLoader

# British National Grid (EPSG:27700) to WGS84 (EPSG:4326). always_xy gives us
# (lng, lat) from (easting, northing).
_BNG_TO_WGS84 = Transformer.from_crs(27700, 4326, always_xy=True)


def normalise_postcode(raw: str) -> str:
    """Uppercase and strip spaces so lookups are consistent."""
    return "".join(raw.split()).upper()


class PostcodeLoader(ReferenceLoader):
    target_table = "postcode_lookup"
    columns = ("postcode", "geom")
    geometry_columns = {"geom": "ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)"}

    def __init__(self, spec, source: str, has_header: bool = False, db=None) -> None:
        super().__init__(spec, source, db)
        self.has_header = has_header

    def fetch(self) -> list[list[str]]:
        with open(self.source, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
        return rows[1:] if self.has_header else rows

    def transform(self, raw: list[list[str]]) -> list[dict]:
        rows: list[dict] = []
        for record in raw:
            if len(record) < 4:
                continue
            postcode = normalise_postcode(record[0])
            try:
                easting = float(record[2])
                northing = float(record[3])
            except (ValueError, IndexError):
                continue
            # CodePoint Open uses (0, 0) for postcodes with no grid reference.
            if easting == 0 and northing == 0:
                continue
            lng, lat = _BNG_TO_WGS84.transform(easting, northing)
            rows.append(
                {
                    "postcode": postcode,
                    "geom": json.dumps(
                        {"type": "Point", "coordinates": [round(lng, 6), round(lat, 6)]}
                    ),
                }
            )
        return rows
