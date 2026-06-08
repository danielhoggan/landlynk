"""PDF export of a Battlecard.

Renders the single Battlecard payload to a PDF, the third of the four surfaces.
Layout follows the Abbots Vale reference: a visual summary then audience and
demographic commentary then income and tenure commentary (SCOPING.md Section 9).

Brand theming is per client and passed in, never hard-coded (design-framework.md).
Headings use the theme primary colour, defaulting to Royal Blue. Document font
is Tenorite per the house conventions; the proprietary font file is registered
at startup when available and falls back to a standard face otherwise. Generated
prose already follows the house conventions (no em dashes, no Oxford commas, no
markdown headers).
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .schema import Battlecard, DataValue

# Default document heading colour where a client brand does not override.
_DEFAULT_HEADING = "#4169E1"  # Royal Blue
_BODY_FONT = "Helvetica"  # Tenorite fallback until the licensed font is registered


def _fmt(dv: DataValue, *, money: bool = False, pct: bool = False) -> str:
    """Format a DataValue, honouring suppression (null, never zero)."""
    if dv.value is None:
        return "Suppressed" if dv.suppressed else "Not available"
    if money:
        return f"£{dv.value:,.0f}"
    if pct:
        return f"{dv.value:.1f}%"
    return f"{dv.value:,.0f}"


def render_battlecard_pdf(card: Battlecard, heading_color: str | None = None) -> bytes:
    """Render a Battlecard payload to PDF bytes."""
    heading_hex = heading_color or _DEFAULT_HEADING
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Battlecard {card.area_code}",
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        textColor=colors.HexColor(heading_hex),
        fontName="Helvetica-Bold",
    )
    h2 = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        textColor=colors.HexColor(heading_hex),
        fontName="Helvetica-Bold",
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName=_BODY_FONT, leading=14
    )

    vs = card.visual_summary
    story: list = []

    # --- Page 1: visual summary ---
    story.append(Paragraph(vs.header.development_name, h1))
    location = ", ".join(p for p in [vs.header.town, vs.header.postcode] if p)
    story.append(Paragraph(location, body))
    story.append(Paragraph(vs.header.strapline, body))
    if vs.header.lifestyle_pillars:
        story.append(Paragraph(" | ".join(vs.header.lifestyle_pillars), body))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("Key statistics", h2))
    stats = vs.key_statistics
    story.append(
        _two_col_table(
            [
                ("Bed range", stats.bed_range),
                (
                    "Average household income",
                    _fmt(stats.average_household_income, money=True),
                ),
                ("Owner occupied", _fmt(stats.owner_occupied_percentage, pct=True)),
                ("Price from", _fmt(stats.price_from, money=True)),
                ("Median age", _fmt(stats.median_age)),
                ("Population catchment", _fmt(stats.population_catchment)),
                ("Households catchment", _fmt(stats.households_catchment)),
                ("Family households", _fmt(stats.family_household_share, pct=True)),
            ]
        )
    )
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Priority", h2))
    story.append(
        Paragraph(
            f"Rank {card.rank}. Score {card.score.total:.2f} ({card.score.band} priority).",
            body,
        )
    )
    ctx = card.catchment_context
    if ctx.income_index.value is not None:
        story.append(
            Paragraph(
                f"Income index {ctx.income_index.value:.0f} versus the catchment "
                f"average of 100. {_fmt(ctx.share_of_catchment_population, pct=True)} "
                "of the catchment population.",
                body,
            )
        )
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Pricing rationale", h2))
    story.append(Paragraph(card.pricing_rationale.positioning, body))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Addressable segments inside the catchment", h2))
    seg = card.addressable_segments
    story.append(
        _two_col_table(
            [
                ("First-time buyer pipeline", _fmt(seg.first_time_buyer_pipeline)),
                ("Downsizer pool", _fmt(seg.downsizer_pool)),
                ("Family households", _fmt(seg.family_households)),
            ]
        )
    )
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Target audience and messaging", h2))
    for msg in vs.audience_messaging:
        story.append(Paragraph(f"<b>{msg.tier.title()}: {msg.audience}</b>", body))
        for line in msg.message_lines:
            story.append(Paragraph(line, body))
    story.append(Spacer(1, 5 * mm))

    if vs.development_features:
        story.append(Paragraph("The development and location", h2))
        for feature in vs.development_features:
            story.append(Paragraph(f"- {feature}", body))
        story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Age demographics", h2))
    story.append(
        _two_col_table(
            [
                (b.label, _fmt(b.percentage, pct=True))
                for b in vs.charts.age_demographics
            ]
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Housing tenure", h2))
    tenure = vs.charts.housing_tenure
    story.append(
        _two_col_table(
            [
                ("Owns outright", _fmt(tenure.owns_outright, pct=True)),
                ("Owns with mortgage", _fmt(tenure.owns_with_mortgage, pct=True)),
                ("Social rented", _fmt(tenure.social_rented, pct=True)),
                ("Private rented", _fmt(tenure.private_rented, pct=True)),
            ]
        )
    )

    # --- Page 2: audience and demographic commentary ---
    ad = card.audience_and_demographics
    story.append(Paragraph("Audience messaging overview", h1))
    for tier in ad.audience_tiers:
        story.append(Paragraph(f"{tier.tier.title()}: {tier.audience}", h2))
        story.append(Paragraph(tier.body, body))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Demographic commentary", h2))
    for cohort in ad.age_cohorts:
        story.append(Paragraph(f"<b>{cohort.cohort}</b>", body))
        story.append(Paragraph(cohort.body, body))

    # --- Page 3: income and tenure commentary ---
    it = card.income_and_tenure
    story.append(Paragraph("Household income", h1))
    story.append(Paragraph(it.income_commentary, body))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Housing tenure", h2))
    story.append(Paragraph(it.tenure_commentary, body))
    story.append(Spacer(1, 5 * mm))

    dc = card.data_confidence
    story.append(Paragraph(f"Data confidence: {dc.level}", h2))
    story.append(Paragraph(dc.note, body))
    if dc.suppressed_fields:
        story.append(
            Paragraph("Suppressed inputs: " + ", ".join(dc.suppressed_fields), body)
        )

    doc.build(story)
    return buffer.getvalue()


def _two_col_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(
        [[label, value] for label, value in rows], colWidths=[80 * mm, 80 * mm]
    )
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), _BODY_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666666")),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table
