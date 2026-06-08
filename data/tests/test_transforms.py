"""Shared transform helpers: suppression, age bands and median age."""

from __future__ import annotations

from loaders.transforms import (
    age_from_label,
    aggregate_age_bands,
    median_age,
    parse_count,
    parse_number,
    share,
)


def test_parse_number_handles_suppression_markers():
    for marker in ["", ":", "-", "c", "*", "n/a", "x"]:
        assert parse_number(marker) is None


def test_parse_number_keeps_genuine_zero():
    assert parse_number("0") == 0.0
    assert parse_number(0) == 0.0


def test_parse_number_strips_separators():
    assert parse_number("1,234") == 1234.0
    assert parse_number("£52,000") == 52000.0


def test_parse_count_rounds_and_preserves_none():
    assert parse_count("12") == 12
    assert parse_count(":") is None


def test_share_guards_zero_and_none():
    assert share(50, 200) == 0.25
    assert share(None, 200) is None
    assert share(50, 0) is None


def test_age_from_label_variants():
    assert age_from_label("Aged 16 years") == 16
    assert age_from_label("Age: 16") == 16
    assert age_from_label("Aged 90 years and over") == 90
    assert age_from_label("Aged 16 to 19 years") is None  # a range, not a single age
    assert age_from_label("Total: All usual residents") is None


def test_aggregate_age_bands_sums_into_product_bands():
    counts = {age: 10 for age in range(0, 91)}
    bands = aggregate_age_bands(counts)
    assert bands["age_0_15"] == 160  # ages 0..15 inclusive
    assert bands["age_16_34"] == 190  # ages 16..34
    assert bands["age_75_plus"] == 160  # ages 75..90


def test_aggregate_age_bands_suppression_versus_absence():
    # A band with a suppressed contributor and nothing usable is None.
    counts = {16: None, 17: None}
    bands = aggregate_age_bands(counts)
    assert bands["age_16_34"] is None
    # A band with no ages in range at all is a true zero.
    assert bands["age_75_plus"] == 0


def test_median_age_from_distribution():
    # Lower-median convention: the age at which the cumulative count reaches half.
    assert median_age({30: 10, 40: 10}) == 30.0
    # Single dominant age.
    assert median_age({25: 100, 80: 1}) == 25.0


def test_median_age_empty_is_none():
    assert median_age({}) is None
    assert median_age({30: None}) is None
