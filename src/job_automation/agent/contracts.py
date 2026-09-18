"""Explicit handoffs and states for one job application attempt."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from job_automation.models import Job


class ApplicationStage(str, Enum):
    """Stages that can be recorded before a final application submission."""

    RANKED = "ranked"
    FILLING = "filling"
    READY_FOR_REVIEW = "ready_for_review"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


@dataclass(frozen=True)
class PlannedJob:
    """A ranked job selected for browser work."""

    job: Job
    score: int
    reasoning: str


@dataclass(frozen=True)
class AgentPlan:
    """Immutable output of discovery and ranking."""

    query: str
    location: str
    jobs: tuple[PlannedJob, ...]


@dataclass
class StageHistory:
    """Tracks ordered transitions for one application attempt."""

    current: ApplicationStage = ApplicationStage.RANKED
    events: list[ApplicationStage] = field(default_factory=lambda: [ApplicationStage.RANKED])

    def advance(self, next_stage: ApplicationStage) -> None:
        allowed = {
            ApplicationStage.RANKED: {ApplicationStage.FILLING, ApplicationStage.FAILED},
            ApplicationStage.FILLING: {
                ApplicationStage.READY_FOR_REVIEW,
                ApplicationStage.NEEDS_REVIEW,
                ApplicationStage.FAILED,
            },
        }
        if next_stage not in allowed.get(self.current, set()):
            raise ValueError(f"Invalid application transition: {self.current.value} -> {next_stage.value}")
        self.current = next_stage
        self.events.append(next_stage)
