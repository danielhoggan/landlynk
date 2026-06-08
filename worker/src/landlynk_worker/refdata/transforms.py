"""Pure transforms for server-side reference loading.

Mirrors the standalone loaders in /data so the worker can download and load
reference data itself, with no local commands. ONS suppression is handled here:
a suppressed cell is None, never zero (house-standards.md). Age aggregation and
median age derive from the single year of age distribution.
"""

from __future__ import annotations

import re

_SUPPRESSION_MARKERS = {"", ":", "-", "c", "x", "n/a", "na", "*", "!", "..", "z"}

PRODUCT_AGE_BANDS: list[tuple[str, int, int]] = [
    ("age_0_15", 0, 15),
    ("age_16_34", 16, 34),
    ("age_35_54", 35, 54),
    ("age_55_74", 55, 74),
    ("age_75_plus", 75, 200),
]

# Candidate names for the area-code column across ONS/NOMIS exports.
AREA_CODE_CANDIDATES = (
    "geography code",
    "geography_code",
    "mnemonic",
    "msoa code",
    "msoa21cd",
    "area code",
)


def parse_number(raw: object) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if text.lower() in _SUPPRESSION_MARKERS:
        return None
    cleaned = text.replace(",", "").replace("£", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_count(raw: object) -> int | None:
    value = parse_number(raw)
    return None if value is None else int(round(value))


def share(part: float | None, whole: float | None) -> float | None:
    if part is None or whole is None or whole == 0:
        return None
    return part / whole


def age_from_label(label: str) -> int | None:
    lowered = label.lower()
    if "and over" in lowered or "and above" in lowered or "plus" in lowered:
        match = re.search(r"(\d+)", lowered)
        return int(match.group(1)) if match else None
    numbers = re.findall(r"\d+", lowered)
    if len(numbers) != 1:
        return None
    return int(numbers[0])


def aggregate_age_bands(
    single_year_counts: dict[int, int | None],
) -> dict[str, int | None]:
    bands: dict[str, int | None] = {}
    for name, low, high in PRODUCT_AGE_BANDS:
        values = [
            c
            for age, c in single_year_counts.items()
            if low <= age <= high and c is not None
        ]
        any_in_range = any(low <= age <= high for age in single_year_counts)
        bands[name] = sum(values) if values else (None if any_in_range else 0)
    return bands


def median_age(single_year_counts: dict[int, int | None]) -> float | None:
    pairs = sorted(
        (age, c) for age, c in single_year_counts.items() if c is not None and c > 0
    )
    total = sum(c for _a, c in pairs)
    if total == 0:
        return None
    midpoint = total / 2
    cumulative = 0
    for age, c in pairs:
        cumulative += c
        if cumulative >= midpoint:
            return float(age)
    return float(pairs[-1][0])


def find_area_code_field(fieldnames: list[str]) -> str:
    lookup = {f.lower(): f for f in fieldnames}
    for candidate in AREA_CODE_CANDIDATES:
        if candidate in lookup:
            return lookup[candidate]
    raise ValueError(f"No area code column found in {fieldnames}")


def sum_matching(record: dict, code_field: str, needles: tuple[str, ...]) -> int | None:
    matched = [
        parse_count(v)
        for label, v in record.items()
        if label != code_field and any(n in label.lower() for n in needles)
    ]
    if not matched:
        return None
    usable = [v for v in matched if v is not None]
    return sum(usable) if usable else None


def single_year_counts(record: dict, code_field: str) -> dict[int, int | None]:
    counts: dict[int, int | None] = {}
    for label, value in record.items():
        if label == code_field:
            continue
        age = age_from_label(label)
        if age is None:
            continue
        counts[age] = parse_count(value)
    return counts


def find_column(fieldnames: list[str], needles: tuple[str, ...]) -> str | None:
    lowered = [(f, f.lower()) for f in fieldnames]
    for needle in needles:
        for original, low in lowered:
            if needle in low:
                return original
    return None
