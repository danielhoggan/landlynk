"""Generate a Local Area Profile (description plus amenities) via an LLM.

One prompt, three provider transports (Anthropic, OpenAI, Google). The model is
chosen by the caller (the admin default or a per-request override). The HTTP call
is injectable so the parsing and dispatch are unit tested offline without a key.

This is qualitative enrichment, clearly labelled AI-generated for review. It does
not feed the quantitative scoring, which stays on open ONS data.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from ..config import settings
from .models import model_provider

AMENITY_CATEGORIES = (
    "Transport",
    "Retail",
    "Leisure",
    "Education",
    "Healthcare",
    "Other",
)

_PROMPT = (
    "You are a UK residential property and lifestyle analyst. I need a Local "
    "Area Profile for: {areas}. Write 4 to 5 flowing sentences about what it "
    "feels like to live there: character, connectivity, green space, dining, "
    "culture and any regeneration. Be specific with place names. Also list 8 to "
    "12 local amenities with categories. Respond ONLY with valid JSON: "
    '{{"description": "...", "amenities": [{{"name": "...", "category": '
    '"Transport"}}]}}. Valid categories: Transport, Retail, Leisure, Education, '
    "Healthcare, Other. Do not use em dashes or Oxford commas."
)

# A transport takes (model, prompt) and returns the model's raw text reply.
Transport = Callable[[str, str], str]


def _anthropic(model: str, prompt: str) -> str:
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    blocks = resp.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks)


def _openai(model: str, prompt: str) -> str:
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _google(model: str, prompt: str) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:"
        f"generateContent?key={settings.google_api_key}"
    )
    resp = httpx.post(
        url,
        headers={"content-type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60.0,
    )
    resp.raise_for_status()
    candidates = resp.json().get("candidates", [])
    parts = candidates[0]["content"]["parts"] if candidates else []
    return "".join(p.get("text", "") for p in parts)


_TRANSPORTS: dict[str, Transport] = {
    "anthropic": _anthropic,
    "openai": _openai,
    "google": _google,
}


def _parse(text: str) -> dict:
    clean = text.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean)
    amenities = []
    for a in parsed.get("amenities", []):
        category = a.get("category", "Other")
        if category not in AMENITY_CATEGORIES:
            category = "Other"
        amenities.append({"name": a.get("name", ""), "category": category})
    return {"description": parsed.get("description", ""), "amenities": amenities}


def generate_area_profile(
    area_names: list[str],
    model: str,
    transport: Transport | None = None,
) -> dict:
    """Generate {description, amenities} for the given areas with the model.

    Raises ValueError for an unknown model. The transport is injectable for tests.
    """
    provider = model_provider(model)
    if provider is None:
        raise ValueError(f"Unknown model: {model}")
    call = transport or _TRANSPORTS[provider]
    prompt = _PROMPT.format(areas=", ".join(area_names[:20]))
    return _parse(call(model, prompt))
