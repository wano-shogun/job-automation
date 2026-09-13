"""Data model for a tracked job application."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    """Lifecycle states a tracked application moves through."""

    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(BaseModel):
    """A single job application tracked by job_automation."""

    id: int | None = None
    company: str
    role: str
    status: ApplicationStatus = ApplicationStatus.APPLIED
    date_applied: date = Field(default_factory=date.today)
    url: str | None = None
    notes: str | None = None
