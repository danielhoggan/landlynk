# design-framework.md

The design system for the Geographic Intelligence Engine. The app shell defaults to the Mediaworks and Apple light or dark language, and white-labels to a client brand when the signed-in user belongs to a branded group. Battlecard exports always carry the client brand.

## App shell

The web app uses the standard Mediaworks HTML UI shell by default.

Theme toggle:
- Persistent light and dark mode toggle, bottom-left, position fixed.
- Light mode: Apple-style. Background #F5F5F7. Accent #0071E3.
- Dark mode: Mediaworks palette. Background #0D0D0D. Accent #DC167A.

White-labelling the shell:
- When the signed-in user is pinned to a builder_group, the shell takes that group's brand: logo, accent colour and typeface. The brand is the group's default brand, or the first brand by name when none is flagged.
- Users with no group keep the default Mediaworks/Apple theme. Internal users and admins are unscoped, so they see the default.
- Implemented as CSS variables (--brand-accent, --brand-font) consumed by the shell tokens, plus the brand logo in the wordmark slot. Never hard-code a client brand into shell components; the same shell takes any brand.

Layout shell:
- Mobile-first.
- Slide-out drawer navigation. Hamburger turns to an x. slideIn at 0.28s cubic-bezier. Blurred scrim behind the drawer. Scroll lock when open.
- Sticky frosted-glass top bar.
- Horizontal scrollable tab strip for section navigation.

Cards and components:
- 14px border-radius on cards.
- 1px borders. No shadow.
- Semantic colours: green #34C759, orange #FF9500, red #FF3B30. Use these for priority bands and status, not arbitrary colours.

Typography:
- App UI font: Inter.
- Web output font: Tenor Sans.
- Icons: lucide-react.

## The map (Step 6 surface)

The interactive catchment map is the centrepiece. It must read clearly on mobile and desktop.

- Base map: open-source tiles via MapLibre GL or Leaflet. No licensed tiles.
- The drive-time isochrone is drawn as a translucent overlay polygon so the catchment boundary is always visible.
- Each MSOA or LA inside the catchment is a clickable region, colour-coded by priority score using the semantic bands (green high priority, orange mid, red or muted low). Use a clear, accessible sequential scale, not a rainbow.
- A development pin marks the input location.
- Clicking a region opens its deep-dive in the slide-out drawer or a side panel, never a full page navigation. The map stays in view so the user keeps spatial context.
- An on-map or list ranking shows areas ordered by priority so the user sees the shortlist, not just the colour map.

On-location summary (the compact breakdown shown before the full deep-dive):
- Area name and code.
- Priority rank and score.
- Addressable population inside the catchment.
- Income fit, tenure signal, age skew, household type, as short labelled values.
- A clear call to open the full Battlecard.

## Battlecard render (deep-dive and exports)

The Battlecard is one structured payload rendered to four surfaces: the in-app drawer, PDF, PPTX and the KML balloon. The layout follows the Abbots Vale reference.

Page 1, visual summary:
- Header with development name, town, postcode, strapline and lifestyle pillars.
- Key statistics block: bed range, average household income, owner-occupied percentage, price from, median age, population catchment. Large stat callouts, small labels under each.
- Target audience and messaging: primary, secondary, tertiary tiers with message lines.
- The development and location: feature bullets.
- Three charts:
  - Age demographics, banded bar by age group (0 to 15, 16 to 34, 35 to 54, 55 to 74, 75 plus).
  - Household income, bar with mean, median, lowest LA and highest LA callouts.
  - Housing tenure, donut: owns outright, owns with mortgage, social rented, private rented.
- Catchment map panel and developer logo.

Page 2: audience messaging overview and demographic commentary, prose blocks per audience tier and per age cohort.

Page 3: household income commentary and tenure commentary, prose blocks with positioning implications.

## Brand theming for client outputs

Battlecard exports carry the client or developer brand, not the Mediaworks shell colours.

- Brand is supplied through a theme config per client (primary, secondary, accent, logo, fonts).
- The Abbots Vale reference uses the Hopkins Homes brand: a navy header with a gold or amber accent. That is a theme, not a default.
- Never hard-code a client brand into render logic. The same render takes any theme config.

## Output conventions in generated documents

Consistent with house-standards.md:
- Tenorite for documents, Tenor Sans for HTML.
- LandLynk green #2F6B3A for document headings where the client brand does not override.
- No em dashes. No Oxford commas. No markdown headers in generated prose.

## Accessibility

- Priority colours must pass contrast against their background and not rely on colour alone. Pair colour with rank number and label.
- Map regions are keyboard reachable and the deep-dive drawer is focus-managed.
- Charts carry text labels and values, not colour-only encoding.
