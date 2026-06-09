"""The AI models offered for Local Area Profile enrichment.

Three providers are supported: Anthropic, OpenAI and Google. Which models are
actually offered depends on which provider keys are configured in the
environment, so the admin only ever picks from models that can run. Keeping the
registry here means adding a model is a one-line change.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import settings


@dataclass(frozen=True)
class ModelInfo:
    id: str
    label: str
    provider: str  # "anthropic" | "openai" | "google"
    # Indicative GBP cost for one generation, used for the pre-flight estimate
    # before real token counts are known.
    est_cost_gbp: float = 0.01
    # GBP per 1,000 tokens, input and output, from published pricing (approx).
    # Used to cost a generation precisely once the provider reports token usage.
    rate_in: float = 0.002
    rate_out: float = 0.008


# Order is the preference order for the default when none is set.
MODELS: tuple[ModelInfo, ...] = (
    ModelInfo(
        "claude-sonnet-4-5", "Claude Sonnet 4.5", "anthropic", 0.02, 0.0024, 0.012
    ),
    ModelInfo(
        "claude-haiku-4-5", "Claude Haiku 4.5", "anthropic", 0.005, 0.0006, 0.0032
    ),
    ModelInfo("gpt-4o", "GPT-4o", "openai", 0.02, 0.002, 0.008),
    ModelInfo("gpt-4o-mini", "GPT-4o mini", "openai", 0.002, 0.00012, 0.00048),
    ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", "google", 0.012, 0.001, 0.004),
    ModelInfo(
        "gemini-1.5-flash", "Gemini 1.5 Flash", "google", 0.001, 0.00006, 0.00024
    ),
)

_BY_ID = {m.id: m for m in MODELS}


def model_cost(model_id: str) -> float:
    """Indicative GBP cost for one generation (pre-flight, before real tokens)."""
    info = _BY_ID.get(model_id)
    return info.est_cost_gbp if info else 0.0


def token_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Precise GBP cost from real token counts, falling back to the estimate."""
    info = _BY_ID.get(model_id)
    if info is None:
        return 0.0
    if not input_tokens and not output_tokens:
        return info.est_cost_gbp
    return round(
        input_tokens / 1000 * info.rate_in + output_tokens / 1000 * info.rate_out, 5
    )


def _provider_keys() -> dict[str, bool]:
    return {
        "anthropic": bool(settings.anthropic_api_key),
        "openai": bool(settings.openai_api_key),
        "google": bool(settings.google_api_key),
    }


def model_provider(model_id: str) -> str | None:
    info = _BY_ID.get(model_id)
    return info.provider if info else None


def available_models() -> list[dict]:
    """Models whose provider key is configured, as plain dicts for the API."""
    keys = _provider_keys()
    return [
        {"id": m.id, "label": m.label, "provider": m.provider}
        for m in MODELS
        if keys.get(m.provider)
    ]


def default_available_model() -> str | None:
    """The first available model, used when an admin has not chosen one."""
    available = available_models()
    return available[0]["id"] if available else None
