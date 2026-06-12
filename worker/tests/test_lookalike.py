"""The lookalike signal scores areas by similarity to a brand's best locations."""

from __future__ import annotations

import pytest
from test_scoring import make_profile

from landlynk_worker.scoring import ScoringConfig
from landlynk_worker.scoring.score import (
    feature_vector,
    mean_feature_vector,
    score_lookalike,
)


def test_feature_vector_scales_and_skips_missing():
    v = feature_vector(make_profile(median_income=50_000, median_age=40))
    assert v["income"] == 0.5  # 50k / 100k
    assert v["median_age"] == 0.4
    # A suppressed feature is simply absent, not zero.
    v2 = feature_vector(make_profile(median_income=None, mean_income=None))
    assert "income" not in v2


def test_mean_feature_vector_averages_present_features():
    a = make_profile(median_income=40_000)
    b = make_profile(median_income=80_000)
    ref = mean_feature_vector([a, b])
    assert ref["income"] == pytest.approx(0.6)  # mean(0.4, 0.8)


def test_score_lookalike_rewards_similarity():
    reference = mean_feature_vector([make_profile(median_income=100_000, median_age=45)])
    cfg = ScoringConfig(lookalike_reference=reference)
    near = score_lookalike(make_profile(median_income=100_000, median_age=45), cfg)
    far = score_lookalike(make_profile(median_income=20_000, median_age=25), cfg)
    assert near.raw_score > far.raw_score
    assert near.raw_score > 0.9


def test_score_lookalike_neutral_without_reference():
    assert score_lookalike(make_profile(), ScoringConfig()).raw_score == 0.0
