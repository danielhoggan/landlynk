"""Census demographics and tenure transforms over NOMIS-style rows."""

from __future__ import annotations

from loaders.base import SourceSpec
from loaders.census import CensusDemographicsLoader, CensusTenureLoader

SPEC = SourceSpec("t", "ONS", "OGL", "2021", "url")


def test_demographics_transform_merges_age_and_households():
    age_rows = [
        {
            "geography code": "E02000001",
            "Aged 10 years": "100",
            "Aged 20 years": "200",
            "Aged 40 years": "150",
            "Aged 90 years and over": "50",
            "Total": "500",  # ignored, not a single age
        }
    ]
    household_rows = [
        {
            "geography code": "E02000001",
            "Total: All households": "200",
            "Single family household": "120",
            "One person household": "80",
        }
    ]
    loader = CensusDemographicsLoader(
        SPEC, "age.csv", households_source="hh.csv", area_type="MSOA"
    )
    rows = loader.transform(
        {
            "age": (age_rows, "geography code"),
            "households": (household_rows, "geography code"),
        }
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["area_code"] == "E02000001"
    assert row["population"] == 500  # 100 + 200 + 150 + 50
    assert row["age_0_15"] == 100
    assert row["age_16_34"] == 200
    assert row["age_35_54"] == 150
    assert row["age_75_plus"] == 50
    assert row["households"] == 200
    assert row["family_household_share"] == 120 / 200


def test_demographics_suppressed_age_is_not_zero():
    age_rows = [{"geography code": "E1", "Aged 20 years": ":"}]
    loader = CensusDemographicsLoader(SPEC, "a", households_source="h")
    rows = loader.transform(
        {"age": (age_rows, "geography code"), "households": ([], "geography code")}
    )
    assert rows[0]["age_16_34"] is None
    assert rows[0]["population"] is None


def test_tenure_transform_to_shares():
    rows = [
        {
            "geography code": "E02000001",
            "Total: All households": "1000",
            "Owned: Owns outright": "250",
            "Owned: Owns with a mortgage or loan": "400",
            "Social rented": "150",
            "Private rented": "200",
        }
    ]
    loader = CensusTenureLoader(SPEC, "tenure.csv")
    out = loader.transform((rows, "geography code"))[0]
    assert out["owns_outright"] == 0.25
    assert out["owns_with_mortgage"] == 0.40
    assert out["social_rented"] == 0.15
    assert out["private_rented"] == 0.20


def test_tenure_suppressed_total_yields_none_shares():
    rows = [
        {
            "geography code": "E1",
            "Total: All households": ":",
            "Owned: Owns outright": "100",
        }
    ]
    out = CensusTenureLoader(SPEC, "t").transform((rows, "geography code"))[0]
    assert out["owns_outright"] is None
