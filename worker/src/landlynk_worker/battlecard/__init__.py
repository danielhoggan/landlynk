"""The Battlecard payload: one source of truth, four render surfaces."""

from .assemble import (
    CatchmentStats,
    DevelopmentInfo,
    IncomeContext,
    assemble_battlecard,
)
from .pdf import render_battlecard_pdf
from .pptx import render_battlecard_pptx
from .schema import BATTLECARD_SCHEMA_VERSION, Battlecard

__all__ = [
    "Battlecard",
    "BATTLECARD_SCHEMA_VERSION",
    "CatchmentStats",
    "DevelopmentInfo",
    "IncomeContext",
    "assemble_battlecard",
    "render_battlecard_pdf",
    "render_battlecard_pptx",
]
