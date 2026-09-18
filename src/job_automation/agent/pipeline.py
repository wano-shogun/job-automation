"""A resumable, bounded pipeline from job discovery to browser form filling."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable

from job_automation.apply.submitter import ApplicationSubmission, JobSubmitter
from job_automation.models import Job
from job_automation.profile.loader import ProfileLoader
from job_automation.scoring.ranker import JobRanker, RankedJob


class AgentMode(str, Enum):
    """Browser visibility mode for an application run."""

    VISIBLE = "visible"
    HEADLESS = "headless"


@dataclass
class AgentRunItem:
    """One job's discovery, ranking, and browser fill outcome."""

    job: Job
    score: int
    submission: ApplicationSubmission | None = None
    error: str | None = None


@dataclass
class AgentRun:
    """A bounded record of one execution of the application agent."""

    query: str
    location: str
    mode: AgentMode
    items: list[AgentRunItem] = field(default_factory=list)

    @property
    def ready_for_review(self) -> int:
        return sum(item.submission is not None and item.submission.status == "ready_for_review" for item in self.items)


class ApplicationAgent:
    """Coordinates discovery, matching, and fill-only browser sessions.

    The pipeline never submits an application. ``JobSubmitter`` has a separate
    explicit submission boundary, so this high-level run is safe to use for a
    short list of newly discovered jobs.
    """

    def __init__(
        self,
        profile_loader: ProfileLoader,
        discover: Callable[[str, str], Iterable[Job]],
        ranker: JobRanker | None = None,
    ) -> None:
        self.profile_loader = profile_loader
        self.discover = discover
        self.ranker = ranker or JobRanker()

    def prepare(
        self,
        query: str,
        location: str = "",
        *,
        max_jobs: int = 5,
        min_score: int = 6,
    ) -> list[RankedJob]:
        """Discover and rank a bounded job list using local heuristic scoring."""
        if max_jobs < 1:
            raise ValueError("max_jobs must be at least 1")
        jobs = list(self.discover(query, location))
        return self.ranker.rank_jobs(
            jobs,
            self.profile_loader.load_profile(),
            min_score=min_score,
            use_claude=False,
        )[:max_jobs]

    def run(
        self,
        query: str,
        submitter: JobSubmitter,
        location: str = "",
        *,
        mode: AgentMode = AgentMode.VISIBLE,
        max_jobs: int = 1,
        min_score: int = 6,
        resume_path: str | None = None,
        ranked_jobs: list[RankedJob] | None = None,
    ) -> AgentRun:
        """Search, rank, and fill each selected application without sending it."""
        run = AgentRun(query=query, location=location, mode=mode)
        selected = ranked_jobs if ranked_jobs is not None else self.prepare(query, location, max_jobs=max_jobs, min_score=min_score)
        for index, ranked in enumerate(selected[:max_jobs]):
            item = AgentRunItem(job=ranked.job, score=ranked.match_score)
            try:
                if index and hasattr(submitter.driver, "switch_to"):
                    submitter.driver.switch_to.new_window("tab")
                item.submission = submitter.submit_application(
                    ranked.job.url, resume_path, submit=False
                )
                item.submission.company = ranked.job.company
                item.submission.role = ranked.job.title
            except Exception as exc:
                item.error = str(exc)
            run.items.append(item)
        return run
