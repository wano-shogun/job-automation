"""Command-line interface for job_automation.

Run `job-automation --help` (after an editable install) or
`python -m job_automation.cli --help` to see all commands.
"""

from __future__ import annotations

import click

from job_automation.autofill.engine import AutofillEngine
from job_automation.browser.driver import BrowserDriver
from job_automation.db import DEFAULT_DB_PATH, JobRepository
from job_automation.models import Application, ApplicationStatus
from job_automation.profile.loader import ProfileLoader


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


@main.group(name="autofill")
@click.pass_context
def autofill_group(ctx: click.Context) -> None:
    """Autofill job application forms across job boards."""
    pass


@autofill_group.command(name="run")
@click.argument("url")
@click.option("--auto-fill", is_flag=True, help="Auto-fill without asking for confirmation.")
@click.pass_context
def autofill_run(ctx: click.Context, url: str, auto_fill: bool) -> None:
    """Autofill a job application form.

    Opens the URL in Chrome, analyzes the form, shows a fill plan,
    and fills it with your profile data. You review before final submission.

    Example:
        job-automation autofill run "https://www.example.com/careers/job/123"
    """
    try:
        # Validate profile and answers exist
        profile_loader = ProfileLoader()
        if not profile_loader.validate_profile():
            raise click.ClickException("Profile not found at ~/.job-automation/profile.json")
        if not profile_loader.validate_answers():
            raise click.ClickException("Answers not found at ~/.job-automation/answers.json")

        click.echo("🚀 Starting autofill workflow...")
        click.echo(f"📍 URL: {url}")

        # Open browser and navigate
        driver = BrowserDriver()
        driver.start()

        try:
            click.echo("🌐 Opening page...")
            driver.navigate_to(url)

            # Create autofill engine
            engine = AutofillEngine(profile_loader, driver.get_driver())

            # Analyze the form
            click.echo("📋 Analyzing form...")
            plan = engine.create_autofill_plan()

            # Print the plan
            engine.print_plan(plan)

            # Ask for confirmation (unless --auto-fill)
            should_fill = auto_fill or click.confirm("✓ Fill the form?")

            if should_fill:
                click.echo("🚀 Filling form...")
                engine.fill_form(plan)
                click.echo("\n" + "=" * 60)
                click.echo("✅ FORM FILLED - REVIEW AND SUBMIT MANUALLY")
                click.echo("=" * 60)
                click.echo("The form has been filled with your profile data.")
                click.echo("Please review all fields and click Submit when ready.")
                click.echo("The browser will remain open for you to interact with.")
                click.echo("Press Ctrl+C here to close the browser when done.")
                click.echo("=" * 60 + "\n")

                # Keep browser open
                import time

                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    click.echo("\nClosing browser...")
            else:
                click.echo("❌ Cancelled. Form not filled.")

        finally:
            driver.stop()

    except FileNotFoundError as e:
        raise click.ClickException(f"Configuration error: {e}")
    except ValueError as e:
        raise click.ClickException(f"Form error: {e}")
    except Exception as e:
        raise click.ClickException(f"Autofill error: {e}")


if __name__ == "__main__":
    main()
