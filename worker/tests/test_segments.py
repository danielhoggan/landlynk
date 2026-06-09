"""Segment-first targeting: a segment changes the preference vectors and ranking."""

from __future__ import annotations

from landlynk_worker.api_models import CatchmentJobRequest, to_scoring_config
from landlynk_worker.scoring import AgeProfile, AreaProfile, TenureMix, compute_score
from landlynk_worker.scoring.profile import ScoringConfig
from landlynk_worker.scoring.segments import SEGMENTS, apply_segment


def _req(**config) -> CatchmentJobRequest:
    return CatchmentJobRequest.model_validate(
        {"kind": "postcode", "value": "X", "developmentName": "D", "config": config}
    )


def test_segment_sets_preferences_and_bed_range():
    cfg = to_scoring_config(_req(segment="downsizer"))
    assert cfg.segment == "downsizer"
    assert cfg.age_preference["age_55_74"] == 1.0
    assert cfg.tenure_preference["owns_outright"] == 1.0
    assert cfg.bed_range == "2 to 3"


def test_explicit_bed_range_overrides_segment():
    cfg = to_scoring_config(_req(segment="downsizer", bedRange="5"))
    assert cfg.bed_range == "5"  # caller wins
    assert cfg.age_preference["age_55_74"] == 1.0  # preferences still applied


def test_segment_changes_ranking_between_cohorts():
    young = AreaProfile(
        "Y",
        "MSOA",
        5000,
        2000,
        40000,
        42000,
        30,
        TenureMix(0.1, 0.3, 0.1, 0.5),
        AgeProfile(0.2, 0.5, 0.2, 0.07, 0.03),
        0.4,
        1.0,
    )
    old = AreaProfile(
        "O",
        "MSOA",
        5000,
        2000,
        40000,
        42000,
        68,
        TenureMix(0.7, 0.1, 0.1, 0.1),
        AgeProfile(0.05, 0.05, 0.2, 0.4, 0.3),
        0.4,
        1.0,
    )
    ftb = apply_segment(ScoringConfig(), "first_time_buyer")
    ds = apply_segment(ScoringConfig(), "downsizer")
    # The young, rented area scores higher for FTB; the old, owned area for downsizers.
    assert compute_score(young, ftb).total > compute_score(old, ftb).total
    assert compute_score(old, ds).total > compute_score(young, ds).total


def test_unknown_segment_is_a_noop():
    base = ScoringConfig()
    assert apply_segment(base, "nope") is base


def test_library_has_five_segments():
    assert len(SEGMENTS) == 5
