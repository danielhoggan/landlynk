"""Versioned, auditable reference data loader base.

Reference data (ONS, OS, GWI) loads through a versioned loader. Each load
records source, version and date so refreshes are auditable (CLAUDE.md,
house-standards.md). Never hand-edit reference tables; always go through a
loader so provenance is captured in the reference_load table.

This is the loader contract. Concrete loaders per dataset (boundaries, census,
income, postcodes) subclass it and implement fetch and transform. ONS
suppression and rounding are handled in transform: a suppressed cell maps to
None, never zero.

The ``target_table``, ``columns`` and ``load`` are wired so the same DB writer
serves every loader. ``fetch`` reads from a local path or URL; transforms are
pure and unit tested.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .db import ReferenceDB


@dataclass(frozen=True)
class SourceSpec:
    target_table: str
    provider: str
    licence: str
    version: str
    url: str


class ReferenceLoader(abc.ABC):
    """One loader per reference dataset.

    ``source`` is a local file path or URL the concrete loader knows how to
    read. ``db`` is the writer; it is optional so transforms can be exercised in
    tests without a database.
    """

    #: Target table name in Postgres.
    target_table: str
    #: Ordered column names the rows from ``transform`` provide.
    columns: tuple[str, ...]
    #: Optional map of column name to a PostGIS SQL expression with one %s,
    #: used to write geometry columns from a GeoJSON string.
    geometry_columns: dict[str, str] = {}

    def __init__(
        self, spec: SourceSpec, source: str, db: ReferenceDB | None = None
    ) -> None:
        self.spec = spec
        self.source = source
        self.db = db

    @abc.abstractmethod
    def fetch(self) -> object:
        """Download or open the raw source. No transformation here."""

    @abc.abstractmethod
    def transform(self, raw: object) -> list[dict]:
        """Map raw source to rows for the target table.

        Suppressed or unavailable ONS cells must become None, never zero.
        """

    def load(self, rows: list[dict]) -> int:
        """Replace the target table contents and record provenance.

        Uses the shared DB writer, which truncates and bulk inserts in one
        transaction and records a reference_load row capturing target_table,
        source, version and date.
        """
        if self.db is None:
            raise RuntimeError("No database configured for this loader")
        return self.db.replace_table(
            table=self.target_table,
            columns=self.columns,
            rows=rows,
            source=self.spec.provider,
            version=self.spec.version,
            geometry_columns=self.geometry_columns,
        )

    def run(self) -> int:
        """Full load: fetch, transform, load. Returns rows loaded."""
        raw = self.fetch()
        rows = self.transform(raw)
        return self.load(rows)
