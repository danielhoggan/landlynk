"""Registry for additional area context metrics.

The area_metric table holds values keyed by metric_key; this registry holds how
each one is labelled, formatted and ordered for display, so a loader only needs
to write a key and a value. Adding a public data point is then: a loader that
writes the key, plus an entry here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextMetricDef:
    key: str
    label: str
    unit: str
    # "Higher is better", "Lower is better" or "" for neutral, used by the UI.
    direction: str = ""
    decimals: int = 0


# Display order is the order here.
CONTEXT_METRICS: tuple[ContextMetricDef, ...] = (
    ContextMetricDef(
        "greenspace_minutes", "Nearest green space", "min walk", "Lower is better", 0
    ),
    ContextMetricDef(
        "imd_decile",
        "Deprivation decile",
        "of 10 (10 = least deprived)",
        "Higher is better",
        0,
    ),
    ContextMetricDef("schools_count", "Schools in area", "", "", 0),
    ContextMetricDef(
        "schools_good_pct", "Good or Outstanding schools", "%", "Higher is better", 0
    ),
    ContextMetricDef(
        "crime_per_1k", "Crime rate", "per 1,000 residents", "Lower is better", 0
    ),
    ContextMetricDef("hospital_km", "Nearest hospital", "km", "Lower is better", 1),
    ContextMetricDef(
        "site_capacity", "Brownfield capacity", "dwellings", "Higher is better", 0
    ),
)

_BY_KEY = {m.key: m for m in CONTEXT_METRICS}


def build_context_metrics(values: dict[str, float] | None) -> list[dict]:
    """Shape a {key: value} dict into ordered display rows for the Battlecard."""
    if not values:
        return []
    rows: list[dict] = []
    for m in CONTEXT_METRICS:
        v = values.get(m.key)
        if v is None:
            continue
        rows.append(
            {
                "key": m.key,
                "label": m.label,
                "value": round(float(v), m.decimals) if m.decimals else round(float(v)),
                "unit": m.unit,
                "direction": m.direction,
            }
        )
    return rows
