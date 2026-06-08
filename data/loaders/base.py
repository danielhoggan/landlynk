"""Versioned, auditable reference data loader base.

Reference data (ONS, OS, GWI) loads through a versioned loader. Each load
records source, version and date so refreshes are auditable (CLAUDE.md,
house-standards.md). Never hand-edit reference tables; always go through a
loader so provenance is captured in the reference_load table.

This is the loader contract. Concrete loaders per dataset (boundaries, census,
income, postcodes, personas) subclass it and implement fetch and transform.
ONS suppression and rounding are handled in transform: a suppressed cell maps
to None, never zero.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSpec:
    target_table: str
    provider: str
    licence: str
    version: str
    url: str


class ReferenceLoader(abc.ABC):
    """One loader per reference dataset."""

    def __init__(self, spec: SourceSpec) -> None:
        self.spec = spec

    @abc.abstractmethod
    def fetch(self) -> object:
        """Download or open the raw source. No transformation here."""

    @abc.abstractmethod
    def transform(self, raw: object) -> list[dict]:
        """Map raw source to rows for the target table.

        Suppressed or unavailable ONS cells must become None, never zero.
        """

    @abc.abstractmethod
    def load(self, rows: list[dict]) -> int:
        """Replace the target table contents and record provenance.

        Implementations write the rows and insert a reference_load row capturing
        target_table, source, source_version and loaded_at. Returns the row
        count loaded.
        """

    def run(self) -> int:
        """Full load: fetch, transform, load. Returns rows loaded."""
        raw = self.fetch()
        rows = self.transform(raw)
        return self.load(rows)
