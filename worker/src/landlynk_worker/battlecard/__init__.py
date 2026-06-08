"""The Battlecard payload: one source of truth, four render surfaces."""

from .assemble import (
    DevelopmentInfo,
    IncomeContext,
    assemble_battlecard,
)
from .schema import BATTLECARD_SCHEMA_VERSION, Battlecard

__all__ = [
    "Battlecard",
    "BATTLECARD_SCHEMA_VERSION",
    "DevelopmentInfo",
    "IncomeContext",
    "assemble_battlecard",
]
