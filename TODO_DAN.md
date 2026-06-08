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
- [ ] Under Authentication, add a platform of type **Web** and add this exact
      Redirect URI (replace the host with your real web URL, keep the path):

      https://YOUR-WEB-URL/api/auth/callback/azure-ad

      Example for a Railway domain:
      `https://landlynk-web.up.railway.app/api/auth/callback/azure-ad`
- [ ] Under Certificates and secrets, create a **client secret** and copy its
      **Value** (not the Secret ID). You set this as `AZURE_AD_CLIENT_SECRET`.
- [ ] From the app Overview, copy these three values for the web env vars below:
  - Application (client) ID  ->  `AZURE_AD_CLIENT_ID`
  - Directory (tenant) ID    ->  `AZURE_AD_TENANT_ID`
  - the client secret Value  ->  `AZURE_AD_CLIENT_SECRET`
- [ ] Under API permissions, confirm delegated `User.Read` is granted (default).

## Railway project

- [ ] Create the Railway project.
- [ ] Add a Postgres plugin and confirm PostGIS can be enabled. Note its
      connection string (Railway exposes it as `DATABASE_URL` on the plugin).
- [ ] Create the `web` service from the repo, root directory `web`, Dockerfile
      build.
- [ ] Create the `worker` service from the repo, root directory `worker`,
      Dockerfile build.

### Worker service variables (set these exact names on the `worker` service)

- [ ] `WORKER_DATABASE_URL` = the Postgres connection string (same value as the
      plugin's `DATABASE_URL`). Required.
- [ ] `WORKER_ISOCHRONE_API_KEY` = your OpenRouteService API key. Required.
- [ ] `WORKER_ISOCHRONE_PROVIDER` = `openrouteservice`. Optional, this is the
      default; only set it to change provider.
- [ ] `WORKER_ISOCHRONE_BASE_URL` = `https://api.openrouteservice.org`. Optional,
      this is the default; set it only to point at a self-hosted ORS or Valhalla.
- [ ] `WORKER_PERSIST_RESULTS` = `true`. Optional, default is true.
- [ ] `WORKER_DEFAULT_DRIVE_TIME_MINUTES` = `30`. Optional, default is 30.

### Web service variables (set these exact names on the `web` service)

- [ ] `NEXTAUTH_URL` = your public web URL, e.g. `https://landlynk-web.up.railway.app`.
      No trailing slash. Required.
- [ ] `NEXTAUTH_SECRET` = the output of `openssl rand -base64 32`. Required.
- [ ] `AZURE_AD_CLIENT_ID` = Application (client) ID from the App Registration.
      Required.
- [ ] `AZURE_AD_CLIENT_SECRET` = the client secret Value. Required.
- [ ] `AZURE_AD_TENANT_ID` = Directory (tenant) ID. Required.
- [ ] `WORKER_BASE_URL` = the worker service URL Railway gives the `worker`
      service (the internal/private URL is fine), e.g.
      `http://worker.railway.internal:8000` or the public worker URL. Required.

  Note: the web service does NOT need `DATABASE_URL`; only the worker talks to
  the database.

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
