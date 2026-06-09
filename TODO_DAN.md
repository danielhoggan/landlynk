# Dan to-do list

The actions only you can do, so we are ready to go live. Detail for each is in
DEPLOYMENT.md. Rough order below.

## Accounts and keys

- [x] Create an OpenRouteService account and generate an API key (free tier).
      https://openrouteservice.org/dev/#/signup
      This value goes into the worker variable `WORKER_ISOCHRONE_API_KEY`.
- [x] Decide the public web hostname (Railway domain or custom domain). This
      value goes into the web variable `NEXTAUTH_URL` (no trailing slash) and is
      also the host in the Azure redirect URI.
- [x] Generate a NextAuth secret by running `openssl rand -base64 32`. Put the
      output into the web variable `NEXTAUTH_SECRET`.

## Azure App Registration (SSO)

- [x] Register an app in Entra ID (Azure AD) in the Mediaworks tenant.
- [x] Under Authentication, add a platform of type **Web** and add this exact
      Redirect URI (replace the host with your real web URL, keep the path):

      https://YOUR-WEB-URL/api/auth/callback/azure-ad

      Example for a Railway domain:
      `https://landlynk-web.up.railway.app/api/auth/callback/azure-ad`
- [x] Under Certificates and secrets, create a **client secret** and copy its
      **Value** (not the Secret ID). You set this as `AZURE_AD_CLIENT_SECRET`.
- [x] From the app Overview, copy these three values for the web env vars below:
  - Application (client) ID  ->  `AZURE_AD_CLIENT_ID`
  - Directory (tenant) ID    ->  `AZURE_AD_TENANT_ID`
  - the client secret Value  ->  `AZURE_AD_CLIENT_SECRET`
- [x] Under API permissions, confirm delegated `User.Read` is granted (default).

## Railway project

- [x] Create the Railway project.
- [x] Add a Postgres plugin and confirm PostGIS can be enabled. Note its
      connection string (Railway exposes it as `DATABASE_URL` on the plugin).
- [x] Create the `web` service from the repo.
- [x] Create the `worker` service from the repo.
- [x] IMPORTANT set each service's Root Directory (Service -> Settings ->
      Source -> Root Directory). Without this the build fails with
      "Railpack could not determine how to build the app":
  - `web` service Root Directory = `web`
  - `worker` service Root Directory = `worker`

  With the Root Directory set, Railway picks up `web/railway.json` and
  `worker/railway.json`, which select the Dockerfile build. You should not need
  to choose a builder manually; if a service still shows the Railpack builder,
  set Builder to Dockerfile in Settings.

### Worker service variables (set these exact names on the `worker` service)

- [x] `WORKER_DATABASE_URL` = the Postgres connection string (same value as the
      plugin's `DATABASE_URL`). Required.
- [x] `WORKER_ISOCHRONE_API_KEY` = your OpenRouteService API key. Required.
- [x] `WORKER_ISOCHRONE_PROVIDER` = `openrouteservice`. Optional, this is the
      default; only set it to change provider.
- [x] `WORKER_ISOCHRONE_BASE_URL` = `https://api.openrouteservice.org`. Optional,
      this is the default; set it only to point at a self-hosted ORS or Valhalla.
- [x] `WORKER_PERSIST_RESULTS` = `true`. Optional, default is true.
- [x] `WORKER_DEFAULT_DRIVE_TIME_MINUTES` = `30`. Optional, default is 30.
- [x] AI Local Area Profile keys (optional, enables the amenities lookup). Add
      any you use; the AI models admin page only offers providers with a key set.
      Either the WORKER_ prefixed name or the provider's conventional name works:
  - Anthropic: `WORKER_ANTHROPIC_API_KEY` or `ANTHROPIC_API_KEY`.
  - OpenAI: `WORKER_OPENAI_API_KEY` or `OPENAI_API_KEY`.
  - Google (Gemini): `WORKER_GOOGLE_API_KEY`, `GOOGLE_API_KEY` or `GEMINI_API_KEY`.
      Set these on the worker service, then redeploy/restart it so the new values
      load. Then pick the default model on the in-app AI models page (admin only).
- [ ] `WORKER_GITHUB_TOKEN` (optional, enables brand logo upload). A fine-grained
      GitHub PAT with contents:write on this repo. Logos uploaded on the Builders
      page are committed to brand-assets/ and read back for the UI and exports.
      Optional `WORKER_GITHUB_REPO` (default `danielhoggan/landlynk`) and
      `WORKER_GITHUB_BRANCH` (default `main`) override the target.
- [x] `WORKER_ADMIN_EMAILS` = comma-separated emails always granted the admin
      role on sign in, e.g. `danielhoggan@gmail.com`. Bootstraps the first
      admin, who can then set other users' roles from the Users page. Required
      to have at least one admin (only admins can delete runs and manage roles).

### Web service variables (set these exact names on the `web` service)

- [x] `NEXTAUTH_URL` = your public web URL, e.g. `https://landlynk-web.up.railway.app`.
      No trailing slash. Required.
- [x] `NEXTAUTH_SECRET` = the output of `openssl rand -base64 32`. Required.
- [x] `AZURE_AD_CLIENT_ID` = Application (client) ID from the App Registration.
      Required.
- [x] `AZURE_AD_CLIENT_SECRET` = the client secret Value. Required.
- [x] `AZURE_AD_TENANT_ID` = Directory (tenant) ID. Required.
- [x] `WORKER_BASE_URL` = the worker service URL Railway gives the `worker`
      service (the internal/private URL is fine), e.g.
      `http://worker.railway.internal:8000` or the public worker URL. Required.

  Note: the web service does NOT need `DATABASE_URL`; only the worker talks to
  the database.

## Database and reference data

- [x] Use a PostGIS database, NOT Railway's plain Postgres plugin (it lacks the
      PostGIS extension). A Railway PostGIS template or the `postgis/postgis`
      image both work. Point `WORKER_DATABASE_URL` at it.
- [x] Migrations run automatically on each worker deploy (worker pre-deploy
      command `python -m landlynk_worker.migrate`). No manual step. Just confirm
      the worker's latest deploy log shows "Applied N migration(s)" or
      "Database is up to date".
- [x] Load reference data IN THE APP (no local commands): open the "Reference
      data" page in the nav and press Load on each dataset. The worker downloads
      and loads it.
  - [x] MSOA boundaries (essential, gets areas showing). The ArcGIS URL is
        pre-filled; replace only if a newer ONS vintage exists.
  - [x] Census demographics: paste the NOMIS bulk CSV URLs for age (TS007) and
        household composition (TS003).
  - [x] Census tenure: paste the NOMIS bulk CSV URL (TS054).
  - [x] Income estimates: paste the ONS small-area income XLSX URL.
  - Lookup and OS CodePoint Open are NOT needed (geocoding uses postcodes.io).
- [x] Optional: set `WORKER_ADMIN_TOKEN` (same value) on the web and worker
      services to lock the load endpoints down. Not required while the worker is
      private.
- [x] Confirm the GWI persona licence terms before we wire persona-driven channel
      guidance into client outputs (SCOPING.md section 11). Tell me the outcome.

## Decisions I need from you

- [x] A default development brief for the first real run: town, strapline,
      lifestyle pillars, feature bullets, price band and bed range (so the
      Battlecard header and scoring reflect the real scheme, not defaults). I am
      building the form to capture these; your example content lets me validate.
- [x] Confirm MSOA-only for MVP is fine, or whether you want LA-level now.
- [x] Confirm the income-to-price affordability multiple used in the new pricing
      rationale (default 4.5x gross household income). Tell me if you price off a
      different multiple or net income and I will adjust.
- [x] Fonts: standardised on Poppins for all exports (Tenorite dropped).

## Go-live check

- [x] Run the smoke test in DEPLOYMENT.md section 6 with a real Suffolk postcode.
- [x] Tell me the result so I can fix anything that surfaces against real data.
