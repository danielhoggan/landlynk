"""PDF export of a Battlecard.

Renders the single Battlecard payload to a PDF, the third of the four surfaces.
Layout follows the Abbots Vale reference: a visual summary then audience and
demographic commentary then income and tenure commentary (SCOPING.md Section 9).

Brand theming is per client and passed in, never hard-coded (design-framework.md).
Headings use the theme primary colour, defaulting to Royal Blue. Document font
is Poppins; the TTF files are registered at startup when available (the worker
image downloads them at build) and fall back to Helvetica otherwise. Generated
prose already follows the house conventions (no em dashes, no Oxford commas, no
markdown headers).
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepInFrame,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .schema import Battlecard, DataValue

# Default document heading colour where a client brand does not override.
_DEFAULT_HEADING = "#2F6B3A"  # LandLynk green
_GOLD = colors.HexColor("#C9A24B")
_GREY = colors.HexColor("#9AA3AD")
_INK = colors.HexColor("#1E2A32")
_TENURE_COLORS = [
    colors.HexColor("#C04A1F"),
    colors.HexColor("#1F5A3C"),
    colors.HexColor("#0A1F44"),
    colors.HexColor("#8E959C"),
]


def _register_fonts() -> tuple[str, str]:
    """Register Poppins from the font directory, falling back to Helvetica.

    The worker image fetches Poppins-Regular and Poppins-SemiBold at build time
    into LANDLYNK_FONT_DIR (default /app/fonts). When the files are absent, as in
    the offline test environment, the document uses Helvetica so rendering never
    fails on a missing font.
    """
    font_dir = Path(os.environ.get("LANDLYNK_FONT_DIR", "/app/fonts"))
    regular = font_dir / "Poppins-Regular.ttf"
    bold = font_dir / "Poppins-SemiBold.ttf"
    if regular.is_file() and bold.is_file():
        try:
            pdfmetrics.registerFont(TTFont("Poppins", str(regular)))
            pdfmetrics.registerFont(TTFont("Poppins-Bold", str(bold)))
            return "Poppins", "Poppins-Bold"
        except Exception:  # corrupt or unreadable font, fall back rather than fail
            pass
    return "Helvetica", "Helvetica-Bold"


_BODY_FONT, _BOLD_FONT = _register_fonts()


def _fmt(dv: DataValue, *, money: bool = False, pct: bool = False) -> str:
    """Format a DataValue, honouring suppression (null, never zero)."""
    if dv.value is None:
        return "Suppressed" if dv.suppressed else "Not available"
    if money:
        return f"£{dv.value:,.0f}"
    if pct:
        return f"{dv.value:.1f}%"
    return f"{dv.value:,.0f}"


def _styles(heading_hex: str) -> dict:
    navy = colors.HexColor(heading_hex)
    base = getSampleStyleSheet()
    return {
        "navy": navy,
        "title": ParagraphStyle(
            "Title",
            parent=base["Normal"],
            fontName=_BOLD_FONT,
            fontSize=20,
            leading=22,
            textColor=colors.white,
        ),
        "location": ParagraphStyle(
            "Loc",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=10,
            textColor=_GOLD,
            spaceBefore=2,
        ),
        "side_label": ParagraphStyle(
            "SideLabel",
            parent=base["Normal"],
            fontName=_BOLD_FONT,
            fontSize=8,
            textColor=_GOLD,
            spaceBefore=6,
            spaceAfter=2,
        ),
        "stat_value": ParagraphStyle(
            "StatVal",
            parent=base["Normal"],
            fontName=_BOLD_FONT,
            fontSize=13,
            leading=14,
            textColor=colors.white,
        ),
        "stat_label": ParagraphStyle(
            "StatLab",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=6.5,
            textColor=_GREY,
        ),
        "strap": ParagraphStyle(
            "Strap",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=8,
            textColor=_GREY,
            fontStyle="italic",
        ),
        "pillars": ParagraphStyle(
            "Pillars",
            parent=base["Normal"],
            fontName=_BOLD_FONT,
            fontSize=10,
            textColor=_INK,
            alignment=TA_CENTER,
        ),
        "header": ParagraphStyle(
            "HeaderBar",
            parent=base["Normal"],
            fontName=_BOLD_FONT,
            fontSize=9,
            textColor=colors.white,
            backColor=navy,
            borderPadding=(4, 4, 4, 4),
            spaceBefore=4,
            spaceAfter=4,
            leading=12,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=9,
            textColor=_INK,
            leading=12,
            leftIndent=8,
            bulletIndent=0,
        ),
        "bullet_bold": ParagraphStyle(
            "BulletBold",
            parent=base["Normal"],
            fontName=_BOLD_FONT,
            fontSize=9,
            textColor=_INK,
            leading=12,
        ),
        "chart_label": ParagraphStyle(
            "ChartLabel",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=7,
            textColor=_INK,
        ),
    }


def render_battlecard_pdf(
    card: Battlecard,
    heading_color: str | None = None,
    map_geometry: dict | None = None,
    logo: bytes | None = None,
    accent: str | None = None,
    map_image: bytes | None = None,
) -> bytes:
    """Render a single Battlecard payload to PDF bytes (one landscape page)."""
    return render_battlecards_pdf(
        [card],
        heading_color,
        [map_geometry],
        logo=logo,
        accent=accent,
        map_image=map_image,
    )


def render_battlecards_pdf(
    cards: list[Battlecard],
    heading_color: str | None = None,
    geometries: list[dict | None] | None = None,
    logo: bytes | None = None,
    accent: str | None = None,
    map_image: bytes | None = None,
) -> bytes:
    """Render one or more Battlecards into a single PDF, one page per area.

    The single-slide reference layout: a brand sidebar, two messaging columns
    and three charts. Used for the shortlist export so a builder gets every
    selected area as one combined document.
    """
    heading_hex = heading_color or _DEFAULT_HEADING
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=(
            "LandLynk Battlecards"
            if len(cards) != 1
            else f"Battlecard {cards[0].area_code}"
        ),
    )
    styles = _styles(heading_hex)
    accent_color = colors.HexColor(accent) if accent else _GOLD
    story: list = []
    for i, card in enumerate(cards):
        if i > 0:
            story.append(PageBreak())
        geom = geometries[i] if geometries and i < len(geometries) else None
        story.extend(_card_flowables(card, styles, geom, logo, accent_color, map_image))
    doc.build(story)
    return buffer.getvalue()


def _group_amenities(amenities: list) -> list[tuple[str, list]]:
    order = ["Transport", "Retail", "Leisure", "Education", "Healthcare", "Other"]
    grouped: dict[str, list] = {}
    for a in amenities:
        grouped.setdefault(a.category, []).append(a)
    return [(c, grouped[c]) for c in order if grouped.get(c)]


def _numf(dv: DataValue) -> float:
    return 0.0 if dv.value is None else float(dv.value)


def _short_money(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1_000_000:
        return f"£{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"£{value / 1_000:.0f}k"
    return f"£{value:,.0f}"


def _bar_drawing(
    categories: list[str],
    values: list[float],
    color: colors.Color,
    width: float,
    height: float,
) -> Drawing:
    d = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x = 14
    chart.y = 24
    chart.width = width - 24
    chart.height = height - 40
    chart.data = [values]
    chart.categoryAxis.categoryNames = [str(c) for c in categories]
    chart.categoryAxis.labels.fontSize = 6
    chart.categoryAxis.labels.fontName = _BODY_FONT
    chart.categoryAxis.labels.angle = 20
    chart.categoryAxis.labels.dy = -4
    chart.valueAxis.visible = False
    chart.valueAxis.valueMin = 0
    chart.bars[0].fillColor = color
    chart.bars[0].strokeColor = None
    d.add(chart)
    return d


def _pie_drawing(
    values: list[float], palette: list, width: float, height: float
) -> Drawing:
    d = Drawing(width, height)
    pie = Pie()
    size = min(width, height) - 20
    pie.width = size
    pie.height = size
    pie.x = (width - size) / 2
    pie.y = 6
    pie.data = [max(v, 0.0001) for v in values]
    pie.innerRadiusFraction = 0.55
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    for i in range(len(values)):
        pie.slices[i].fillColor = palette[i % len(palette)]
    d.add(pie)
    return d


def _map_drawing(
    geometry: dict | None,
    width: float,
    height: float,
    fill: colors.Color = _GOLD,
) -> Drawing | None:
    """An accent catchment silhouette for the sidebar, or None if no geometry."""
    from reportlab.graphics.shapes import Polygon

    from .mapshape import fit_ring

    pts = fit_ring(geometry, width, height, pad=3, y_down=False)
    if len(pts) < 3:
        return None
    flat: list[float] = []
    for x, y in pts:
        flat.extend([x, y])
    d = Drawing(width, height)
    d.add(
        Polygon(
            points=flat,
            fillColor=fill,
            strokeColor=colors.white,
            strokeWidth=0.75,
        )
    )
    return d


def _card_flowables(
    card: Battlecard,
    st: dict,
    map_geometry: dict | None = None,
    logo: bytes | None = None,
    accent: colors.Color = _GOLD,
    map_image: bytes | None = None,
) -> list:
    vs = card.visual_summary
    h = vs.header
    stats = vs.key_statistics
    navy = st["navy"]

    # --- sidebar cell -------------------------------------------------------
    side: list = [
        Paragraph(h.development_name.upper(), st["title"]),
    ]
    location = ", ".join(p for p in [h.town, h.postcode] if p)
    if location:
        side.append(Paragraph(location, st["location"]))
    side.append(Paragraph("KEY STATISTICS", st["side_label"]))

    tiles = [
        (f"{stats.bed_range} Bed", "HOMES"),
        (_short_money(stats.price_from.value), "FROM"),
        (_short_money(stats.average_household_income.value), "AVG HH INCOME"),
        (f"{_fmt(stats.median_age)} yrs", "MEDIAN AGE"),
        (_fmt(stats.owner_occupied_percentage, pct=True), "OWNER OCCUPIED"),
        (_fmt(stats.population_catchment), "POP. CATCHMENT"),
    ]
    rows = []
    for i in range(0, len(tiles), 2):
        row = []
        for value, label in tiles[i : i + 2]:
            row.append(
                [Paragraph(value, st["stat_value"]), Paragraph(label, st["stat_label"])]
            )
        rows.append(row)
    stat_table = Table(rows, colWidths=[30 * mm, 30 * mm])
    stat_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    side.append(stat_table)
    # Prefer the OSM basemap image for context; fall back to the vector outline.
    placed_map = False
    if map_image:
        from reportlab.platypus import Image

        try:
            mimg = Image(io.BytesIO(map_image), width=54 * mm, kind="proportional")
            side.append(Spacer(1, 3 * mm))
            side.append(mimg)
            placed_map = True
        except Exception:  # fall back to the silhouette
            placed_map = False
    if not placed_map:
        map_drawing = _map_drawing(map_geometry, 54 * mm, 34 * mm, fill=accent)
        if map_drawing is not None:
            side.append(Spacer(1, 3 * mm))
            side.append(map_drawing)
    if logo:
        from reportlab.platypus import Image

        try:
            img = Image(io.BytesIO(logo), height=14 * mm, kind="proportional")
            img.drawWidth = min(img.drawWidth, 54 * mm)
            side.append(Spacer(1, 3 * mm))
            side.append(img)
        except Exception:  # decorative; never fail the export on a bad image
            pass
    elif h.strapline:
        side.append(Spacer(1, 3 * mm))
        side.append(Paragraph(h.strapline, st["strap"]))

    # --- main cell ----------------------------------------------------------
    main: list = []
    if h.lifestyle_pillars:
        main.append(Paragraph("  ·  ".join(h.lifestyle_pillars), st["pillars"]))
        main.append(Spacer(1, 2 * mm))

    main.append(Paragraph("TARGET AUDIENCE &amp; MESSAGING", st["header"]))
    lines = 0
    for m in vs.audience_messaging:
        if lines >= 7:
            break
        main.append(Paragraph(f"{m.tier.title()}: {m.audience}", st["bullet_bold"]))
        lines += 1
        for line in m.message_lines:
            if lines >= 7:
                break
            main.append(Paragraph(line, st["bullet"], bulletText="•"))
            lines += 1

    profile = card.local_area_profile
    if profile:
        main.append(Paragraph("LOCAL AREA &amp; AMENITIES", st["header"]))
        main.append(Paragraph(profile.description, st["bullet_bold"]))
        for cat, items in _group_amenities(profile.amenities):
            names = ", ".join(a.name for a in items[:6])
            main.append(Paragraph(f"<b>{cat}:</b> {names}", st["bullet"]))
    else:
        main.append(Paragraph("THE DEVELOPMENT &amp; LOCATION", st["header"]))
        where = f" in {h.town}" if h.town else ""
        summary = (
            f"{stats.bed_range} bed homes from {_short_money(stats.price_from.value)}{where}"
            if stats.price_from.value is not None
            else f"{stats.bed_range} bed homes{where}"
        )
        main.append(Paragraph(summary, st["bullet_bold"]))
        for feature in vs.development_features[:7]:
            main.append(Paragraph(feature, st["bullet"], bulletText="•"))
    main.append(Spacer(1, 2 * mm))

    # charts row
    charts = vs.charts
    cw = 62 * mm
    ch = 42 * mm
    age = _bar_drawing(
        [b.label for b in charts.age_demographics],
        [_numf(b.percentage) for b in charts.age_demographics],
        navy,
        cw,
        ch,
    )
    inc = charts.household_income
    income = _bar_drawing(
        ["Mean", "Median", "Low LA", "High LA"],
        [
            _numf(inc.mean),
            _numf(inc.median),
            _numf(inc.lowest_la.value),
            _numf(inc.highest_la.value),
        ],
        navy,
        cw,
        ch,
    )
    t = charts.housing_tenure
    tenure = _pie_drawing(
        [
            _numf(t.owns_outright),
            _numf(t.owns_with_mortgage),
            _numf(t.social_rented),
            _numf(t.private_rented),
        ],
        _TENURE_COLORS,
        cw,
        ch,
    )
    chart_table = Table(
        [
            [
                Paragraph("AGE DEMOGRAPHICS", st["header"]),
                Paragraph("HOUSEHOLD INCOME", st["header"]),
                Paragraph("HOUSING TENURE", st["header"]),
            ],
            [age, income, tenure],
            [
                Paragraph("", st["chart_label"]),
                Paragraph("", st["chart_label"]),
                Paragraph("Outright, mortgage, social, private", st["chart_label"]),
            ],
        ],
        colWidths=[cw + 4 * mm, cw + 4 * mm, cw + 4 * mm],
    )
    chart_table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    main.append(chart_table)

    master = Table([[side, main]], colWidths=[64 * mm, 205 * mm])
    master.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), navy),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 8),
                ("RIGHTPADDING", (0, 0), (0, 0), 8),
                ("TOPPADDING", (0, 0), (0, 0), 10),
                ("LEFTPADDING", (1, 0), (1, 0), 10),
                ("RIGHTPADDING", (1, 0), (1, 0), 4),
                ("TOPPADDING", (1, 0), (1, 0), 4),
            ]
        )
    )
    return [KeepInFrame(277 * mm, 188 * mm, [master], mode="shrink")]
