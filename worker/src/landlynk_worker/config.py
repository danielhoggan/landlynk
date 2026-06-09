"""Worker settings. Secrets via Railway environment variables, never in the repo."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", extra="ignore")

    # Postgres with PostGIS.
    database_url: str = "postgresql://postgres:postgres@localhost:5432/landlynk"

    # Isochrone provider. OpenRouteService or TravelTime. Key from the env.
    isochrone_provider: str = "openrouteservice"
    isochrone_api_key: str = ""
    # Base URL, override to point at a self-hosted ORS or Valhalla.
    isochrone_base_url: str = "https://api.openrouteservice.org"

    # Default drive-time for the catchment.
    default_drive_time_minutes: int = 30

    # Persist results to Postgres. When false, the worker uses an in-memory
    # store (single process only). Production keeps this true.
    persist_results: bool = True

    # Optional shared secret for the admin reference-load endpoints. When set,
    # callers must send it as X-Admin-Token. The worker is private (internal
    # networking) and the web caller is SSO-gated, so this is defence in depth.
    admin_token: str = ""

    # Comma-separated emails always granted the admin role on sign in. Bootstraps
    # the first admin, who can then promote others from the Users page.
    admin_emails: str = ""

    # AI provider keys for the Local Area Profile enrichment. Set the providers
    # you use in Railway; the available models in the app reflect which keys are
    # present. An admin picks the default model from those.
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


settings = Settings()
