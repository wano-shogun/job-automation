"""Site-specific application form adapters.

Adapters improve recognition for an ATS while the generic browser filler remains
available for every other site.
"""

from job_automation.adapters.base import ApplicationAdapter
from job_automation.adapters.registry import get_adapter

__all__ = ["ApplicationAdapter", "get_adapter"]
