"""Generate a Marketing Activation playbook for a catchment via an LLM.

This is the marketing-activation pipeline, kept deliberately separate from the
quantitative Battlecard engine and from the qualitative Local Area Profile. It
takes the reproducible catchment facts (audience pools, income, pricing read,
top areas) and asks a model to turn them into a media plan: a budget split by
audience tier, a channel mix per tier, Google Search themes, Meta audiences,
watch-outs and KPIs. It mirrors the area-profile pattern (one prompt, the same
three provider transports, injectable for offline tests) so it meters and caches
the same way.

It is internal-only and optional to run: it costs an LLM call, so the caller
flags the cost and the user opts in. Like the area profile, the output is
clearly AI-generated for review and never feeds the scoring.
"""

from __future__ import annotations

import json

from .area_profile import _TRANSPORTS, Transport
from .models import model_provider

# The structured shape we ask the model for. Keeping the keys explicit in the
# prompt means the panel can render predictable sections rather than free prose.
_PROMPT = (
    "You are a UK residential property performance-marketing strategist planning "
    "the launch media for a new housing development. Use ONLY the catchment facts "
    "below to shape the plan. Be concrete and numerate. Do not invent local place "
    "names that are not in the facts.\n\n"
    "DEVELOPMENT AND CATCHMENT FACTS:\n{facts}\n\n"
    "Produce a marketing activation playbook. Split a launch budget across the "
    "audience tiers that the facts support (the largest addressable pools and the "
    "segments that fit the price). For each tier give a channel mix that sums to "
    "100 percent. Suggest Google Search themes with example keyword groups, Meta "
    "(Facebook and Instagram) audience definitions with a creative angle, the "
    "watch-outs given this catchment (affordability, competition, demand depth) "
    "and the KPIs to hold the plan to.\n\n"
    "Respond ONLY with valid JSON in exactly this shape: "
    '{{"summary": "2 to 3 sentence plan overview", '
    '"budgetTiers": [{{"tier": "name", "audience": "who", "sharePct": 40, '
    '"rationale": "why this share"}}], '
    '"channelMix": [{{"tier": "name", "channels": [{{"channel": "Google Search", '
    '"sharePct": 30, "role": "what it does"}}]}}], '
    '"searchThemes": [{{"theme": "name", "exampleKeywords": ["kw1", "kw2"], '
    '"intent": "what the searcher wants"}}], '
    '"metaAudiences": [{{"name": "name", "definition": "targeting", '
    '"creativeAngle": "the message"}}], '
    '"watchOuts": ["risk 1", "risk 2"], '
    '"kpis": [{{"metric": "name", "target": "value", "why": "reason"}}]}}. '
    "Do not use em dashes or Oxford commas."
)


def build_facts(card: object, *, development: str, location: str, intent: str | None) -> str:
    """Flatten the combined Battlecard into the plain-text facts the prompt needs.

    Pulls only the reproducible numbers (audience pools, income, pricing read,
    confidence) so the media plan is anchored on the engine, not the model's
    guesswork. Accepts the pydantic Battlecard; reads defensively so a partial
    card still produces usable facts.
    """
    ks = getattr(getattr(card, "visual_summary", None), "key_statistics", None)
    seg = getattr(card, "addressable_segments", None)
    pr = getattr(card, "pricing_rationale", None)
    conf = getattr(card, "data_confidence", None)

    def val(obj: object, attr: str) -> object:
        node = getattr(obj, attr, None)
        return getattr(node, "value", None) if node is not None else None

    lines = [
        f"Development: {development}",
        f"Location: {location}",
    ]
    if intent:
        lines.append(f"Housebuilder intent: {intent}")
    if ks is not None:
        lines += [
            f"Addressable population: {val(ks, 'population_catchment')}",
            f"Households: {val(ks, 'households_catchment')}",
            f"Average household income: {val(ks, 'average_household_income')}",
            f"Median local house price: {val(ks, 'median_house_price')}",
            f"Owner-occupied share (%): {val(ks, 'owner_occupied_percentage')}",
            f"Median age: {val(ks, 'median_age')}",
        ]
    if seg is not None:
        lines += [
            f"First-time-buyer pipeline: {val(seg, 'first_time_buyer_pipeline')}",
            f"Downsizer pool: {val(seg, 'downsizer_pool')}",
            f"Family households: {val(seg, 'family_households')}",
        ]
    if pr is not None:
        positioning = getattr(pr, "positioning", None)
        lines += [
            f"Implied affordable price: {val(pr, 'implied_affordable_price')}",
            f"Indicative price from: {val(pr, 'price_from')}",
        ]
        if positioning:
            lines.append(f"Pricing positioning: {positioning}")
    if conf is not None:
        lines.append(f"Data confidence: {getattr(conf, 'level', None)}")
    return "\n".join(str(line) for line in lines)


def _coerce_share(value: object) -> int | None:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _parse(text: str) -> dict:
    clean = text.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean)
    budget_tiers = []
    for t in parsed.get("budgetTiers", []) or []:
        budget_tiers.append(
            {
                "tier": t.get("tier", ""),
                "audience": t.get("audience", ""),
                "sharePct": _coerce_share(t.get("sharePct")),
                "rationale": t.get("rationale", ""),
            }
        )
    channel_mix = []
    for m in parsed.get("channelMix", []) or []:
        channels = [
            {
                "channel": c.get("channel", ""),
                "sharePct": _coerce_share(c.get("sharePct")),
                "role": c.get("role", ""),
            }
            for c in (m.get("channels", []) or [])
        ]
        channel_mix.append({"tier": m.get("tier", ""), "channels": channels})
    search_themes = [
        {
            "theme": s.get("theme", ""),
            "exampleKeywords": [str(k) for k in (s.get("exampleKeywords", []) or [])],
            "intent": s.get("intent", ""),
        }
        for s in (parsed.get("searchThemes", []) or [])
    ]
    meta_audiences = [
        {
            "name": a.get("name", ""),
            "definition": a.get("definition", ""),
            "creativeAngle": a.get("creativeAngle", ""),
        }
        for a in (parsed.get("metaAudiences", []) or [])
    ]
    return {
        "summary": parsed.get("summary", ""),
        "budgetTiers": budget_tiers,
        "channelMix": channel_mix,
        "searchThemes": search_themes,
        "metaAudiences": meta_audiences,
        "watchOuts": [str(w) for w in (parsed.get("watchOuts", []) or [])],
        "kpis": [
            {
                "metric": k.get("metric", ""),
                "target": k.get("target", ""),
                "why": k.get("why", ""),
            }
            for k in (parsed.get("kpis", []) or [])
        ],
    }


def generate_marketing_activation(
    facts: str,
    model: str,
    transport: Transport | None = None,
) -> dict:
    """Generate a structured marketing-activation playbook for a catchment.

    facts is the flattened catchment text from build_facts; model is the chosen
    LLM. Raises ValueError for an unknown model. The transport is injectable so
    the parsing and dispatch are unit tested offline without a provider key.
    """
    provider = model_provider(model)
    if provider is None:
        raise ValueError(f"Unknown model: {model}")
    call = transport or _TRANSPORTS[provider]
    prompt = _PROMPT.format(facts=facts)
    text, usage = call(model, prompt)
    total = (usage.get("input", 0) or 0) + (usage.get("output", 0) or 0)
    return {**_parse(text), "usage": {**usage, "total": total}}
