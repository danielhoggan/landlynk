"""Request and response models for the worker HTTP surface.

The mapping from the API request to the internal ScoringConfig and
DevelopmentInfo is pure and unit tested. The response serialisers shape stored
results into the contracts the web app expects (web/src/lib/types/catchment.ts
and the Battlecard payload).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .battlecard import DevelopmentInfo
from .scoring.profile import PriceBand, ScoringConfig


class PriceBandModel(BaseModel):
    frm: float = Field(alias="from")
    to: float

    model_config = {"populate_by_name": True}


class ScoringConfigModel(BaseModel):
    weights: dict[str, float] | None = None
    price_band: PriceBandModel | None = Field(default=None, alias="priceBand")
    bed_range: str | None = Field(default=None, alias="bedRange")
    overlap_threshold: float | None = Field(default=None, alias="overlapThreshold")
    drive_time_minutes: int | None = Field(default=None, alias="driveTimeMinutes")
    catchment_mode: str | None = Field(default=None, alias="catchmentMode")
    radius_km: float | None = Field(default=None, alias="radiusKm")
    segment: str | None = None
    brand_heading: str | None = Field(default=None, alias="brandHeading")
    brand_secondary: str | None = Field(default=None, alias="brandSecondary")
    brand_accent: str | None = Field(default=None, alias="brandAccent")
    brand_logo_path: str | None = Field(default=None, alias="brandLogoPath")
    affordability_multiple: float | None = Field(
        default=None, alias="affordabilityMultiple"
    )

    model_config = {"populate_by_name": True}


class CatchmentJobRequest(BaseModel):
    kind: str  # "postcode" or "gridref"
    value: str
    development_name: str = Field(alias="developmentName")
    town: str = ""
    strapline: str = ""
    lifestyle_pillars: list[str] = Field(default_factory=list, alias="lifestylePillars")
    development_features: list[str] = Field(
        default_factory=list, alias="developmentFeatures"
    )
    area_type: str = Field(default="MSOA", alias="areaType")
    config: ScoringConfigModel | None = None

    model_config = {"populate_by_name": True}


def to_scoring_config(req: CatchmentJobRequest) -> ScoringConfig:
    """Build a ScoringConfig, applying any overrides over the defaults."""
    base = ScoringConfig()
    cfg = req.config
    if cfg is None:
        return base
    price_band = (
        PriceBand(frm=cfg.price_band.frm, to=cfg.price_band.to)
        if cfg.price_band
        else base.price_band
    )
    config = ScoringConfig(
        weights=cfg.weights or base.weights,
        price_band=price_band,
        bed_range=cfg.bed_range or base.bed_range,
        overlap_threshold=(
            cfg.overlap_threshold
            if cfg.overlap_threshold is not None
            else base.overlap_threshold
        ),
        drive_time_minutes=(
            cfg.drive_time_minutes
            if cfg.drive_time_minutes is not None
            else base.drive_time_minutes
        ),
        catchment_mode=cfg.catchment_mode or base.catchment_mode,
        radius_km=(cfg.radius_km if cfg.radius_km is not None else base.radius_km),
        brand_heading=cfg.brand_heading or base.brand_heading,
        brand_secondary=cfg.brand_secondary or base.brand_secondary,
        brand_accent=cfg.brand_accent or base.brand_accent,
        brand_logo_path=cfg.brand_logo_path or base.brand_logo_path,
        affordability_multiple=(
            cfg.affordability_multiple
            if cfg.affordability_multiple is not None
            else base.affordability_multiple
        ),
    )
    # A chosen segment sets the age and tenure preference vectors, and the bed
    # range unless the caller gave an explicit one.
    if cfg.segment:
        from .scoring.segments import apply_segment

        config = apply_segment(
            config, cfg.segment, override_bed_range=cfg.bed_range is None
        )
    return config


def to_development_info(req: CatchmentJobRequest) -> DevelopmentInfo:
    return DevelopmentInfo(
        development_name=req.development_name,
        town=req.town,
        postcode=req.value if req.kind == "postcode" else None,
        strapline=req.strapline,
        lifestyle_pillars=req.lifestyle_pillars,
        development_features=req.development_features,
    )
