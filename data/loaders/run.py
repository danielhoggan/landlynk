"""CLI to run a reference data load.

Usage examples (run from the data directory, with a downloaded source file):

    python -m loaders.run geo_lookup --source OA_to_LAD.csv
    python -m loaders.run geo_boundaries --source MSOA.geojson --area-type MSOA
    python -m loaders.run census_demographics --source age.csv \
        --households-source households.csv
    python -m loaders.run census_tenure --source tenure.csv
    python -m loaders.run income_estimates --source income.xlsx
    python -m loaders.run postcode_lookup --source codepoint.csv

The database URL comes from --database-url or the DATABASE_URL environment
variable. Sources are downloaded by you from the open portals listed in
sources.yaml; this CLI reads local files so it works regardless of network
policy and is stable against portal URL changes.
"""

from __future__ import annotations

import argparse
import os

from .census import CensusDemographicsLoader, CensusTenureLoader
from .db import ReferenceDB
from .geography import BoundariesLoader, GeoLookupLoader
from .income import IncomeLoader
from .manifest import load_manifest
from .postcodes import PostcodeLoader

DATASETS = (
    "geo_lookup",
    "geo_boundaries",
    "census_demographics",
    "census_tenure",
    "income_estimates",
    "postcode_lookup",
)


def build_loader(dataset: str, args: argparse.Namespace, db: ReferenceDB):
    spec = load_manifest()[dataset]
    if dataset == "geo_lookup":
        return GeoLookupLoader(spec, args.source, db)
    if dataset == "geo_boundaries":
        return BoundariesLoader(spec, args.source, db=db, area_type=args.area_type)
    if dataset == "census_demographics":
        if not args.households_source:
            raise SystemExit("census_demographics needs --households-source")
        return CensusDemographicsLoader(
            spec,
            args.source,
            households_source=args.households_source,
            area_type=args.area_type,
            db=db,
        )
    if dataset == "census_tenure":
        return CensusTenureLoader(spec, args.source, area_type=args.area_type, db=db)
    if dataset == "income_estimates":
        return IncomeLoader(spec, args.source, area_type=args.area_type, db=db)
    if dataset == "postcode_lookup":
        return PostcodeLoader(spec, args.source, has_header=args.has_header, db=db)
    raise SystemExit(f"Unknown dataset: {dataset}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a LandLynk reference data load")
    parser.add_argument("dataset", choices=DATASETS)
    parser.add_argument("--source", required=True, help="Path to the downloaded file")
    parser.add_argument("--households-source", help="Household composition CSV")
    parser.add_argument("--area-type", default="MSOA", choices=["MSOA", "LA"])
    parser.add_argument(
        "--has-header", action="store_true", help="CSV has a header row"
    )
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()

    if not args.database_url:
        raise SystemExit("Set --database-url or the DATABASE_URL environment variable")

    db = ReferenceDB(args.database_url)
    loader = build_loader(args.dataset, args, db)
    count = loader.run()
    print(f"Loaded {count} rows into {loader.target_table}")


if __name__ == "__main__":
    main()
