"""Business objectives for objective-first targeting.

An objective is what the user is trying to do with the catchment: sell homes,
source land, find high net worth areas for wealth management, site a store, and
so on. It is a named bundle of scoring weights over the signal library (see
scoring/score.py), plus an AI framing line and the data points most relevant to
that objective. Choosing an objective reweights the same transparent engine so
"good" areas mean different things for different strategies, without forking the
scoring code.

The registry is deliberately data-driven: adding an objective is one entry here,
no engine changes. Weights need not sum to 1; they are normalised at scoring
time. Signals not named simply carry no weight for that objective.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .profile import ScoringConfig


@dataclass(frozen=True)
class Objective:
    id: str
    label: str
    description: str
    # Weights over signal names in scoring/score.py SCORERS.
    weights: dict[str, float]
    # One line that frames the AI commentary to the objective.
    ai_framing: str
    # Context metric / signal keys most relevant to this objective, surfaced as
    # objective-specific data on the outputs.
    highlight: tuple[str, ...] = ()
    # Optional default audience segment (scoring/segments.py) for this objective.
    segment: str | None = None


OBJECTIVES: dict[str, Objective] = {
    "home_sales": Objective(
        id="home_sales",
        label="Home sales and marketing",
        description="Rank areas by fit to a housing scheme's buyers and price.",
        weights={
            "income_fit": 0.30,
            "tenure_signal": 0.20,
            "age_skew": 0.20,
            "addressable_scale": 0.20,
            "household_type": 0.10,
        },
        ai_framing=(
            "Frame the commentary for a housebuilder marketing this scheme to "
            "local buyers: who they are, the messages that land, the price story."
        ),
        highlight=("income_fit", "household_type", "schools"),
    ),
    "land_acquisition": Objective(
        id="land_acquisition",
        label="Land acquisition and appraisal",
        description="Favour demand, scale and sales-value upside for site sourcing.",
        weights={
            "addressable_scale": 0.30,
            "income_fit": 0.20,
            "income_level": 0.20,
            "low_deprivation": 0.15,
            "household_type": 0.15,
        },
        ai_framing=(
            "Frame the commentary for a land or development team appraising a "
            "site: demand depth, exit values and the case to acquire here."
        ),
        highlight=("addressable_scale", "income_level", "low_deprivation"),
    ),
    "wealth_management": Objective(
        id="wealth_management",
        label="Wealth management (high net worth)",
        description="Target the most affluent areas for high net worth lead generation.",
        weights={
            "income_level": 0.40,
            "low_deprivation": 0.25,
            "low_crime": 0.15,
            "green_space": 0.10,
            "healthcare_access": 0.10,
        },
        ai_framing=(
            "Frame the commentary for a wealth manager targeting affluent "
            "households: where the high net worth prospects concentrate and why."
        ),
        highlight=("income_level", "low_deprivation", "low_crime"),
        segment="high_net_worth",
    ),
    "retail_site": Objective(
        id="retail_site",
        label="Retail and leisure site selection",
        description="Favour population scale and spend potential for a store or venue.",
        weights={
            "addressable_scale": 0.45,
            "income_level": 0.30,
            "low_crime": 0.25,
        },
        ai_framing=(
            "Frame the commentary for a retail or leisure operator siting a "
            "location: catchment size, spend potential and the trading case."
        ),
        highlight=("addressable_scale", "income_level"),
    ),
}


def list_objectives() -> list[dict]:
    """Plain dicts for the API and the form picker (weights included so the UI
    can show and let the user tune the objective's preset)."""
    return [
        {
            "id": o.id,
            "label": o.label,
            "description": o.description,
            "weights": dict(o.weights),
            "segment": o.segment,
        }
        for o in OBJECTIVES.values()
    ]


def apply_objective(
    config: ScoringConfig,
    objective_id: str,
    *,
    set_weights: bool = True,
    set_segment: bool = True,
) -> ScoringConfig:
    """Return a config tuned for the objective.

    Records the objective id. Sets the weight preset when ``set_weights`` (so a
    non-web caller that omits weights still gets the objective's profile, while
    the web keeps weights in sync itself). Applies the objective's default
    segment when ``set_segment`` and no segment is already set.
    """
    obj = OBJECTIVES.get(objective_id)
    if obj is None:
        return config
    changes: dict = {"objective": obj.id}
    if set_weights:
        changes["weights"] = dict(obj.weights)
    config = replace(config, **changes)
    if set_segment and obj.segment and config.segment is None:
        from .segments import apply_segment

        config = apply_segment(config, obj.segment, override_bed_range=False)
    return config
