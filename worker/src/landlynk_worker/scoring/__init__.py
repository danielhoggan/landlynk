"""Pure, testable scoring for area prioritisation."""

from .profile import (
    AgeProfile,
    AreaProfile,
    PriceBand,
    ScoringConfig,
    TenureMix,
)
from .score import (
    Contribution,
    ScoreBreakdown,
    SignalScore,
    band_for_score,
    compute_score,
    score_addressable_scale,
    score_age_skew,
    score_household_type,
    score_income_fit,
    score_tenure_signal,
)

__all__ = [
    "AgeProfile",
    "AreaProfile",
    "PriceBand",
    "ScoringConfig",
    "TenureMix",
    "Contribution",
    "ScoreBreakdown",
    "SignalScore",
    "band_for_score",
    "compute_score",
    "score_addressable_scale",
    "score_age_skew",
    "score_household_type",
    "score_income_fit",
    "score_tenure_signal",
]
