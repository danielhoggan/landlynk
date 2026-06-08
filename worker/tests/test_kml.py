"""KML export: catchment polygon plus foldered, colour-coded area pins."""

from __future__ import annotations

from xml.etree import ElementTree

from landlynk_worker.pipeline.outputs.kml import band_to_kml_color, render_catchment_kml

_KML_NS = "{http://www.opengis.net/kml/2.2}"


def _catchment() -> dict:
    return {
        "input": {"developmentName": "Abbots Vale"},
        "coordinate": {"lat": 52.0, "lng": 1.0},
        "isochrone": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0, 2], [2, 2], [2, 0], [0, 0]]],
        },
        "areas": [
            {
                "areaCode": "E02000001",
                "name": "Area A",
                "band": "high",
                "rank": 1,
                "score": 0.81,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
                },
            },
            {
                "areaCode": "E02000002",
                "name": "Area B",
                "band": "low",
                "rank": 2,
                "score": 0.20,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[1, 0], [1, 1], [2, 1], [2, 0], [1, 0]]],
                },
            },
        ],
    }


def _battlecards() -> dict:
    return {
        "E02000001": {
            "visualSummary": {
                "keyStatistics": {
                    "averageHouseholdIncome": {"value": 68000},
                    "ownerOccupiedPercentage": {"value": 65.0},
                    "medianAge": {"value": 39},
                    "populationCatchment": {"value": 8000},
                }
            },
            "pricingRationale": {"positioning": "Within local reach"},
        }
    }


def test_kml_is_well_formed_xml():
    kml = render_catchment_kml(_catchment(), _battlecards())
    root = ElementTree.fromstring(kml)  # raises if malformed
    assert root.tag == f"{_KML_NS}kml"


def test_kml_has_foldered_pins_and_balloon():
    kml = render_catchment_kml(_catchment(), _battlecards())
    root = ElementTree.fromstring(kml)
    folder_names = {f.findtext(f"{_KML_NS}name") for f in root.iter(f"{_KML_NS}Folder")}
    assert "Drive-time catchment" in folder_names
    assert "High priority" in folder_names
    assert "Low priority" in folder_names
    # The high-priority balloon carries the area's stats.
    assert "Average income" in kml
    assert "Within local reach" in kml


def test_band_colours_present():
    kml = render_catchment_kml(_catchment(), _battlecards())
    assert band_to_kml_color("high") in kml
    assert band_to_kml_color("low") in kml


def test_handles_missing_battlecard_and_geometry():
    catchment = _catchment()
    catchment["areas"][0]["geometry"] = None  # no geometry, no pin
    kml = render_catchment_kml(catchment, {})  # no battlecards at all
    ElementTree.fromstring(kml)  # still well formed
