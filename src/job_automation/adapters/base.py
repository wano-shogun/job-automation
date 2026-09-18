"""Contract used by site-specific application form adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ApplicationAdapter(ABC):
    """Provide form knowledge for one applicant tracking system.

    An adapter only identifies fields and prepares values. It never clicks a
    final submit button; that decision remains in :class:`JobSubmitter`.
    """

    name = "generic"

    @abstractmethod
    def matches(self, url: str) -> bool:
        """Return whether this adapter owns ``url``."""

    def identity(self, driver: Any, control: Any, fallback: str) -> str:
        """Return a human-readable identity for a browser control."""
        return fallback

    def prepare_values(self, values: dict[str, str]) -> dict[str, str]:
        """Add safe site-specific aliases to normalized profile values."""
        return values
