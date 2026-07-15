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
    # distance, stations get walk and drive estimates, paired stops dedupe.
    lat, lng = 55.0, -1.6
    elements = [
        _node(55.001, -1.6, highway="bus_stop", name="High St", route_ref="21;X9"),
        _node(55.0012, -1.6, highway="bus_stop", name="High St"),  # paired shelter
        _node(55.003, -1.6, highway="bus_stop", name="Market"),
        _node(55.0005, -1.6, amenity="restaurant", name="Luigi's", cuisine="italian"),
        _node(55.002, -1.6, amenity="pub", name="The Ship"),
        _node(55.002, -1.6, amenity="cafe"),  # unnamed: dropped
        _node(55.03, -1.6, railway="station", name="Central"),
        _node(55.06, -1.6, railway="station", name="Further"),
    ]
    out = parse_place_nodes(elements, lat, lng)
    assert out["station"]["name"] == "Central"
    assert out["station"]["distanceKm"] == pytest.approx(3.3, abs=0.2)
    assert out["station"]["walkMinutes"] > out["station"]["driveMinutes"]
    assert [s["name"] for s in out["otherStations"]] == ["Further"]
    assert [s["name"] for s in out["busStops"]] == ["High St", "Market"]  # deduped
    assert out["busRoutes"] == ["21", "X9"]
    assert [r["name"] for r in out["restaurants"]] == ["Luigi's", "The Ship"]
    assert out["restaurants"][0]["cuisine"] == "italian"


def test_parse_cycle_relations_dedupes_and_requires_identity():
    elements = [
        {"tags": {"route": "bicycle", "ref": "72", "name": "Hadrian's Cycleway"}},
        {"tags": {"route": "bicycle", "ref": "72", "name": "Hadrian's Cycleway"}},
        {"tags": {"route": "bicycle"}},  # no ref or name: dropped
        {"tags": {"route": "bus", "ref": "21"}},  # not a cycle route
    ]
    out = parse_cycle_relations(elements)
    assert out == [{"ref": "72", "name": "Hadrian's Cycleway"}]


def test_place_story_parses_events_and_history():
    from landlynk_worker.enrichment.place_story import generate_place_story

    def fake(model, prompt):
        assert "NE1" in prompt
        return (
            '{"events": [{"name": "Great North Run", "when": "September", '
            '"description": "Half marathon."}, "stray string"], '
            '"history": "A market town."}'
        ), {"input": 300, "output": 500}

    out = generate_place_story("Oak Rise, NE1", "gpt-4o", transport=fake)
    assert out["events"] == [
        {
            "name": "Great North Run",
            "when": "September",
            "description": "Half marathon.",
        }
    ]
    assert out["history"] == "A market town."
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
    record["story"] = {
        "events": [{"name": "Fair", "when": "June", "description": "Annual fair."}],
        "history": "Built on coal and shipping.",
        "model": "gpt-4o",
    }
    with_story = render_place_pptx(record, "Oak Rise · NE1")
    assert with_story[:2] == b"PK" and len(with_story) > len(bare)
    # An empty record still renders the factual slides with explanations.
    assert render_place_pptx({}, "X")[:2] == b"PK"
