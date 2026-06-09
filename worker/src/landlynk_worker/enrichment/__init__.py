"""AI enrichment: Local Area Profiles from a choice of LLM providers."""

from .area_profile import generate_area_profile
from .models import MODELS, available_models, model_provider

__all__ = [
    "MODELS",
    "available_models",
    "model_provider",
    "generate_area_profile",
]
