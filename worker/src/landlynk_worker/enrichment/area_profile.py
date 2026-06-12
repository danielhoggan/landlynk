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
    "You are a UK residential property and lifestyle analyst. Profile the area "
    "of a new residential development located at: {location}. Anchor everything "
    "on this exact location. Write 4 to 5 flowing sentences about what it feels "
    "like to live there: character, connectivity, green space, dining, culture "
    "and any regeneration. Be specific with real place names in and immediately "
    "around {location}. Also list 8 to 12 real local amenities near {location} "
    "with categories. If unsure of the town, use the postcode to place it "
    "correctly. Respond ONLY with valid JSON: "
    '{{"description": "...", "amenities": [{{"name": "...", "category": '
    '"Transport"}}]}}. Valid categories: Transport, Retail, Leisure, Education, '
    "Healthcare, Other. Do not use em dashes or Oxford commas."
)

# A transport takes (model, prompt) and returns (raw text reply, token usage).
# usage is {"input": int, "output": int}; zeros when the provider omits it.
Transport = Callable[[str, str], tuple[str, dict]]


def _anthropic(model: str, prompt: str) -> tuple[str, dict]:
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
    data = resp.json()
    text = "".join(b.get("text", "") for b in data.get("content", []))
    u = data.get("usage", {})
    return text, {
        "input": u.get("input_tokens", 0),
        "output": u.get("output_tokens", 0),
    }


def _openai(model: str, prompt: str) -> tuple[str, dict]:
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
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    u = data.get("usage", {})
    return text, {
        "input": u.get("prompt_tokens", 0),
        "output": u.get("completion_tokens", 0),
    }


def _google(model: str, prompt: str) -> tuple[str, dict]:
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
    data = resp.json()
    candidates = data.get("candidates", [])
    parts = candidates[0]["content"]["parts"] if candidates else []
    text = "".join(p.get("text", "") for p in parts)
    u = data.get("usageMetadata", {})
    return text, {
        "input": u.get("promptTokenCount", 0),
        "output": u.get("candidatesTokenCount", 0),
    }


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
    location: str,
    model: str,
    transport: Transport | None = None,
) -> dict:
    """Generate {description, amenities} for a development location with the model.

    location anchors the profile (e.g. "Montgomery Place, TF9 3RP"); the postcode
    keeps the model on the right town. Raises ValueError for an unknown model.
    The transport is injectable for tests.
    """
    provider = model_provider(model)
    if provider is None:
        raise ValueError(f"Unknown model: {model}")
    call = transport or _TRANSPORTS[provider]
    prompt = _PROMPT.format(location=location)
    text, usage = call(model, prompt)
    total = (usage.get("input", 0) or 0) + (usage.get("output", 0) or 0)
    return {**_parse(text), "usage": {**usage, "total": total}}
