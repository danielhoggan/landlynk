"""Census 2021 loaders: demographics and tenure.

Sources are ONS Census 2021 area tables (via NOMIS bulk CSV, Open Government
Licence). Demographics combines the single year of age table (population, age
bands, median age) with household composition (family household share). Tenure
maps the tenure table to the four product categories as 0..1 shares.

Column labels vary by NOMIS export, so the loaders detect the area code column
and match value columns by substring, configurable per instance. Every share
runs through the shared helpers so suppression stays None, never zero.
"""

from __future__ import annotations

import csv

from .base import ReferenceLoader
from .transforms import (
    age_from_label,
    aggregate_age_bands,
    median_age,
    parse_count,
    share,
)

_AREA_CODE_CANDIDATES = (
    "geography code",
    "GEOGRAPHY_CODE",
    "geography_code",
    "mnemonic",
    "MSOA code",
    "Area code",
)


def find_area_code_field(fieldnames: list[str]) -> str:
    """Return the column holding the area code, trying the known candidates."""
    lookup = {f.lower(): f for f in fieldnames}
    for candidate in _AREA_CODE_CANDIDATES:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    raise ValueError(f"No area code column found in {fieldnames}")


def _sum_matching(
    record: dict, code_field: str, needles: tuple[str, ...]
) -> int | None:
    """Sum counts across columns whose label contains any needle.

    Returns None only if every matching column is suppressed; a match set with
    no usable values is treated as missing rather than zero.
    """
    matched = [
        parse_count(value)
        for label, value in record.items()
        if label != code_field and any(n in label.lower() for n in needles)
    ]
    if not matched:
        return None
    usable = [v for v in matched if v is not None]
    return sum(usable) if usable else None


def _read_csv(path: str) -> tuple[list[dict], str]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        code_field = find_area_code_field(reader.fieldnames or [])
    return rows, code_field


def _single_year_counts(record: dict, code_field: str) -> dict[int, int | None]:
    """Extract a single year of age to count map from a demographics record."""
    counts: dict[int, int | None] = {}
    for label, value in record.items():
        if label == code_field:
            continue
        age = age_from_label(label)
        if age is None:
            continue
        counts[age] = parse_count(value)
    return counts


class CensusDemographicsLoader(ReferenceLoader):
    """Loads population, age bands, median age and family household share.

    Combines the single year of age table (``source``) with the household
    composition table (``households_source``), joined on area code.
    """

    target_table = "census_demographics"
    columns = (
        "area_code",
        "area_type",
        "population",
        "households",
        "age_0_15",
        "age_16_34",
        "age_35_54",
        "age_55_74",
        "age_75_plus",
        "median_age",
        "family_household_share",
    )

    def __init__(
        self,
        spec,
        source: str,
        households_source: str,
        area_type: str = "MSOA",
        db=None,
    ) -> None:
        super().__init__(spec, source, db)
        self.households_source = households_source
        self.area_type = area_type

    def fetch(self) -> dict:
        age_rows, age_code = _read_csv(self.source)
        hh_rows, hh_code = _read_csv(self.households_source)
        return {
            "age": (age_rows, age_code),
            "households": (hh_rows, hh_code),
        }

    def transform(self, raw: dict) -> list[dict]:
        age_rows, age_code = raw["age"]
        hh_rows, hh_code = raw["households"]

        households_by_area: dict[str, tuple[int | None, float | None]] = {}
        for record in hh_rows:
            code = (record.get(hh_code) or "").strip()
            if not code:
                continue
            total = _sum_matching(record, hh_code, ("all households",))
            family = _sum_matching(record, hh_code, ("single family", "one family"))
            households_by_area[code] = (total, share(family, total))

        rows: list[dict] = []
        for record in age_rows:
            code = (record.get(age_code) or "").strip()
            if not code:
                continue
            counts = _single_year_counts(record, age_code)
            bands = aggregate_age_bands(counts)
            population = sum(v for v in counts.values() if v is not None) or None
            households, family_share = households_by_area.get(code, (None, None))
            rows.append(
                {
                    "area_code": code,
                    "area_type": self.area_type,
                    "population": population,
                    "households": households,
                    **bands,
                    "median_age": median_age(counts),
                    "family_household_share": family_share,
                }
            )
        return rows


class CensusTenureLoader(ReferenceLoader):
    """Loads the tenure split as 0..1 shares of all households."""

    target_table = "census_tenure"
    columns = (
        "area_code",
        "area_type",
        "owns_outright",
        "owns_with_mortgage",
        "social_rented",
        "private_rented",
    )

    def __init__(self, spec, source: str, area_type: str = "MSOA", db=None) -> None:
        super().__init__(spec, source, db)
        self.area_type = area_type

    def fetch(self) -> tuple[list[dict], str]:
        return _read_csv(self.source)

    def transform(self, raw: tuple[list[dict], str]) -> list[dict]:
        records, code_field = raw
        rows: list[dict] = []
        for record in records:
            code = (record.get(code_field) or "").strip()
            if not code:
                continue
            total = _sum_matching(record, code_field, ("all households",))
            rows.append(
                {
                    "area_code": code,
                    "area_type": self.area_type,
                    "owns_outright": share(
                        _sum_matching(record, code_field, ("owns outright",)), total
                    ),
                    "owns_with_mortgage": share(
                        _sum_matching(
                            record, code_field, ("mortgage", "shared ownership")
                        ),
                        total,
                    ),
                    "social_rented": share(
                        _sum_matching(record, code_field, ("social rented",)), total
                    ),
                    "private_rented": share(
                        _sum_matching(
                            record, code_field, ("private rented", "rent free")
                        ),
                        total,
                    ),
                }
            )
        return rows
