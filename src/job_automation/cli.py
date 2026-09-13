"""Command-line interface for job_automation.

Run `job-automation --help` (after an editable install) or
`python -m job_automation.cli --help` to see all commands.
"""

from __future__ import annotations

import click

from job_automation.db import DEFAULT_DB_PATH, JobRepository
from job_automation.models import Application, ApplicationStatus


@click.group()
@click.option(
    "--db-path",
    default=str(DEFAULT_DB_PATH),
    show_default=True,
    help="Path to the SQLite database file.",
)
@click.pass_context
def main(ctx: click.Context, db_path: str) -> None:
    """Track job applications from the command line."""
    ctx.obj = {"db_path": db_path}


@main.command()
@click.argument("company")
@click.argument("role")
@click.option("--url", default=None, help="Link to the job posting.")
@click.option("--notes", default=None, help="Free-form notes about the application.")
@click.pass_context
def add(ctx: click.Context, company: str, role: str, url: str | None, notes: str | None) -> None:
    """Record a new application to COMPANY for ROLE."""
    with JobRepository(ctx.obj["db_path"]) as repo:
        saved = repo.add(Application(company=company, role=role, url=url, notes=notes))
    click.echo(f"Added application #{saved.id}: {saved.company} - {saved.role}")


@main.command(name="list")
@click.option(
    "--status",
    type=click.Choice([s.value for s in ApplicationStatus]),
    default=None,
    help="Filter by status.",
)
@click.pass_context
def list_applications(ctx: click.Context, status: str | None) -> None:
    """List tracked applications, most recent first."""
    with JobRepository(ctx.obj["db_path"]) as repo:
        apps = repo.list(ApplicationStatus(status) if status else None)
    if not apps:
        click.echo("No applications tracked yet.")
        return
    for app in apps:
        click.echo(
            f"#{app.id} [{app.status.value}] {app.company} - {app.role} "
            f"(applied {app.date_applied.isoformat()})"
        )


@main.command(name="update-status")
@click.argument("application_id", type=int)
@click.argument("status", type=click.Choice([s.value for s in ApplicationStatus]))
@click.pass_context
def update_status(ctx: click.Context, application_id: int, status: str) -> None:
    """Change the status of application APPLICATION_ID to STATUS."""
    with JobRepository(ctx.obj["db_path"]) as repo:
        updated = repo.update_status(application_id, ApplicationStatus(status))
    if updated is None:
        raise click.ClickException(f"No application with id {application_id}")
    click.echo(f"Application #{updated.id} is now {updated.status.value}")


if __name__ == "__main__":
    main()
