"""Generate the qualitative half of a Place setting pack via an LLM.

Annual events and festivals near a location, and the place's history, have no
structured open dataset, so they are the one part of the pack that needs GenAI.
One prompt, the same three provider transports as the Local Area Profile, so it
meters and caches identically and is unit tested offline through an injectable
transport. Clearly labelled AI-generated for review; never feeds the scoring.
"""

from __future__ import annotations

from .area_profile import _TRANSPORTS, Transport, extract_json
from .models import model_provider

_PROMPT = (
    "You are a UK local culture and history researcher. The location is: "
    "{location}. Anchor everything on this exact place; if unsure of the town, "
    "use the postcode to place it correctly.\n\n"
    "1. List 4 to 8 real annual events or festivals held in or near this "
    "location (fairs, markets, music, sport, cultural festivals), each with "
    "roughly when in the year it happens and one sentence on what it is.\n"
    "2. Write 4 to 6 flowing sentences on the history of the place: origins, "
    "what shaped it (industry, trade, transport), and any notable heritage "
    "still visible today.\n\n"
    "Only include events you are confident are real and recurring. Respond "
    'ONLY with valid JSON: {{"events": [{{"name": "...", "when": "...", '
    '"description": "..."}}], "history": "..."}}. '
    "Do not use em dashes or Oxford commas."
)


def generate_place_story(
    location: str,
    model: str,
    transport: Transport | None = None,
) -> dict:
    """Generate {events, history} for a location with the chosen model.

    Raises ValueError for an unknown model. The transport is injectable so the
    parsing and dispatch are unit tested offline without a provider key.
    """
    provider = model_provider(model)
    if provider is None:
        raise ValueError(f"Unknown model: {model}")
    call = transport or _TRANSPORTS[provider]
    text, usage = call(model, _PROMPT.format(location=location))
    parsed = extract_json(text)
    events = [
        {
            "name": e.get("name", ""),
            "when": e.get("when", ""),
            "description": e.get("description", ""),
        }
        for e in (parsed.get("events") or [])
        if isinstance(e, dict) and e.get("name")
    ]
    total = (usage.get("input", 0) or 0) + (usage.get("output", 0) or 0)
    return {
        "events": events,
        "history": str(parsed.get("history") or ""),
        "usage": {**usage, "total": total},
    }
