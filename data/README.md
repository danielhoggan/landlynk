# data

Reference data loaders and seed definitions for landlynk: ONS, OS and GWI.

## Principles

- All reference data is open or free tier. No third-party data licences. Adding
  any paid source needs sign-off (house-standards.md, data handling).
- Reference data loads through a versioned loader. Each load records source,
  version and date in the `reference_load` table so refreshes are auditable.
- Never hand-edit reference tables. Always load through a loader.
- ONS suppression and rounding are handled explicitly: a suppressed cell maps to
  NULL, never zero. Data confidence is surfaced in the deep-dive, not hidden.

## Layout

```
data/
  sources.yaml      manifest of every reference dataset, provider and licence
  loaders/
    base.py         the ReferenceLoader contract (fetch, transform, load, run)
```

## Datasets

See `sources.yaml`. The MVP residential path needs: geo lookup and boundaries
(ONS Open Geography Portal), census demographics and tenure (ONS Census 2021),
income estimates (ONS), and postcode lookup (OS CodePoint Open). GWI personas
enrich messaging and channel mix; confirm licence terms before embedding
persona-driven guidance in client outputs.

## Status

The loader contract and source manifest are defined. Concrete per-dataset
loaders and the download and transform logic are wired as the reference data is
brought in. Pin a concrete version and url in `sources.yaml` before each load.
