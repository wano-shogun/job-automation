"""SQLite-backed storage for tracked job applications and discovered jobs.

All persistence goes through repositories so the CLI (and any future
interface, such as the planned autofill module) never touches SQL directly.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from job_automation.models import Application, ApplicationStatus, Job

DEFAULT_DB_PATH = Path.home() / ".job-automation" / "applications.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    date_applied TEXT NOT NULL,
    url TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    job_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    salary TEXT,
    description TEXT,
    url TEXT NOT NULL,
    posted_date TEXT,
    discovered_date TEXT NOT NULL,
    scraped_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scraper_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL UNIQUE,
    last_run TEXT,
    last_success TEXT,
    error_count INTEGER DEFAULT 0,
    error_message TEXT
);
"""


class JobRepository:
    """CRUD access to the applications table in a SQLite database."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> JobRepository:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def add(self, application: Application) -> Application:
        cursor = self._conn.execute(
            "INSERT INTO applications (company, role, status, date_applied, url, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                application.company,
                application.role,
                application.status.value,
                application.date_applied.isoformat(),
                application.url,
                application.notes,
            ),
        )
        self._conn.commit()
        return application.model_copy(update={"id": cursor.lastrowid})

    def get(self, application_id: int) -> Application | None:
        row = self._conn.execute(
            "SELECT * FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        return _row_to_application(row) if row else None

    def list(self, status: ApplicationStatus | None = None) -> list[Application]:
        if status is None:
            rows = self._conn.execute(
                "SELECT * FROM applications ORDER BY date_applied DESC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY date_applied DESC",
                (status.value,),
            ).fetchall()
        return [_row_to_application(row) for row in rows]

    def update_status(self, application_id: int, status: ApplicationStatus) -> Application | None:
        self._conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status.value, application_id),
        )
        self._conn.commit()
        return self.get(application_id)

    def delete(self, application_id: int) -> None:
        self._conn.execute("DELETE FROM applications WHERE id = ?", (application_id,))
        self._conn.commit()


def _row_to_application(row: sqlite3.Row) -> Application:
    return Application(
        id=row["id"],
        company=row["company"],
        role=row["role"],
        status=ApplicationStatus(row["status"]),
        date_applied=date.fromisoformat(row["date_applied"]),
        url=row["url"],
        notes=row["notes"],
    )


class JobDiscoveryRepository:
    """CRUD access to the jobs and scraper_status tables in a SQLite database."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> JobDiscoveryRepository:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # Job CRUD operations
    def add_job(self, job: Job) -> Job:
        """Add a job to the database. Updates if job_id already exists."""
        cursor = self._conn.execute(
            """INSERT OR REPLACE INTO jobs
               (source, job_id, title, company, location, salary, description, url, posted_date, discovered_date, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job.source,
                job.job_id,
                job.title,
                job.company,
                job.location,
                job.salary,
                job.description,
                job.url,
                job.posted_date,
                job.discovered_date.isoformat(),
                job.scraped_at.isoformat(),
            ),
        )
        self._conn.commit()
        # Fetch the inserted/updated record to get the ID
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job.job_id,)
        ).fetchone()
        return _row_to_job(row) if row else job

    def add_jobs(self, jobs: list[Job]) -> list[Job]:
        """Add multiple jobs to the database."""
        return [self.add_job(job) for job in jobs]

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by its source job_id."""
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return _row_to_job(row) if row else None

    def list_jobs(
        self,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Job]:
        """List jobs with optional filtering."""
        if source:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE source = ? ORDER BY discovered_date DESC LIMIT ? OFFSET ?",
                (source, limit, offset),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM jobs ORDER BY discovered_date DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [_row_to_job(row) for row in rows]

    def search_jobs(self, query: str, limit: int = 50) -> list[Job]:
        """Search jobs by title, company, or location."""
        search_term = f"%{query}%"
        rows = self._conn.execute(
            """SELECT * FROM jobs
               WHERE title LIKE ? OR company LIKE ? OR location LIKE ?
               ORDER BY discovered_date DESC LIMIT ?""",
            (search_term, search_term, search_term, limit),
        ).fetchall()
        return [_row_to_job(row) for row in rows]

    def get_job_count(self, source: str | None = None) -> int:
        """Get total count of jobs."""
        if source:
            row = self._conn.execute(
                "SELECT COUNT(*) as count FROM jobs WHERE source = ?", (source,)
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) as count FROM jobs").fetchone()
        return row["count"] if row else 0

    def delete_job(self, job_id: str) -> None:
        """Delete a job by its source job_id."""
        self._conn.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))
        self._conn.commit()

    def delete_jobs_before(self, days: int) -> int:
        """Delete jobs older than N days."""
        cursor = self._conn.execute(
            """DELETE FROM jobs
               WHERE datetime(discovered_date) < datetime('now', ? || ' days')""",
            (f"-{days}",),
        )
        self._conn.commit()
        return cursor.rowcount

    # Scraper status operations
    def update_scraper_status(
        self, source: str, success: bool = True, error_message: str | None = None
    ) -> None:
        """Update scraper status for a source."""
        now = datetime.now().isoformat()
        if success:
            self._conn.execute(
                """INSERT OR REPLACE INTO scraper_status (source, last_run, last_success, error_count, error_message)
                   VALUES (?, ?, ?, 0, NULL)""",
                (source, now, now),
            )
        else:
            self._conn.execute(
                """INSERT INTO scraper_status (source, last_run, error_count, error_message)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT(source) DO UPDATE SET last_run = ?, error_count = error_count + 1, error_message = ?""",
                (source, now, error_message, now, error_message),
            )
        self._conn.commit()

    def get_scraper_status(self, source: str) -> dict | None:
        """Get status for a scraper."""
        row = self._conn.execute(
            "SELECT * FROM scraper_status WHERE source = ?", (source,)
        ).fetchone()
        if not row:
            return None
        return {
            "source": row["source"],
            "last_run": row["last_run"],
            "last_success": row["last_success"],
            "error_count": row["error_count"],
            "error_message": row["error_message"],
        }


def _row_to_job(row: sqlite3.Row) -> Job:
    return Job(
        id=row["id"],
        source=row["source"],
        job_id=row["job_id"],
        title=row["title"],
        company=row["company"],
        location=row["location"],
        salary=row["salary"],
        description=row["description"],
        url=row["url"],
        posted_date=row["posted_date"],
        discovered_date=datetime.fromisoformat(row["discovered_date"]),
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )
