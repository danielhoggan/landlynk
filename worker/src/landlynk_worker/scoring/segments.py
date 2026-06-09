"""Predefined audience segments for segment-first targeting.

A segment is a named bundle of scoring preferences: which age cohorts and tenure
mixes a product is aimed at, plus a sensible bed range. Choosing a segment on the
form (or, later, via a builder profile) lets a user ask "rank this catchment for
first time buyers" rather than hand-tuning preference vectors. Segments feed the
existing transparent scoring; they change the age and tenure preference vectors
that score_age_skew and score_tenure_signal already consume.

The library is deliberately small and explainable. Builder profiles reference a
segment by id, so this is the shared vocabulary for targeting.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .profile import ScoringConfig


@dataclass(frozen=True)
class Segment:
    id: str
    label: str
    description: str
    age_preference: dict[str, float]
    tenure_preference: dict[str, float]
    bed_range: str


SEGMENTS: dict[str, Segment] = {
    "first_time_buyer": Segment(
        id="first_time_buyer",
        label="First time buyers",
        description="Young renters stepping onto the ladder. Compact homes.",
        age_preference={"age_16_34": 1.0, "age_35_54": 0.3},
        tenure_preference={"private_rented": 1.0, "owns_with_mortgage": 0.4},
        bed_range="2 to 3",
    ),
    "second_stepper": Segment(
        id="second_stepper",
        label="Second steppers",
        description="Mortgaged owners trading up. Three bed family starts.",
        age_preference={"age_35_54": 1.0, "age_16_34": 0.4, "age_0_15": 0.4},
        tenure_preference={"owns_with_mortgage": 1.0, "private_rented": 0.3},
        bed_range="3 to 4",
    ),
    "growing_family": Segment(
        id="growing_family",
        label="Growing families",
        description="Mid-life households with children. Larger family homes.",
        age_preference={"age_35_54": 1.0, "age_0_15": 0.8},
        tenure_preference={"owns_with_mortgage": 1.0, "owns_outright": 0.3},
        bed_range="3 to 5",
    ),
    "downsizer": Segment(
        id="downsizer",
        label="Downsizers",
        description="Older outright owners releasing equity. Low maintenance.",
        age_preference={"age_55_74": 1.0, "age_75_plus": 0.7},
        tenure_preference={"owns_outright": 1.0, "owns_with_mortgage": 0.2},
        bed_range="2 to 3",
    ),
    "high_net_worth": Segment(
        id="high_net_worth",
        label="High net worth",
        description="Affluent established owners. Premium, larger homes.",
        age_preference={"age_35_54": 1.0, "age_55_74": 0.8},
        tenure_preference={"owns_outright": 1.0, "owns_with_mortgage": 0.6},
        bed_range="4 to 5",
    ),
}


def list_segments() -> list[dict]:
    """Plain dicts for the API and the form picker."""
    return [
        {
            "id": s.id,
            "label": s.label,
            "description": s.description,
            "bedRange": s.bed_range,
        }
        for s in SEGMENTS.values()
    ]


def apply_segment(
    config: ScoringConfig,
    segment_id: str,
    *,
    override_bed_range: bool = True,
) -> ScoringConfig:
    """Return a config tuned for the segment.

    Always sets the age and tenure preference vectors (these drive the segment
    lens and are not otherwise exposed). The bed range is set from the segment
    only when override_bed_range is True, so an explicit bed range from the
    caller is preserved.
    """
    seg = SEGMENTS.get(segment_id)
    if seg is None:
        return config
    changes = {
        "age_preference": dict(seg.age_preference),
        "tenure_preference": dict(seg.tenure_preference),
        "segment": seg.id,
    }
    if override_bed_range:
        changes["bed_range"] = seg.bed_range
    return replace(config, **changes)
