"""Battlecard PDF export produces a valid PDF from the payload."""

from __future__ import annotations

from landlynk_worker.battlecard import (
    DevelopmentInfo,
    IncomeContext,
    assemble_battlecard,
    render_battlecard_pdf,
    render_battlecard_pptx,
)
from landlynk_worker.scoring import (
    AgeProfile,
    AreaProfile,
    ScoringConfig,
    TenureMix,
    compute_score,
)


def _card():
    profile = AreaProfile(
        area_code="E02000001",
        area_type="MSOA",
        population=8000,
        households=3200,
        median_income=60000,
        mean_income=68000,
        median_age=39,
        tenure=TenureMix(0.25, 0.40, 0.10, 0.25),
        age=AgeProfile(0.18, 0.30, 0.28, 0.18, 0.06),
        family_household_share=0.55,
        proportion_inside=0.9,
    )
    config = ScoringConfig()
    score = compute_score(profile, config)
    return assemble_battlecard(
        profile,
        config,
        score,
        rank=1,
        development=DevelopmentInfo(
            "Abbots Vale", "Stowmarket", "IP14 1AA", "Room to grow", ["Green"], ["Park"]
        ),
        income_context=IncomeContext("Ipswich", 52000, "Babergh", 71000),
    )


def test_renders_a_pdf():
    pdf = render_battlecard_pdf(_card())
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000  # a real multi-page document, not an empty stub


def test_handles_suppressed_values():
    card = _card()
    card.visual_summary.key_statistics.average_household_income.value = None
    card.visual_summary.key_statistics.average_household_income.suppressed = True
    pdf = render_battlecard_pdf(card)
    assert pdf[:5] == b"%PDF-"


def test_theme_heading_colour_accepted():
    pdf = render_battlecard_pdf(_card(), heading_color="#0A1F44")
    assert pdf[:5] == b"%PDF-"


def test_renders_a_pptx():
    pptx = render_battlecard_pptx(_card())
    # PPTX is a zip (Office Open XML); zip files start with "PK".
    assert pptx[:2] == b"PK"
    assert len(pptx) > 1000


def test_pptx_handles_suppressed_and_theme():
    card = _card()
    card.visual_summary.key_statistics.median_age.value = None
    card.visual_summary.key_statistics.median_age.suppressed = True
    pptx = render_battlecard_pptx(card, heading_color="#0A1F44")
    assert pptx[:2] == b"PK"
