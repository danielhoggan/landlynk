"""Request mapping to ScoringConfig and DevelopmentInfo."""

from __future__ import annotations

from landlynk_worker.api_models import (
    CatchmentJobRequest,
    to_development_info,
    to_scoring_config,
)


def test_defaults_when_no_config_given():
    req = CatchmentJobRequest.model_validate(
        {"kind": "postcode", "value": "IP14 1AA", "developmentName": "Abbots Vale"}
    )
    config = to_scoring_config(req)
    assert config.drive_time_minutes == 30
    assert config.bed_range == "2 to 5"
    assert config.affordability_multiple == 4.5


def test_affordability_multiple_override_applied():
    req = CatchmentJobRequest.model_validate(
        {
            "kind": "postcode",
            "value": "IP14 1AA",
            "developmentName": "X",
            "config": {"affordabilityMultiple": 5.0},
        }
    )
    assert to_scoring_config(req).affordability_multiple == 5.0


def test_config_overrides_applied():
    req = CatchmentJobRequest.model_validate(
        {
            "kind": "postcode",
            "value": "IP14 1AA",
            "developmentName": "Abbots Vale",
            "config": {
                "priceBand": {"from": 300000, "to": 500000},
                "bedRange": "3 to 5",
                "driveTimeMinutes": 45,
                "overlapThreshold": 0.2,
            },
        }
    )
    config = to_scoring_config(req)
    assert config.price_band.frm == 300000
    assert config.price_band.to == 500000
    assert config.bed_range == "3 to 5"
    assert config.drive_time_minutes == 45
    assert config.overlap_threshold == 0.2


def test_postcode_input_sets_header_postcode():
    req = CatchmentJobRequest.model_validate(
        {"kind": "postcode", "value": "IP14 1AA", "developmentName": "X"}
    )
    assert to_development_info(req).postcode == "IP14 1AA"


def test_gridref_input_has_no_postcode():
    req = CatchmentJobRequest.model_validate(
        {"kind": "gridref", "value": "TM 06457 58755", "developmentName": "X"}
    )
    assert to_development_info(req).postcode is None
