"""Place profile: Overpass parsing, the AI story and the Place setting pack."""

from __future__ import annotations

import pytest

from landlynk_worker.pipeline.places import (
    parse_cycle_relations,
    parse_place_nodes,
)


def _node(lat, lng, **tags):
    return {"type": "node", "lat": lat, "lng": None, "lon": lng, "tags": tags}


def test_parse_place_nodes_groups_and_sorts():
    # Around a pin at (55.0, -1.6): stops carry route refs, eateries sort by
    # distance, stations get walk and drive estimates, paired stops dedupe,
    # daily-life amenities (shops, schools, health, parks) group from nodes
    # and ways with centers.
    lat, lng = 55.0, -1.6
    elements = [
        _node(55.001, -1.6, highway="bus_stop", name="High St", route_ref="21;X9"),
        _node(55.0012, -1.6, highway="bus_stop", name="High St"),  # paired shelter
        _node(55.003, -1.6, highway="bus_stop", name="Market"),
        _node(55.0005, -1.6, amenity="restaurant", name="Luigi's", cuisine="italian"),
        _node(55.002, -1.6, amenity="pub", name="The Ship"),
        _node(55.004, -1.6, amenity="fast_food", name="Chippy"),
        _node(55.002, -1.6, amenity="cafe"),  # unnamed: dropped
        _node(55.03, -1.6, railway="station", name="Central"),
        # A closer Metro stop must not displace heavy rail as the lead station.
        _node(55.01, -1.6, railway="station", station="light_rail", name="Tram Stop"),
        _node(55.002, -1.6, shop="supermarket", name="Aldi"),
        _node(55.002, -1.6, amenity="pharmacy", name="Boots"),
        # A school mapped as a way, carrying a center instead of lat/lon.
        {
            "type": "way",
            "center": {"lat": 55.003, "lon": -1.6},
            "tags": {"amenity": "school", "name": "Brunton First School"},
        },
        {
            "type": "way",
            "center": {"lat": 55.004, "lon": -1.6},
            "tags": {"leisure": "park", "name": "Brunton Park"},
        },
    ]
    out = parse_place_nodes(elements, lat, lng)
    # The nearest station leads even when it is Metro; the nearest heavy-rail
    # station always appears in the follow-ups so neither reading is lost.
    assert out["station"]["name"] == "Tram Stop"
    assert out["station"]["metro"] is True
    assert [s["name"] for s in out["otherStations"]] == ["Central"]
    assert out["otherStations"][0]["metro"] is False
    assert out["station"]["walkMinutes"] > out["station"]["driveMinutes"]
    assert [s["name"] for s in out["busStops"]] == ["High St", "Market"]  # deduped
    assert out["busRoutes"] == ["21", "X9"]
    assert [r["name"] for r in out["restaurants"]] == [
        "Luigi's",
        "The Ship",
        "Chippy",
    ]
    assert out["restaurants"][0]["cuisine"] == "italian"
    assert [s["name"] for s in out["shops"]] == ["Aldi"]
    assert [s["name"] for s in out["schools"]] == ["Brunton First School"]
    assert [s["name"] for s in out["health"]] == ["Boots"]
    assert [s["name"] for s in out["parks"]] == ["Brunton Park"]


def test_parse_bus_relations_groups_directions():
    from landlynk_worker.pipeline.places import parse_bus_relations

    elements = [
        {"tags": {"route": "bus", "ref": "X21", "to": "Ashington"}},
        {"tags": {"route": "bus", "ref": "X21", "to": "Newcastle"}},
        {"tags": {"route": "bus", "ref": "21", "to": "City Centre"}},
        {"tags": {"route": "bus"}},  # no ref: dropped
        {"tags": {"route": "bicycle", "ref": "72"}},  # not a bus
    ]
    out = parse_bus_relations(elements)
    assert out == [
        {"ref": "21", "destinations": ["City Centre"]},
        {"ref": "X21", "destinations": ["Ashington", "Newcastle"]},
    ]


def test_parse_cycle_relations_dedupes_and_requires_identity():
    elements = [
        {"tags": {"route": "bicycle", "ref": "72", "name": "Hadrian's Cycleway"}},
        {"tags": {"route": "bicycle", "ref": "72", "name": "Hadrian's Cycleway"}},
        {"tags": {"route": "bicycle"}},  # no ref or name: dropped
        {"tags": {"route": "bus", "ref": "21"}},  # not a cycle route
    ]
    out = parse_cycle_relations(elements)
    assert out == [{"ref": "72", "name": "Hadrian's Cycleway"}]


def test_place_story_parses_and_grounds():
    from landlynk_worker.enrichment.place_story import generate_place_story

    seen = {}

    def fake(model, prompt):
        seen["prompt"] = prompt
        return (
            '{"events": [{"name": "Great North Run", "when": "September", '
            '"description": "Half marathon."}, "stray string"], '
            '"history": "A market town.", '
            '"politics": {"mp": "A Guess", '
            '"councilControl": "Labour", "commentary": "Broadly pro-housing."}}'
        ), {"input": 300, "output": 500}

    out = generate_place_story(
        "Oak Rise, NE1",
        "gpt-4o",
        transport=fake,
        grounding="Ward: Parklands; Council: Newcastle upon Tyne",
    )
    # The anchors land in the prompt so the model cannot drift to the wrong
    # suburb, and a model-guessed MP is discarded (official records supply it).
    assert "Ward: Parklands" in seen["prompt"]
    assert "never relocate" in seen["prompt"]
    assert out["events"] == [
        {
            "name": "Great North Run",
            "when": "September",
            "description": "Half marathon.",
        }
    ]
    assert out["history"] == "A market town."
    assert out["politics"]["mp"] == ""
    assert out["politics"]["councilControl"] == "Labour"
    assert out["usage"]["total"] == 800


def test_place_pack_renders_with_and_without_story():
    from landlynk_worker.battlecard.place_pptx import render_place_pptx

    record = {
        "station": {
            "name": "Central",
            "distanceKm": 1.2,
            "walkMinutes": 14,
            "driveMinutes": 4,
        },
        "otherStations": [],
        "busStops": [{"name": "High St", "distanceM": 120, "routes": ["21"]}],
        "busRoutes": ["21", "X9"],
        "restaurants": [
            {"name": "Luigi's", "type": "restaurant", "cuisine": "italian", "distanceM": 90}
        ],
        "cycleRoutes": [{"ref": "72", "name": "Hadrian's Cycleway"}],
    }
    bare = render_place_pptx(record, "Oak Rise · NE1")
    assert bare[:2] == b"PK"
    record["civic"] = {
        "constituency": "Newcastle upon Tyne North",
        "council": "Newcastle upon Tyne",
        "ward": "Parklands",
    }
    record["story"] = {
        "events": [{"name": "Fair", "when": "June", "description": "Annual fair."}],
        "history": "Built on coal and shipping.",
        "politics": {
            "mp": "A Person",
            "mpParty": "Labour",
            "councilControl": "Labour",
            "commentary": "Broadly pro-housing.",
        },
        "model": "gpt-4o",
    }
    with_story = render_place_pptx(record, "Oak Rise · NE1", map_image=None)
    assert with_story[:2] == b"PK" and len(with_story) > len(bare)
    # An empty record still renders the factual slides with explanations.
    assert render_place_pptx({}, "X")[:2] == b"PK"
