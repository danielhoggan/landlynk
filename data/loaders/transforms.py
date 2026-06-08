"""Shared, pure transform helpers for the reference loaders.

ONS suppression and rounding are handled here, once, so every loader treats a
suppressed cell as None and never as zero (house-standards.md, data handling).
Age aggregation and median age are derived from the single year of age
distribution, which is the auditable basis for the product age bands.
"""

from __future__ import annotations

import re

# Markers ONS and OS use for suppressed, withheld or not-applicable cells.
# Any of these maps to None, never to zero.
_SUPPRESSION_MARKERS = {"", ":", "-", "c", "x", "n/a", "na", "*", "!", "..", "z"}

# The product age bands, as inclusive single-year ranges.
PRODUCT_AGE_BANDS: list[tuple[str, int, int]] = [
    ("age_0_15", 0, 15),
    ("age_16_34", 16, 34),
    ("age_35_54", 35, 54),
    ("age_55_74", 55, 74),
    ("age_75_plus", 75, 200),
]


def parse_number(raw: object) -> float | None:
    """Parse a numeric cell, returning None for any suppression marker.

    Strips thousands separators and surrounding whitespace. A genuine zero
    stays zero; only suppression markers become None.
    """
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
    """Parse an integer count, preserving suppression as None."""
    value = parse_number(raw)
    return None if value is None else int(round(value))


def share(part: float | None, whole: float | None) -> float | None:
    """Return part/whole as a 0..1 share, or None if either is missing or zero whole."""
    if part is None or whole is None or whole == 0:
        return None
    return part / whole


def age_from_label(label: str) -> int | None:
    """Extract a single year of age from a census column label.

    Handles forms like "Aged 16 years", "Age: 16", "16", "Aged 90 years and over".
    Returns None for labels that are not a single age (totals, ranges).
    """
    lowered = label.lower()
    if "and over" in lowered or "and above" in lowered or "plus" in lowered:
        match = re.search(r"(\d+)", lowered)
        return int(match.group(1)) if match else None
    # Reject explicit ranges like "16 to 19".
    numbers = re.findall(r"\d+", lowered)
    if len(numbers) != 1:
        return None
    return int(numbers[0])


def aggregate_age_bands(
    single_year_counts: dict[int, int | None],
) -> dict[str, int | None]:
    """Sum single year of age counts into the five product bands.

    A band is None only if every contributing year is suppressed; otherwise the
    available years are summed. The "75 plus" band absorbs the open top bucket.
    """
    bands: dict[str, int | None] = {}
    for name, low, high in PRODUCT_AGE_BANDS:
        values = [
            count
            for age, count in single_year_counts.items()
            if low <= age <= high and count is not None
        ]
        any_in_range = any(low <= age <= high for age in single_year_counts)
        bands[name] = sum(values) if values else (None if any_in_range else 0)
    return bands


def median_age(single_year_counts: dict[int, int | None]) -> float | None:
    """Median age from a single year of age distribution.

    Suppressed years are skipped. Returns None when the distribution is empty.
    """
    pairs = sorted(
        (age, count)
        for age, count in single_year_counts.items()
        if count is not None and count > 0
    )
    total = sum(count for _age, count in pairs)
    if total == 0:
        return None
    midpoint = total / 2
    cumulative = 0
    for age, count in pairs:
        cumulative += count
        if cumulative >= midpoint:
            return float(age)
    return float(pairs[-1][0])
