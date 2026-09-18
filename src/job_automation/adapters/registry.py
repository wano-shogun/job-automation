"""Adapter selection for application URLs."""

from __future__ import annotations

from job_automation.adapters.ashby import AshbyAdapter
from job_automation.adapters.base import ApplicationAdapter


_ADAPTERS: tuple[ApplicationAdapter, ...] = (AshbyAdapter(),)


def get_adapter(url: str) -> ApplicationAdapter | None:
    """Return the specialised adapter for a URL, if one is installed."""
    return next((adapter for adapter in _ADAPTERS if adapter.matches(url)), None)
