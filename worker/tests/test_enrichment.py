"""AI Local Area Profile generation: parsing and provider dispatch (offline)."""

from __future__ import annotations

import pytest

from landlynk_worker.enrichment.area_profile import generate_area_profile
from landlynk_worker.enrichment.models import MODELS, model_provider


def test_model_provider_known_and_unknown():
    assert model_provider("gpt-4o") == "openai"
    assert model_provider("claude-sonnet-4-5") == "anthropic"
    assert model_provider("gemini-1.5-pro") == "google"
    assert model_provider("nope") is None


def test_generate_parses_json_and_filters_categories():
    captured = {}

    def fake(model: str, prompt: str):
        captured["model"] = model
        captured["prompt"] = prompt
        text = (
            '```json\n{"description": "A leafy commuter town.", '
            '"amenities": [{"name": "Station", "category": "Transport"}, '
            '{"name": "Odd", "category": "Bogus"}]}\n```'
        )
        return text, {"input": 400, "output": 600}

    out = generate_area_profile("Montgomery Place, TF9 3RP", "gpt-4o", transport=fake)
    assert out["description"].startswith("A leafy")
    assert out["amenities"][0] == {"name": "Station", "category": "Transport"}
    # Unknown categories collapse to Other.
    assert out["amenities"][1]["category"] == "Other"
    # The prompt is anchored on the development location, postcode included.
    assert "TF9 3RP" in captured["prompt"]
    assert captured["model"] == "gpt-4o"
    # Token usage is surfaced for costing.
    assert out["usage"] == {"input": 400, "output": 600, "total": 1000}


def test_token_cost_uses_real_tokens():
    from landlynk_worker.enrichment.models import model_cost, token_cost

    # 400 in + 600 out for gpt-4o (0.002 / 0.008 per 1k) = 0.0008 + 0.0048.
    assert token_cost("gpt-4o", 400, 600) == 0.0056
    # No tokens falls back to the flat per-generation estimate.
    assert token_cost("gpt-4o", 0, 0) == model_cost("gpt-4o")


def test_generate_rejects_unknown_model():
    with pytest.raises(ValueError):
        generate_area_profile(["X"], "no-such-model", transport=lambda m, p: ("{}", {}))


def test_models_registry_covers_three_providers():
    providers = {m.provider for m in MODELS}
    assert providers == {"anthropic", "openai", "google"}


def test_marketing_parses_playbook_structure():
    from landlynk_worker.enrichment.marketing import generate_marketing_activation

    captured = {}

    def fake(model: str, prompt: str):
        captured["prompt"] = prompt
        text = (
            '{"summary": "Lead with first-time buyers.", '
            '"budgetTiers": [{"tier": "Core", "audience": "FTB", '
            '"sharePct": "60", "rationale": "deepest pool"}], '
            '"channelMix": [{"tier": "Core", "channels": '
            '[{"channel": "Google Search", "sharePct": 40, "role": "capture"}]}], '
            '"searchThemes": [{"theme": "New homes", '
            '"exampleKeywords": ["new homes near me"], "intent": "ready to buy"}], '
            '"metaAudiences": [{"name": "Renters", "definition": "25-34 renters", '
            '"creativeAngle": "own for less than rent"}], '
            '"watchOuts": ["affordability is tight"], '
            '"kpis": [{"metric": "CPL", "target": "under 40", "why": "efficiency"}]}'
        )
        return text, {"input": 500, "output": 800}

    out = generate_marketing_activation("Facts here", "gpt-4o", transport=fake)
    # sharePct is coerced to an int even when the model returns a string.
    assert out["budgetTiers"][0]["sharePct"] == 60
    assert out["channelMix"][0]["channels"][0]["channel"] == "Google Search"
    assert out["searchThemes"][0]["exampleKeywords"] == ["new homes near me"]
    assert out["metaAudiences"][0]["name"] == "Renters"
    assert out["watchOuts"] == ["affordability is tight"]
    assert out["kpis"][0]["metric"] == "CPL"
    assert "Facts here" in captured["prompt"]
    assert out["usage"] == {"input": 500, "output": 800, "total": 1300}


def test_marketing_rejects_unknown_model():
    from landlynk_worker.enrichment.marketing import generate_marketing_activation

    with pytest.raises(ValueError):
        generate_marketing_activation("facts", "no-such", transport=lambda m, p: ("{}", {}))


def test_build_facts_flattens_known_fields():
    from types import SimpleNamespace

    from landlynk_worker.enrichment.marketing import build_facts

    def cell(v):
        return SimpleNamespace(value=v)

    card = SimpleNamespace(
        visual_summary=SimpleNamespace(
            key_statistics=SimpleNamespace(
                population_catchment=cell(120000),
                households_catchment=cell(48000),
                average_household_income=cell(36000),
                median_house_price=cell(285000),
                owner_occupied_percentage=cell(64.2),
                median_age=cell(41),
            )
        ),
        addressable_segments=SimpleNamespace(
            first_time_buyer_pipeline=cell(9000),
            downsizer_pool=cell(7000),
            family_households=cell(20000),
        ),
        pricing_rationale=SimpleNamespace(
            implied_affordable_price=cell(310000),
            price_from=cell(295000),
            positioning="Priced within local affordability.",
        ),
        data_confidence=SimpleNamespace(level="high"),
    )
    facts = build_facts(
        card, development="Oak Rise", location="Oak Rise, NN15 7FJ", intent="find_site"
    )
    assert "Oak Rise, NN15 7FJ" in facts
    assert "find_site" in facts
    assert "48000" in facts
    assert "Priced within local affordability." in facts
