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
