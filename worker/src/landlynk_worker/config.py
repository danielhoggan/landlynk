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

    # Default drive-time for the catchment.
    default_drive_time_minutes: int = 30


settings = Settings()
