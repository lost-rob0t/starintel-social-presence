"""Deterministic StarIntel Git change ingestion."""

from .git import GitChangeSource
from .models import NormalizedChange

__all__ = ["GitChangeSource", "NormalizedChange"]
