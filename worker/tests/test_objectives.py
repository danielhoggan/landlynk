"""Objectives reweight the same scoring engine and frame the commentary."""

from __future__ import annotations

from test_scoring import make_profile

from landlynk_worker.api_models import (
    CatchmentJobRequest,
    ScoringConfigModel,
    to_scoring_config,
)
from landlynk_worker.scoring import ScoringConfig, compute_score
from landlynk_worker.scoring.objectives import (
    OBJECTIVES,
    apply_objective,
    list_objectives,
)
from landlynk_worker.scoring.score import (
    score_green_space,
    score_income_level,
    score_low_deprivation,
)


def test_list_objectives_carries_weight_presets():
    objs = {o["id"]: o for o in list_objectives()}
    assert "wealth_management" in objs
    assert objs["wealth_management"]["weights"]["income_level"] > 0
    assert objs["wealth_management"]["segment"] == "high_net_worth"


def test_apply_objective_sets_weights_and_segment():
    cfg = apply_objective(ScoringConfig(), "wealth_management")
    assert cfg.objective == "wealth_management"
    assert cfg.weights == OBJECTIVES["wealth_management"].weights
    # The objective's default segment is applied when none is set.
    assert cfg.segment == "high_net_worth"


def test_income_level_rewards_affluence():
    rich = score_income_level(make_profile(median_income=120_000), ScoringConfig())
    poor = score_income_level(make_profile(median_income=22_000), ScoringConfig())
    assert rich.raw_score > poor.raw_score


def test_context_signals_handle_missing_data():
    # No context metrics -> neutral 0.0, never a crash or a coerced value.
    p = make_profile(context={})
    assert score_low_deprivation(p, ScoringConfig()).raw_score == 0.0
    assert score_green_space(p, ScoringConfig()).raw_score == 0.0
    # With data, deprivation decile 9 of 10 scores high.
    p2 = make_profile(context={"imd_decile": 9.0})
    assert score_low_deprivation(p2, ScoringConfig()).raw_score == 0.9


def test_wealth_objective_ranks_affluent_area_higher_than_home_sales():
    affluent = make_profile(
        median_income=130_000, context={"imd_decile": 10.0, "crime_per_1k": 20.0}
    )
    wealth = apply_objective(ScoringConfig(), "wealth_management")
    home = apply_objective(ScoringConfig(), "home_sales")
    assert (
        compute_score(affluent, wealth).total
        > compute_score(affluent, home).total
    )


def test_to_scoring_config_applies_objective_weights_when_no_weights_given():
    req = CatchmentJobRequest(
        kind="postcode",
        value="NN15 7FJ",
        developmentName="Test",
        config=ScoringConfigModel(objective="wealth_management"),
    )
    cfg = to_scoring_config(req)
    assert cfg.objective == "wealth_management"
    assert cfg.weights["income_level"] > 0
