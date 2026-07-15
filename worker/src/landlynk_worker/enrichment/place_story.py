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
    "You are a UK local culture, history and civic affairs researcher. The "
    "location is: {location}.\n"
    "{grounding}"
    "Anchor everything on this exact place. If anything you believe about the "
    "postcode conflicts with the anchors above, trust the anchors: describe "
    "the ward and suburb they name, and never relocate the place to a "
    "different suburb.\n\n"
    "1. List 4 to 8 real annual events or festivals held in or near this "
    "location (fairs, markets, music, sport, cultural festivals), each with "
    "roughly when in the year it happens and one sentence on what it is. "
    "Prefer events in or near the anchored ward and town.\n"
    "2. Write 4 to 6 flowing sentences on the history of this specific "
    "neighbourhood and its town: origins, what shaped it (industry, trade, "
    "transport), and any notable heritage still visible today.\n"
    "3. Give the political picture as of your knowledge: which party "
    "controls the local council, and 2 to 3 sentences on the area's general "
    "political character and what that has tended to mean for new housing "
    "development. Be neutral and factual; if control may have changed "
    "recently, say so. Do not name the MP; that is supplied separately from "
    "official records.\n\n"
    "Only include events you are confident are real and recurring. Respond "
    'ONLY with valid JSON: {{"events": [{{"name": "...", "when": "...", '
    '"description": "..."}}], "history": "...", "politics": '
    '{{"councilControl": "...", "commentary": "..."}}}}. '
    "Do not use em dashes or Oxford commas."
)


def generate_place_story(
    location: str,
    model: str,
    transport: Transport | None = None,
    grounding: str | None = None,
) -> dict:
    """Generate {events, history, politics} for a location with the model.

    grounding is an authoritative anchor block (ward, council, constituency
    and nearby landmark names from ONS and OpenStreetMap): a bare postcode
    lets a small model guess the wrong suburb, the anchors pin it down.
    Raises ValueError for an unknown model. The transport is injectable so the
    parsing and dispatch are unit tested offline without a provider key.
    """
    provider = model_provider(model)
    if provider is None:
        raise ValueError(f"Unknown model: {model}")
    call = transport or _TRANSPORTS[provider]
    grounding_block = (
        "Authoritative anchors for this location, from ONS and OpenStreetMap:\n"
        f"{grounding}\n"
        if grounding
        else ""
    )
    text, usage = call(
        model, _PROMPT.format(location=location, grounding=grounding_block)
    )
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
    politics_raw = parsed.get("politics")
    # The MP is never taken from the model (official records supply it); the
    # keys stay for older cached stories that carried them.
    politics = (
        {
            "mp": "",
            "mpParty": "",
            "councilControl": str(politics_raw.get("councilControl") or ""),
            "commentary": str(politics_raw.get("commentary") or ""),
        }
        if isinstance(politics_raw, dict)
        else None
    )
    total = (usage.get("input", 0) or 0) + (usage.get("output", 0) or 0)
    return {
        "events": events,
        "history": str(parsed.get("history") or ""),
        "politics": politics,
        "usage": {**usage, "total": total},
    }
