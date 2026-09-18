"""A bounded pipeline from job discovery to browser form filling."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable
from urllib.parse import urlsplit
from uuid import uuid4

from job_automation.apply.submitter import ApplicationSubmission, JobSubmitter
from job_automation.agent.contracts import AgentPlan, ApplicationStage, PlannedJob, StageHistory
from job_automation.agent.journal import AgentJournal
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
    history: StageHistory = field(default_factory=StageHistory)

    @property
    def stage(self) -> ApplicationStage:
        return self.history.current


@dataclass
class AgentRun:
    """A bounded record of one execution of the application agent."""

    query: str
    location: str
    mode: AgentMode
    run_id: str = field(default_factory=lambda: uuid4().hex)
    items: list[AgentRunItem] = field(default_factory=list)

    @property
    def ready_for_review(self) -> int:
        return sum(item.stage == ApplicationStage.READY_FOR_REVIEW for item in self.items)


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
        seen: set[str] = set()
        jobs: list[Job] = []
        for job in self.discover(query, location):
            parsed = urlsplit(job.url)
            key = f"{parsed.netloc.casefold()}{parsed.path.rstrip('/').casefold()}"
            if key not in seen:
                seen.add(key)
                jobs.append(job)
        return self.ranker.rank_jobs(
            jobs,
            self.profile_loader.load_profile(),
            min_score=min_score,
            use_claude=False,
        )[:max_jobs]

    def plan(
        self,
        query: str,
        location: str = "",
        *,
        max_jobs: int = 5,
        min_score: int = 6,
    ) -> AgentPlan:
        """Return a bounded, deduplicated plan before opening a browser."""
        ranked = self.prepare(query, location, max_jobs=max_jobs, min_score=min_score)
        return AgentPlan(
            query=query,
            location=location,
            jobs=tuple(PlannedJob(item.job, item.match_score, item.reasoning) for item in ranked),
        )

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
        plan: AgentPlan | None = None,
        journal: AgentJournal | None = None,
        run_id: str | None = None,
    ) -> AgentRun:
        """Search, rank, and fill each selected application without sending it."""
        run = AgentRun(query=query, location=location, mode=mode, run_id=run_id or uuid4().hex)
        selected = plan or self.plan(query, location, max_jobs=max_jobs, min_score=min_score)
        if journal:
            journal.create_plan(run.run_id, selected)
        for index, planned in enumerate(selected.jobs[:max_jobs]):
            item = AgentRunItem(job=planned.job, score=planned.score)
            try:
                item.history.advance(ApplicationStage.FILLING)
                if journal:
                    journal.record(run.run_id, item)
                if index and hasattr(submitter.driver, "switch_to"):
                    submitter.driver.switch_to.new_window("tab")
                item.submission = submitter.submit_application(
                    planned.job.url, resume_path, submit=False
                )
                item.submission.company = planned.job.company
                item.submission.role = planned.job.title
                if item.submission.status == "ready_for_review":
                    item.history.advance(ApplicationStage.READY_FOR_REVIEW)
                else:
                    item.history.advance(ApplicationStage.NEEDS_REVIEW)
            except Exception as exc:
                item.error = str(exc)
                item.history.advance(ApplicationStage.FAILED)
            if journal:
                journal.record(run.run_id, item)
            run.items.append(item)
        return run
