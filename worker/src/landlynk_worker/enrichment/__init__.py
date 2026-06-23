"""AI enrichment: Local Area Profiles and Marketing Activation playbooks from a
choice of LLM providers."""

from .area_profile import generate_area_profile
from .marketing import build_facts, generate_marketing_activation
from .models import (
    MODELS,
    available_models,
    model_cost,
    model_provider,
    token_cost,
)

__all__ = [
    "MODELS",
    "available_models",
    "model_provider",
    "model_cost",
    "token_cost",
    "generate_area_profile",
    "build_facts",
    "generate_marketing_activation",
]
