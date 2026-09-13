"""SQLite-backed storage for tracked job applications.

All persistence goes through JobRepository so the CLI (and any future
interface, such as the planned autofill module) never touches SQL directly.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from job_automation.models import Application, ApplicationStatus

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
