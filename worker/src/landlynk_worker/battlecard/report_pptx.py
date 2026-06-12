"""Multi-slide report deck from a Battlecard payload.

The fuller, unbranded-by-default analytical report (the LA Insight equivalent):
a cover, an overview, the AI area profile, the three demographic charts with
narrative, a marketing development plan and a methodology appendix. It renders
from the same single Battlecard payload as the one-slide card, and themes to the
brand (primary, secondary, accent colours and logo) when those are supplied.

One area is one report (use the combined Battlecard for a whole-catchment study
area). Charts are native and editable. Generated prose already follows the house
conventions.
"""

from __future__ import annotations

import io

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.slide import Slide
from pptx.util import Inches, Length, Pt

from .schema import Battlecard, DataValue

_DEFAULT_HEADING = "4169E1"
_FONT = "Poppins"
_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
_INK = RGBColor(0x1E, 0x2A, 0x32)
_GREY = RGBColor(0x6A, 0x73, 0x7B)
_LIGHT = RGBColor(0xF4, 0xF5, 0xF7)
_GOLD = RGBColor(0xC9, 0xA2, 0x4B)
_TENURE_COLORS = [
    RGBColor(0xC0, 0x4A, 0x1F),
    RGBColor(0x1F, 0x5A, 0x3C),
    RGBColor(0x0A, 0x1F, 0x44),
    RGBColor(0x8E, 0x95, 0x9C),
]
_AMENITY_ORDER = ["Transport", "Retail", "Leisure", "Education", "Healthcare", "Other"]


def _hex(color: str | None, fallback: str = _DEFAULT_HEADING) -> RGBColor:
    return RGBColor.from_string((color or fallback).lstrip("#"))


def _num(dv: DataValue) -> float:
    return 0.0 if dv.value is None else float(dv.value)


def _money(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1_000_000:
        return f"£{value / 1_000_000:.1f}m"
    if value >= 1_000:
        return f"£{value / 1_000:.0f}k"
    return f"£{value:,.0f}"


def render_report_pptx(
    card: Battlecard,
    heading_color: str | None = None,
    logo: bytes | None = None,
    accent: str | None = None,
    secondary: str | None = None,
    map_image: bytes | None = None,
) -> bytes:
    """Render the full report deck for one Battlecard payload."""
    navy = _hex(heading_color)
    accent_rgb = _hex(accent, "C9A24B")
    secondary_rgb = _hex(secondary, "1F5A3C")
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    theme = {"navy": navy, "accent": accent_rgb, "secondary": secondary_rgb}
    _cover(prs.slides.add_slide(blank), card, theme, logo)
    _overview(prs.slides.add_slide(blank), card, theme)
    _area_profile(prs.slides.add_slide(blank), card, theme, map_image)
    _age(prs.slides.add_slide(blank), card, theme)
    _income(prs.slides.add_slide(blank), card, theme)
    _tenure(prs.slides.add_slide(blank), card, theme)
    _plan(prs.slides.add_slide(blank), card, theme)
    _appendix(prs.slides.add_slide(blank), card, theme)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# --- primitives -------------------------------------------------------------


def _rect(
    slide: Slide,
    left: Length,
    top: Length,
    width: Length,
    height: Length,
    color: RGBColor,
) -> None:
    shape = slide.shapes.add_shape(1, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    shape.shadow.inherit = False


def _text(
    slide: Slide,
    left: Length,
    top: Length,
    width: Length,
    height: Length,
    lines: list[tuple],
) -> None:
    """Each line is (text, size, color, bold, italic)."""
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    for i, (text, size, color, bold, italic) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(3)
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.name = _FONT
        run.font.color.rgb = color


def _section(slide: Slide, label: str, title: str, navy: RGBColor) -> None:
    _text(
        slide,
        Inches(0.6),
        Inches(0.45),
        Inches(11),
        Inches(0.3),
        [(label.upper(), 11, _GOLD, True, False)],
    )
    _text(
        slide,
        Inches(0.6),
        Inches(0.75),
        Inches(11),
        Inches(0.6),
        [(title, 26, navy, True, False)],
    )


def _bar(
    slide: Slide,
    left: Length,
    top: Length,
    width: Length,
    height: Length,
    cats: list[str],
    vals: list[float],
    color: RGBColor,
) -> None:
    data = CategoryChartData()
    data.categories = cats
    data.add_series("", vals)
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, left, top, width, height, data
    )
    chart = frame.chart
    chart.has_legend = False
    chart.has_title = False
    try:
        chart.series[0].format.fill.solid()
        chart.series[0].format.fill.fore_color.rgb = color
        chart.value_axis.visible = False
        chart.value_axis.has_major_gridlines = False
        chart.category_axis.tick_labels.font.size = Pt(10)
        chart.category_axis.tick_labels.font.name = _FONT
    except Exception:
        pass


def _donut(
    slide: Slide,
    left: Length,
    top: Length,
    width: Length,
    height: Length,
    cats: list[str],
    vals: list[float],
) -> None:
    data = CategoryChartData()
    data.categories = cats
    data.add_series("", vals)
    frame = slide.shapes.add_chart(
        XL_CHART_TYPE.DOUGHNUT, left, top, width, height, data
    )
    chart = frame.chart
    chart.has_title = False
    chart.has_legend = True
    try:
        chart.legend.position = XL_LEGEND_POSITION.RIGHT
        chart.legend.include_in_layout = False
        chart.legend.font.size = Pt(10)
        points = chart.plots[0].series[0].points
        for i, pt in enumerate(points):
            pt.format.fill.solid()
            pt.format.fill.fore_color.rgb = _TENURE_COLORS[i % len(_TENURE_COLORS)]
    except Exception:
        pass


# --- slides -----------------------------------------------------------------


def _cover(slide: Slide, card: Battlecard, theme: dict, logo: bytes | None) -> None:
    h = card.visual_summary.header
    _rect(slide, 0, 0, Inches(13.333), Inches(7.5), theme["navy"])
    _rect(slide, 0, Inches(3.5), Inches(13.333), Inches(0.06), theme["accent"])
    _text(
        slide,
        Inches(0.9),
        Inches(2.0),
        Inches(11.5),
        Inches(0.4),
        [("HOUSING DEVELOPMENT INTELLIGENCE", 13, theme["accent"], True, False)],
    )
    _text(
        slide,
        Inches(0.9),
        Inches(2.5),
        Inches(11.5),
        Inches(1.0),
        [(h.development_name, 40, _WHITE, True, False)],
    )
    location = ", ".join(p for p in [h.town, h.postcode] if p)
    _text(
        slide,
        Inches(0.9),
        Inches(3.7),
        Inches(11.5),
        Inches(0.5),
        [(location or "Area analysis report", 16, _WHITE, False, False)],
    )
    _text(
        slide,
        Inches(0.9),
        Inches(6.6),
        Inches(11.5),
        Inches(0.4),
        [
            (
                "LandLynk · ONS Census 2021 and ONS income estimates",
                11,
                _GOLD,
                False,
                False,
            )
        ],
    )
    if logo:
        try:
            slide.shapes.add_picture(
                io.BytesIO(logo), Inches(10.8), Inches(0.6), height=Inches(0.7)
            )
        except Exception:
            pass


def _overview(slide: Slide, card: Battlecard, theme: dict) -> None:
    ks = card.visual_summary.key_statistics
    _section(slide, "Overview", "Key statistics at a glance", theme["navy"])
    tiles = [
        (_fmt_int(ks.population_catchment), "POPULATION"),
        (_fmt_int(ks.median_age, suffix=""), "MEDIAN AGE"),
        (_money(ks.average_household_income.value), "AVG HH INCOME"),
        (_fmt_int(ks.households_catchment), "HOUSEHOLDS"),
        (_pct(ks.owner_occupied_percentage), "OWNER OCCUPIED"),
        (f"{ks.bed_range} bed", "PRODUCT"),
    ]
    for i, (value, label) in enumerate(tiles):
        col = i % 3
        row = i // 3
        left = Inches(0.6 + col * 4.05)
        top = Inches(2.0 + row * 2.0)
        _rect(slide, left, top, Inches(3.8), Inches(1.7), _LIGHT)
        _rect(slide, left, top, Inches(0.08), Inches(1.7), theme["accent"])
        _text(
            slide,
            left + Inches(0.35),
            top + Inches(0.35),
            Inches(3.3),
            Inches(0.7),
            [(value, 30, theme["navy"], True, False)],
        )
        _text(
            slide,
            left + Inches(0.35),
            top + Inches(1.1),
            Inches(3.3),
            Inches(0.4),
            [(label, 11, _GREY, True, False)],
        )


def _area_profile(
    slide: Slide, card: Battlecard, theme: dict, map_image: bytes | None
) -> None:
    _section(slide, "Section 01", "Local area profile", theme["navy"])
    profile = card.local_area_profile
    desc = profile.description if profile else card.visual_summary.header.strapline
    _text(
        slide,
        Inches(0.6),
        Inches(1.7),
        Inches(7.2),
        Inches(2.0),
        [
            ("AREA DESCRIPTION", 11, _GOLD, True, False),
            (
                desc or "Generate an AI local area profile to populate this section.",
                13,
                _INK,
                False,
                False,
            ),
        ],
    )
    # Amenities grouped (left), map (right).
    if profile and profile.amenities:
        grouped: dict[str, list[str]] = {}
        for a in profile.amenities:
            grouped.setdefault(a.category, []).append(a.name)
        lines: list[tuple] = [("LOCAL AMENITIES", 11, _GOLD, True, False)]
        for cat in _AMENITY_ORDER:
            if grouped.get(cat):
                lines.append((cat.upper(), 10, theme["navy"], True, False))
                for name in grouped[cat][:4]:
                    lines.append((f"· {name}", 11, _INK, False, False))
        _text(slide, Inches(0.6), Inches(3.6), Inches(7.2), Inches(3.6), lines)
    if map_image:
        try:
            slide.shapes.add_picture(
                io.BytesIO(map_image), Inches(8.2), Inches(1.9), width=Inches(4.5)
            )
        except Exception:
            pass
    if card.context_metrics:
        lines: list[tuple] = [("LOCAL CONTEXT", 11, _GOLD, True, False)]
        for m in card.context_metrics:
            lines.append((f"{m.label}: {m.value:g} {m.unit}", 11, _INK, False, False))
        _text(slide, Inches(8.2), Inches(4.7), Inches(4.5), Inches(2.4), lines)


def _age(slide: Slide, card: Battlecard, theme: dict) -> None:
    _section(slide, "Chart 01", "Age demographic distribution", theme["navy"])
    charts = card.visual_summary.charts
    _bar(
        slide,
        Inches(0.6),
        Inches(1.7),
        Inches(7.2),
        Inches(4.8),
        [b.label for b in charts.age_demographics],
        [_num(b.percentage) for b in charts.age_demographics],
        theme["secondary"],
    )
    cohorts = card.audience_and_demographics.age_cohorts
    body = cohorts[0].body if cohorts else ""
    _text(
        slide,
        Inches(8.2),
        Inches(1.9),
        Inches(4.5),
        Inches(4.5),
        [("ANALYSIS", 11, _GOLD, True, False), (body, 12, _INK, False, False)],
    )


def _income(slide: Slide, card: Battlecard, theme: dict) -> None:
    _section(slide, "Chart 02", "Household income distribution", theme["navy"])
    inc = card.visual_summary.charts.household_income
    _bar(
        slide,
        Inches(0.6),
        Inches(1.7),
        Inches(7.2),
        Inches(4.8),
        [
            "Mean",
            "Median",
            inc.lowest_la.name or "Lowest",
            inc.highest_la.name or "Highest",
        ],
        [
            _num(inc.mean),
            _num(inc.median),
            _num(inc.lowest_la.value),
            _num(inc.highest_la.value),
        ],
        theme["secondary"],
    )
    _text(
        slide,
        Inches(8.2),
        Inches(1.9),
        Inches(4.5),
        Inches(4.5),
        [
            ("ANALYSIS", 11, _GOLD, True, False),
            (card.income_and_tenure.income_commentary, 12, _INK, False, False),
        ],
    )


def _tenure(slide: Slide, card: Battlecard, theme: dict) -> None:
    _section(slide, "Chart 03", "Housing tenure profile", theme["navy"])
    t = card.visual_summary.charts.housing_tenure
    _donut(
        slide,
        Inches(0.6),
        Inches(1.7),
        Inches(7.2),
        Inches(4.8),
        ["Owns outright", "Owns with mortgage", "Social rented", "Private rented"],
        [
            _num(t.owns_outright),
            _num(t.owns_with_mortgage),
            _num(t.social_rented),
            _num(t.private_rented),
        ],
    )
    _text(
        slide,
        Inches(8.2),
        Inches(1.9),
        Inches(4.5),
        Inches(4.5),
        [
            ("ANALYSIS", 11, _GOLD, True, False),
            (card.income_and_tenure.tenure_commentary, 12, _INK, False, False),
        ],
    )


def _plan(slide: Slide, card: Battlecard, theme: dict) -> None:
    _rect(slide, 0, 0, Inches(13.333), Inches(7.5), theme["navy"])
    _text(
        slide,
        Inches(0.6),
        Inches(0.5),
        Inches(12),
        Inches(0.4),
        [("STRATEGIC INTELLIGENCE", 11, theme["accent"], True, False)],
    )
    _text(
        slide,
        Inches(0.6),
        Inches(0.9),
        Inches(12),
        Inches(0.6),
        [("Marketing development plan", 26, _WHITE, True, False)],
    )

    tiers = card.audience_and_demographics.audience_tiers
    segments = " | ".join(f"{t.tier.title()}: {t.audience}" for t in tiers) or "n/a"
    messages: list[str] = []
    for m in card.visual_summary.audience_messaging:
        messages.extend(m.message_lines)
    cards = [
        ("PRIMARY TARGET SEGMENTS", segments),
        (
            "PRODUCT AND PRICING",
            f"{card.visual_summary.key_statistics.bed_range} bed. "
            + card.pricing_rationale.positioning,
        ),
        ("KEY MARKETING MESSAGES", "  •  ".join(messages[:5]) or "n/a"),
        ("ADDRESSABLE SEGMENTS", _segments_line(card)),
    ]
    for i, (label, body) in enumerate(cards):
        top = Inches(1.9 + i * 1.3)
        _rect(
            slide,
            Inches(0.6),
            top,
            Inches(12.1),
            Inches(1.15),
            RGBColor(0x14, 0x2A, 0x44),
        )
        _rect(slide, Inches(0.6), top, Inches(0.08), Inches(1.15), theme["accent"])
        _text(
            slide,
            Inches(0.9),
            top + Inches(0.12),
            Inches(11.6),
            Inches(0.95),
            [
                (label, 11, theme["accent"], True, False),
                (body, 12, _WHITE, False, False),
            ],
        )


def _appendix(slide: Slide, card: Battlecard, theme: dict) -> None:
    _section(slide, "Appendix", "Data sources and methodology", theme["navy"])
    sources = [
        (
            "ONS Census 2021 — Age (TS007)",
            "Single year of age counts, for population, median age and cohort shares.",
        ),
        (
            "ONS Census 2021 — Household composition (TS003) and tenure (TS054)",
            "Household counts and tenure mix used for the family and tenure signals.",
        ),
        (
            "ONS income estimates for small areas",
            "Net annual household income, for the income fit and affordability.",
        ),
        (
            "ONS median house prices by MSOA",
            "Latest median price paid, for the local price context and pricing.",
        ),
    ]
    lines: list[tuple] = []
    for title, body in sources:
        lines.append((title, 13, theme["navy"], True, False))
        lines.append((body, 11, _GREY, False, False))
    dc = card.data_confidence
    lines.append((f"Data confidence: {dc.level}. {dc.note}", 11, _INK, False, True))
    _text(slide, Inches(0.6), Inches(1.7), Inches(12), Inches(5.2), lines)


# --- helpers ----------------------------------------------------------------


def _fmt_int(dv: DataValue, suffix: str = "") -> str:
    if dv.value is None:
        return "n/a"
    return f"{dv.value:,.0f}{suffix}"


def _pct(dv: DataValue) -> str:
    return "n/a" if dv.value is None else f"{dv.value:.0f}%"


def _segments_line(card: Battlecard) -> str:
    seg = card.addressable_segments

    def n(dv: DataValue) -> str:
        return "n/a" if dv.value is None else f"{dv.value:,.0f}"

    return (
        f"FTB pipeline {n(seg.first_time_buyer_pipeline)}  •  "
        f"Downsizer pool {n(seg.downsizer_pool)}  •  "
        f"Family households {n(seg.family_households)}"
    )
