# PROJECT_CONTEXT.md

The what and why behind the Geographic Intelligence Engine. Read after CLAUDE.md. Build detail is in SCOPING.md.

## The problem

Marketing strategy for a place is too often built on assumption. We have a repeatable, data-led method that grounds it in evidence: take a development location, define a realistic catchment, pull open ONS data for that catchment, profile the people who live there, and turn that profile into a strategy. The output is a Battlecard that tells a development or campaign team who to target, how to price, which channels to use and what to say.

The method works. It has been used on Tilia and Hopkins new-build developments and on PfP Leisure centre catchments. But it carries one manual bottleneck and stops short of being a product. We are fixing both.

## What we are building

A platform that does the whole method automatically and makes the final step interactive.

Input: a development postcode, or an OS National Grid reference for sites with no postcode yet (common for new developments).

Output: an interactive catchment map where every area is scored and ranked by how worth targeting it is, and clicking any area opens its full Battlecard and deep-dive analysis. Plus exports: PDF and PPTX Battlecards to the client brand, and a KML layer for Google Earth.

## The method, end to end

1. Catchment. A 30-minute drive-time zone around the development. Automated via geocode then isochrone, replacing the old manual smappen step.
2. Define. The MSOA or LA areas whose boundaries fall inside the catchment, found by spatial intersect.
3. Ingest. ONS Census 2021 and ONS income estimates for those areas.
4. Analyse. Income (mean vs median), tenure split, age skew, household type, and the strategic signals these imply.
5. Strategise. The Battlecard: positioning, pricing rationale, channel mix, key messages, audience tiers.
6. Visualise and act. The interactive map and clickable deep-dives, plus KML and document exports.

## Why it matters strategically

- It is built entirely on open public data, so there are no data licences and no per-client data cost.
- It is reproducible and auditable. Any ranking or recommendation can be traced back to the data and config that produced it.
- It is geography-agnostic and sector-flexible. The same engine serves residential property, leisure, retail site selection, health planning and local authority communications.
- The interactive, clickable output removes the need for GIS expertise on the client or delivery side. A spreadsheet becomes a navigable map.

## Reference output

The Abbots Vale Battlecard is the gold standard for a single area's output. Three pages: a visual summary (key stats, audience and messaging, development features, three charts, catchment map, developer logo), and two commentary pages (audience and demographics, then income and tenure). The product must generate this quality automatically, per prioritised area, from the structured Battlecard payload.

## Users

- Internal strategy and delivery teams. Run the analysis, present the outputs.
- Client-facing teams. Use Battlecards and maps in pitches and reviews.
- Clients (later). Self-serve via a white-labelled portal, out of MVP scope.

## What good looks like

A user pastes a postcode or grid ref and, in one session, gets a ranked catchment map with per-area deep-dives, no GIS skills needed, with every ranking explainable and every output refreshable when ONS updates. Catchment definition that used to take 15 to 30 minutes by eye now takes under a second.

## Scope discipline

MVP is the residential use case (Tilia, Hopkins) at MSOA level, end to end, with PDF export. Leisure (PfP, LA level), PPTX brand export, expanded data layers (IMD, broadband, transport, planning), LLM-assisted commentary and the client portal are later phases. Phasing is in SCOPING.md Section 10. Do not pull later-phase work into MVP without a decision.
