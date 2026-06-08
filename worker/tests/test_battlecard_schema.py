"""The Battlecard payload is schema-validated so all four surfaces can trust it.

The fixture uses the camelCase field names that match the TypeScript contract in
web/src/lib/types/battlecard.ts, proving the two stay interchangeable.
"""

from __future__ import annotations

from landlynk_worker.battlecard import BATTLECARD_SCHEMA_VERSION, Battlecard


def sample_payload() -> dict:
    dv = {"value": 1.0}
    return {
        "schemaVersion": BATTLECARD_SCHEMA_VERSION,
        "areaCode": "E02000001",
        "areaType": "MSOA",
        "proportionInside": 0.85,
        "rank": 1,
        "score": {
            "total": 0.72,
            "band": "high",
            "contributions": [
                {
                    "signal": "incomeFit",
                    "weight": 0.3,
                    "rawScore": 0.9,
                    "contribution": 0.27,
                    "rationale": "Median income aligns with the implied target",
                }
            ],
        },
        "visualSummary": {
            "header": {
                "developmentName": "Abbots Vale",
                "town": "Stowmarket",
                "postcode": "IP14 1AA",
                "strapline": "Room to grow",
                "lifestylePillars": ["Connected", "Green", "Family"],
            },
            "keyStatistics": {
                "bedRange": "2 to 5",
                "averageHouseholdIncome": {"value": 68000},
                "ownerOccupiedPercentage": {"value": 65.0},
                "priceFrom": {"value": 280000},
                "medianAge": {"value": 39},
                "populationCatchment": {"value": 120000},
            },
            "audienceMessaging": [
                {
                    "tier": "primary",
                    "audience": "Family second steppers",
                    "messageLines": ["Space to grow into"],
                    "channels": ["Meta", "Local press"],
                }
            ],
            "developmentFeatures": ["Open green space", "Primary school nearby"],
            "charts": {
                "ageDemographics": [
                    {"label": "0 to 15", "count": dv, "percentage": dv},
                ],
                "householdIncome": {
                    "mean": {"value": 68000},
                    "median": {"value": 60000},
                    "lowestLa": {"name": "Ipswich", "value": {"value": 52000}},
                    "highestLa": {"name": "Babergh", "value": {"value": 71000}},
                },
                "housingTenure": {
                    "ownsOutright": {"value": 25.0},
                    "ownsWithMortgage": {"value": 40.0},
                    "socialRented": {"value": 10.0},
                    "privateRented": {"value": 25.0},
                },
            },
        },
        "audienceAndDemographics": {
            "audienceTiers": [
                {
                    "tier": "primary",
                    "audience": "Family second steppers",
                    "body": "The catchment skews toward families progressing up the ladder",
                }
            ],
            "ageCohorts": [
                {"cohort": "35 to 54", "body": "A strong family-forming cohort"}
            ],
        },
        "incomeAndTenure": {
            "incomeCommentary": "A narrow income spread argues for mid-market positioning",
            "tenureCommentary": "A healthy private rented share signals a buyer pipeline",
        },
    }


def test_battlecard_validates_from_camelcase_payload():
    card = Battlecard.model_validate(sample_payload())
    assert card.area_code == "E02000001"
    assert card.score.band == "high"
    assert card.visual_summary.header.development_name == "Abbots Vale"


def test_suppressed_data_value_is_none_not_zero():
    payload = sample_payload()
    payload["visualSummary"]["keyStatistics"]["priceFrom"] = {
        "value": None,
        "suppressed": True,
    }
    card = Battlecard.model_validate(payload)
    assert card.visual_summary.key_statistics.price_from.value is None
    assert card.visual_summary.key_statistics.price_from.suppressed is True


def test_round_trip_to_camelcase_json():
    card = Battlecard.model_validate(sample_payload())
    dumped = card.model_dump(by_alias=True)
    assert "areaCode" in dumped
    assert "schemaVersion" in dumped
    # Re-validates cleanly, proving the surface contract is stable.
    Battlecard.model_validate(dumped)
