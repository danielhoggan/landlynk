"""Area profile and scoring config.

These are plain data carriers fed into the pure scoring functions. They take
data in and the scoring functions return scores out, with no side effects, so
scoring is testable and reproducible (house-standards.md, code conventions).

ONS suppression is explicit: a suppressed or unavailable cell is ``None``,
never silently coerced to zero. The scoring functions account for ``None``
rather than treating it as a value.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TenureMix:
    """Tenure shares for an area, each a proportion in 0..1 or None if suppressed."""

    owns_outright: float | None
    owns_with_mortgage: float | None
    social_rented: float | None
    private_rented: float | None


@dataclass(frozen=True)
class AgeProfile:
    """Population shares by age band, each a proportion in 0..1 or None."""

    age_0_15: float | None
    age_16_34: float | None
    age_35_54: float | None
    age_55_74: float | None
    age_75_plus: float | None


@dataclass(frozen=True)
class AreaProfile:
    """Everything the scoring needs for one area. Pure input, no behaviour."""

    area_code: str
    area_type: str  # "MSOA" or "LA"
    population: int | None
    households: int | None
    median_income: float | None
    mean_income: float | None
    median_age: float | None
    tenure: TenureMix
    age: AgeProfile
    family_household_share: float | None
    # Proportion of this area inside the drive-time isochrone, 0..1.
    proportion_inside: float
    # Local median house price (ONS HPSSA). Optional; for the builder use case.
    median_house_price: float | None = None
    # Additional public data points (green space, deprivation, crime), keyed by
    # metric_key. Shown as Local context on the Battlecard, not yet scored.
    context: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceBand:
    frm: float
    to: float

    @property
    def midpoint(self) -> float:
        return (self.frm + self.to) / 2.0


@dataclass(frozen=True)
class ScoringConfig:
    """Weights and targets, tuned per project and stored with the catchment.

    Weights need not sum to 1; they are normalised at scoring time so configs
    stay easy to edit. Targets express the product's intended audience so the
    same engine serves a family scheme and a downsizer scheme differently
    (SCOPING.md Section 8).
    """

    weights: dict[str, float] = field(
        default_factory=lambda: {
            "income_fit": 0.30,
            "tenure_signal": 0.20,
            "age_skew": 0.20,
            "addressable_scale": 0.20,
            "household_type": 0.10,
        }
    )
    price_band: PriceBand = field(default_factory=lambda: PriceBand(250_000, 400_000))
    # Whether the caller set an explicit price. When False the price band is a
    # neutral default used for ranking only, and outputs must not present a price
    # story the user never chose.
    price_set: bool = True
    bed_range: str = "2 to 5"
    overlap_threshold: float = 0.10
    drive_time_minutes: int = 30
    # Catchment shape: "drive_time" builds an isochrone, "radius" a circular
    # buffer of radius_km. Radius suits dense cities where drive times are noisy.
    catchment_mode: str = "drive_time"
    radius_km: float = 1.5
    # Targeted audience segment id (see scoring/segments.py), for reproducibility.
    segment: str | None = None
    # Business objective id (see scoring/objectives.py): what the user is using
    # the catchment for. Reweights the signals and frames the commentary.
    objective: str | None = None
    # Housebuilder journey the run was started from (find_site / appraise /
    # next_phase). Metadata only: restores the UI and labels the run in history.
    intent: str | None = None
    # Brand theme for themed exports, from a builder profile. Metadata only, not
    # used in scoring. brand_heading is the primary colour.
    brand_heading: str | None = None
    brand_secondary: str | None = None
    brand_accent: str | None = None
    brand_logo_path: str | None = None
    # Income an affordability multiple maps a price to. price / multiple.
    affordability_multiple: float = 4.5
    # Preferred tenure mix for the product's audiences, weights 0..1.
    tenure_preference: dict[str, float] = field(
        default_factory=lambda: {
            "owns_outright": 0.3,
            "owns_with_mortgage": 0.4,
            "social_rented": 0.0,
            "private_rented": 0.3,
        }
    )
    # Preferred age bands for the product, weights 0..1.
    age_preference: dict[str, float] = field(
        default_factory=lambda: {
            "age_0_15": 0.1,
            "age_16_34": 0.3,
            "age_35_54": 0.4,
            "age_55_74": 0.2,
            "age_75_plus": 0.0,
        }
    )
    # Population inside the catchment at which addressable scale saturates to ~0.63.
    scale_saturation: float = 50_000.0
    # A brand's best / target locations (postcodes), and the mean feature vector
    # of the areas they fall in. The lookalike signal scores each candidate area
    # by similarity to this reference, so scoring can favour areas resembling the
    # brand's known-good places. The reference is resolved at run time.
    lookalike_locations: list[str] = field(default_factory=list)
    lookalike_reference: dict[str, float] | None = None
