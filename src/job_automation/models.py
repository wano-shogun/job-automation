"""Data models for tracked job applications and discovered jobs."""

from __future__ import annotations

from datetime import date, datetime
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


class Job(BaseModel):
    """A job listing discovered from a job board."""

    id: int | None = None
    source: str  # "indeed", "linkedin", "glassdoor", "ziprecruiter", "google_jobs"
    job_id: str  # Unique ID from the source
    title: str
    company: str
    location: str
    salary: str | None = None
    description: str | None = None
    url: str
    posted_date: str | None = None  # ISO format
    discovered_date: datetime = Field(default_factory=datetime.now)
    scraped_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic config."""

        json_encoders = {datetime: lambda v: v.isoformat()}
