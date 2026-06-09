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


# Order is the preference order for the default when none is set.
MODELS: tuple[ModelInfo, ...] = (
    ModelInfo("claude-sonnet-4-5", "Claude Sonnet 4.5", "anthropic"),
    ModelInfo("claude-haiku-4-5", "Claude Haiku 4.5", "anthropic"),
    ModelInfo("gpt-4o", "GPT-4o", "openai"),
    ModelInfo("gpt-4o-mini", "GPT-4o mini", "openai"),
    ModelInfo("gemini-1.5-pro", "Gemini 1.5 Pro", "google"),
    ModelInfo("gemini-1.5-flash", "Gemini 1.5 Flash", "google"),
)

_BY_ID = {m.id: m for m in MODELS}


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
