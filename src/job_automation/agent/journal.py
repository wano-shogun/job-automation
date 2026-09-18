"""Durable progress journal for the application preparation pipeline."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from job_automation.agent.contracts import AgentPlan, ApplicationStage


class AgentJournal:
    """Persist stage changes without storing personal form answers."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA busy_timeout = 5000")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_attempts (
                run_id TEXT NOT NULL,
                job_url TEXT NOT NULL,
                job_title TEXT NOT NULL,
                company TEXT NOT NULL,
                score INTEGER NOT NULL,
                stage TEXT NOT NULL,
                error TEXT,
                fields_filled INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (run_id, job_url)
            );
            CREATE TABLE IF NOT EXISTS agent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                job_url TEXT NOT NULL,
                stage TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            """
        )

    def create_plan(self, run_id: str, plan: AgentPlan) -> None:
        """Persist selected jobs before opening any application pages."""
        for planned in plan.jobs:
            self._write(
                run_id, planned.job.url, planned.job.title, planned.job.company,
                planned.score, ApplicationStage.RANKED, None, 0,
            )

    def record(self, run_id: str, item: object) -> None:
        """Commit a stage transition and a compact evidence summary."""
        submission = item.submission
        self._write(
            run_id, item.job.url, item.job.title, item.job.company,
            item.score, item.stage, item.error,
            len(submission.fields_filled) if submission else 0,
        )

    def latest(self, limit: int = 20) -> list[dict[str, object]]:
        """Return recent attempts for the status command."""
        rows = self.connection.execute(
            "SELECT run_id, job_title, company, stage, error, fields_filled, updated_at "
            "FROM agent_attempts ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        keys = ("run_id", "job_title", "company", "stage", "error", "fields_filled", "updated_at")
        return [dict(zip(keys, row)) for row in rows]

    def _write(
        self, run_id: str, url: str, title: str, company: str, score: int,
        stage: ApplicationStage, error: str | None, fields_filled: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection:
            existing = self.connection.execute(
                "SELECT stage, error, fields_filled FROM agent_attempts WHERE run_id=? AND job_url=?",
                (run_id, url),
            ).fetchone()
            if existing == (stage.value, error, fields_filled):
                return
            if existing and stage == ApplicationStage.RANKED:
                return
            self.connection.execute(
                "INSERT INTO agent_attempts "
                "(run_id, job_url, job_title, company, score, stage, error, fields_filled, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(run_id, job_url) DO UPDATE SET "
                "stage=excluded.stage, error=excluded.error, "
                "fields_filled=excluded.fields_filled, updated_at=excluded.updated_at",
                (run_id, url, title, company, score, stage.value, error, fields_filled, now),
            )
            self.connection.execute(
                "INSERT INTO agent_events (run_id, job_url, stage, occurred_at) VALUES (?, ?, ?, ?)",
                (run_id, url, stage.value, now),
            )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> AgentJournal:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
