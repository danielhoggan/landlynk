"""PPTX export of a Battlecard.

The fourth render surface for the single Battlecard payload, for sales-enablement
decks. Brand theming is per client and passed in, never hard-coded
(design-framework.md): the heading colour defaults to Royal Blue and the client
primary overrides it. Generated prose already follows the house conventions.
"""

from __future__ import annotations

import io

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.slide import Slide
from pptx.util import Inches, Pt

from .schema import Battlecard, DataValue

_DEFAULT_HEADING = "4169E1"  # Royal Blue, no leading hash for python-pptx


def _hex(color: str | None) -> RGBColor:
    value = (color or _DEFAULT_HEADING).lstrip("#")
    return RGBColor.from_string(value)


def _fmt(dv: DataValue, *, money: bool = False, pct: bool = False) -> str:
    if dv.value is None:
        return "Suppressed" if dv.suppressed else "Not available"
    if money:
        return f"£{dv.value:,.0f}"
    if pct:
        return f"{dv.value:.1f}%"
    return f"{dv.value:,.0f}"


def render_battlecard_pptx(card: Battlecard, heading_color: str | None = None) -> bytes:
    """Render a Battlecard payload to PPTX bytes."""
    heading = _hex(heading_color)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    vs = card.visual_summary

    def add_title(slide: Slide, text: str) -> None:
        box = slide.shapes.add_textbox(
            Inches(0.6), Inches(0.4), Inches(12), Inches(0.9)
        )
        p = box.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = text
        run.font.size = Pt(30)
        run.font.bold = True
        run.font.color.rgb = heading

    def add_body(
        slide: Slide, lines: list[str], top: float = 1.5, size: int = 16
    ) -> None:
        box = slide.shapes.add_textbox(
            Inches(0.6), Inches(top), Inches(12), Inches(5.4)
        )
        tf = box.text_frame
        tf.word_wrap = True
        for i, line in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line
            p.font.size = Pt(size)

    # Slide 1: visual summary
    s1 = prs.slides.add_slide(blank)
    add_title(s1, vs.header.development_name)
    stats = vs.key_statistics
    add_body(
        s1,
        [
            ", ".join(p for p in [vs.header.town, vs.header.postcode] if p),
            vs.header.strapline,
            "",
            f"Rank {card.rank}  |  score {card.score.total:.2f} ({card.score.band})",
            f"Bed range: {stats.bed_range}",
            f"Average household income: {_fmt(stats.average_household_income, money=True)}",
            f"Owner occupied: {_fmt(stats.owner_occupied_percentage, pct=True)}",
            f"Price from: {_fmt(stats.price_from, money=True)}",
            f"Median age: {_fmt(stats.median_age)}",
            f"Population in catchment: {_fmt(stats.population_catchment)}",
            f"Households in catchment: {_fmt(stats.households_catchment)}",
        ],
    )

    # Slide 2: audience and pricing
    s2 = prs.slides.add_slide(blank)
    add_title(s2, "Audience and positioning")
    audience_lines: list[str] = []
    for m in vs.audience_messaging:
        audience_lines.append(f"{m.tier.title()}: {m.audience}")
        audience_lines.extend(f"  - {line}" for line in m.message_lines)
    audience_lines.append("")
    audience_lines.append("Pricing rationale")
    audience_lines.append(card.pricing_rationale.positioning)
    add_body(s2, audience_lines)

    # Slide 3: demographics and tenure
    s3 = prs.slides.add_slide(blank)
    add_title(s3, "Demographics and tenure")
    tenure = vs.charts.housing_tenure
    add_body(
        s3,
        [
            "Age demographics",
            *[
                f"  {b.label}: {_fmt(b.percentage, pct=True)}"
                for b in vs.charts.age_demographics
            ],
            "",
            "Housing tenure",
            f"  Owns outright: {_fmt(tenure.owns_outright, pct=True)}",
            f"  Owns with mortgage: {_fmt(tenure.owns_with_mortgage, pct=True)}",
            f"  Social rented: {_fmt(tenure.social_rented, pct=True)}",
            f"  Private rented: {_fmt(tenure.private_rented, pct=True)}",
        ],
    )

    # Slide 4: commentary
    s4 = prs.slides.add_slide(blank)
    add_title(s4, "Income and tenure commentary")
    add_body(
        s4,
        [
            card.income_and_tenure.income_commentary,
            "",
            card.income_and_tenure.tenure_commentary,
            "",
            f"Data confidence: {card.data_confidence.level}. {card.data_confidence.note}",
        ],
    )

    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()
