# Dan to-do list

The actions only you can do, so we are ready to go live. Detail for each is in
DEPLOYMENT.md. Rough order below.

## Accounts and keys

- [ ] Create an OpenRouteService account and generate an API key (free tier).
      https://openrouteservice.org/dev/#/signup
- [ ] Decide the public web hostname (Railway domain or custom domain). You need
      it for `NEXTAUTH_URL` and the Azure redirect URI.
- [ ] Generate a NextAuth secret: `openssl rand -base64 32`.

## Azure App Registration (SSO)

- [ ] Register an app in Entra ID (Azure AD) in the Mediaworks tenant.
- [ ] Add the Web redirect URI: `${NEXTAUTH_URL}/api/auth/callback/azure-ad`.
- [ ] Create a client secret.
- [ ] Note the client id, client secret and tenant id for the web env vars.
- [ ] Confirm delegated `User.Read` is granted (usually default).

## Railway project

- [ ] Create the Railway project.
- [ ] Add a Postgres plugin and confirm PostGIS can be enabled.
- [ ] Create the `web` service from the repo, root directory `web`, Dockerfile
      build.
- [ ] Create the `worker` service from the repo, root directory `worker`,
      Dockerfile build.
- [ ] Set the worker environment variables (see DEPLOYMENT.md section 3).
- [ ] Set the web environment variables (see DEPLOYMENT.md section 4).
- [ ] Point `WORKER_BASE_URL` (web) at the worker service URL.

## Database and reference data

- [ ] Run migrations: `DATABASE_URL=... python infra/migrate.py`.
- [ ] Download the open reference datasets (links and licences in
      `data/sources.yaml`):
  - [ ] ONS MSOA 2021 boundaries (GeoJSON), Open Geography Portal.
  - [ ] ONS OA to MSOA to LAD lookup (CSV).
  - [ ] ONS Census 2021 age by single year (CSV, NOMIS TS007-style).
  - [ ] ONS Census 2021 household composition (CSV, TS003-style).
  - [ ] ONS Census 2021 tenure (CSV, TS054-style).
  - [ ] ONS MSOA income estimates (XLSX).
  - [ ] OS CodePoint Open (CSV).
- [ ] Load each with the loaders (DEPLOYMENT.md section 2). Pin the concrete
      version in `data/sources.yaml` as you go.
- [ ] Confirm the GWI persona licence terms before we wire persona-driven channel
      guidance into client outputs (SCOPING.md section 11). Tell me the outcome.

## Decisions I need from you

- [ ] A default development brief for the first real run: town, strapline,
      lifestyle pillars, feature bullets, price band and bed range (so the
      Battlecard header and scoring reflect the real scheme, not defaults). I am
      building the form to capture these; your example content lets me validate.
- [ ] Confirm MSOA-only for MVP is fine, or whether you want LA-level now.
- [ ] Confirm the income-to-price affordability multiple used in the new pricing
      rationale (default 4.5x gross household income). Tell me if you price off a
      different multiple or net income and I will adjust.
- [ ] If you have the Tenorite font file, share it so I can embed it in the PDF
      and PPTX exports (currently a Helvetica fallback).

## Go-live check

- [ ] Run the smoke test in DEPLOYMENT.md section 6 with a real Suffolk postcode.
- [ ] Tell me the result so I can fix anything that surfaces against real data.
