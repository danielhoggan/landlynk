"""Read the reference data source manifest (sources.yaml) into SourceSpecs."""

from __future__ import annotations

import os

import yaml

from .base import SourceSpec

_DEFAULT_MANIFEST = os.path.join(os.path.dirname(__file__), os.pardir, "sources.yaml")


def load_manifest(path: str | None = None) -> dict[str, SourceSpec]:
    """Return a map of dataset key to SourceSpec from the manifest."""
    with open(path or _DEFAULT_MANIFEST, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    sources = data.get("sources") or {}
    specs: dict[str, SourceSpec] = {}
    for key, entry in sources.items():
        specs[key] = SourceSpec(
            target_table=entry.get("target_table", key),
            provider=entry.get("provider", "unknown"),
            licence=entry.get("licence", "unknown"),
            version=str(entry.get("version", "TBC")),
            url=str(entry.get("url", "TBC")),
        )
    return specs
