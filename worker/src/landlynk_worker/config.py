"""Worker settings. Secrets via Railway environment variables, never in the repo."""

from __future__ import annotations

from pydantic import AliasChoices, Field
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
    # present. An admin picks the default model from those. Each accepts either
    # the WORKER_ prefixed name or the provider's conventional name (e.g.
    # OPENAI_API_KEY), so the keys most SDKs expect work without renaming.
    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("WORKER_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    )
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("WORKER_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    google_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "WORKER_GOOGLE_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"
        ),
    )

    # Brand logo storage in GitHub. A fine-grained PAT with contents:write on the
    # repo, the repo in owner/name form, and the branch to commit logos to.
    github_token: str = Field(
        default="", validation_alias=AliasChoices("WORKER_GITHUB_TOKEN", "GITHUB_TOKEN")
    )
    github_repo: str = "danielhoggan/landlynk"
    github_branch: str = "main"

    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


settings = Settings()
