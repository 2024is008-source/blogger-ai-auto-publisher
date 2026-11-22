"""Abstract base class for modular image discovery providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.models.schemas import ImageAsset


class ImageProvider(ABC):
    """Contract for pluggable copyright-aware image search providers."""

    provider_name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if this provider is enabled and has required credentials."""

    @abstractmethod
    def search(self, query: str, *, limit: int = 8) -> list[ImageAsset]:
        """Search provider and return normalized ImageAsset candidates with raw license metadata."""
