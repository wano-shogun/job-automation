"""Command-line interface for job_automation.

Run `job-automation --help` (after an editable install) or
`python -m job_automation.cli --help` to see all commands.
"""

from __future__ import annotations

import click

from job_automation.autofill.engine import AutofillEngine
from job_automation.browser.driver import BrowserDriver
from job_automation.db import DEFAULT_DB_PATH, JobRepository, JobDiscoveryRepository
from job_automation.models import Application, ApplicationStatus
from job_automation.profile.loader import ProfileLoader
from job_automation.discovery import (
    IndeedScraper,
    LinkedInScraper,
    GlassdoorScraper,
    ZipRecruiterScraper,
    GoogleJobsScraper,
)
from job_automation.scoring import JobRanker
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


@main.group(name="discover")
@click.pass_context
def discover_group(ctx: click.Context) -> None:
    """Discover job listings from various job boards."""
    pass


@discover_group.command(name="search")
@click.argument("query")
@click.option("--location", default="", help="Job location.")
@click.option("--source", type=click.Choice(["indeed", "linkedin", "glassdoor", "ziprecruiter", "google_jobs", "all"]), default="all", help="Job board to search.")
@click.option("--limit", type=int, default=10, help="Number of results to show.")
@click.pass_context
def discover_search(
    ctx: click.Context, query: str, location: str, source: str, limit: int
) -> None:
    """Search for jobs across job boards.

    QUERY: Job title or keyword to search for

    Example:
        job-automation discover search "Python Developer" --location "San Francisco"
        job-automation discover search "Data Scientist" --source indeed
    """
    click.echo(f"🔍 Searching for: {query}")
    if location:
        click.echo(f"📍 Location: {location}")

    scrapers = {}
    if source == "all" or source == "indeed":
        scrapers["indeed"] = IndeedScraper()
    if source == "all" or source == "linkedin":
        scrapers["linkedin"] = LinkedInScraper()
    if source == "all" or source == "glassdoor":
        scrapers["glassdoor"] = GlassdoorScraper()
    if source == "all" or source == "ziprecruiter":
        scrapers["ziprecruiter"] = ZipRecruiterScraper()
    if source == "all" or source == "google_jobs":
        scrapers["google_jobs"] = GoogleJobsScraper()

    all_jobs = []
    with JobDiscoveryRepository(ctx.obj["db_path"]) as discovery_repo:
        for source_name, scraper in scrapers.items():
            try:
                click.echo(f"  Searching {source_name}...", err=True)
                jobs = scraper.search(query, location, page=1)

                # Save jobs to database
                if jobs:
                    discovery_repo.add_jobs(jobs)
                    all_jobs.extend(jobs[:limit])
                    click.echo(f"  Found {len(jobs)} jobs on {source_name}", err=True)
                    discovery_repo.update_scraper_status(source_name, success=True)
                else:
                    click.echo(f"  No jobs found on {source_name}", err=True)
                    discovery_repo.update_scraper_status(source_name, success=True)
            except Exception as e:
                click.echo(f"  Error searching {source_name}: {e}", err=True)
                discovery_repo.update_scraper_status(source_name, success=False, error_message=str(e))
            finally:
                scraper.close()

    if not all_jobs:
        click.echo("No jobs found.")
        return

    click.echo(f"\n📋 Found {len(all_jobs)} jobs:\n")
    for i, job in enumerate(all_jobs[:limit], 1):
        click.echo(f"{i}. {job.title}")
        click.echo(f"   Company: {job.company}")
        click.echo(f"   Location: {job.location}")
        if job.salary:
            click.echo(f"   Salary: {job.salary}")
        click.echo(f"   Source: {job.source}")
        click.echo(f"   URL: {job.url}")
        click.echo()


@discover_group.command(name="list")
@click.option("--source", default=None, help="Filter by job board source.")
@click.option("--limit", type=int, default=20, help="Number of jobs to show.")
@click.option("--offset", type=int, default=0, help="Offset for pagination.")
@click.pass_context
def discover_list(ctx: click.Context, source: str, limit: int, offset: int) -> None:
    """List discovered jobs.

    Example:
        job-automation discover list
        job-automation discover list --source indeed --limit 50
    """
    with JobDiscoveryRepository(ctx.obj["db_path"]) as repo:
        jobs = repo.list_jobs(source=source, limit=limit, offset=offset)
        total = repo.get_job_count(source=source)

    if not jobs:
        click.echo("No jobs found.")
        return

    click.echo(f"📋 Jobs ({offset + 1}-{offset + len(jobs)} of {total}):\n")
    for i, job in enumerate(jobs, offset + 1):
        click.echo(f"{i}. {job.title}")
        click.echo(f"   Company: {job.company}")
        click.echo(f"   Location: {job.location}")
        if job.salary:
            click.echo(f"   Salary: {job.salary}")
        click.echo(f"   Source: {job.source}")
        click.echo(f"   Discovered: {job.discovered_date.strftime('%Y-%m-%d %H:%M')}")
        click.echo()


@discover_group.command(name="search-jobs")
@click.argument("search_query")
@click.option("--limit", type=int, default=20, help="Number of results to show.")
@click.pass_context
def discover_search_jobs(ctx: click.Context, search_query: str, limit: int) -> None:
    """Search through discovered jobs in the database.

    SEARCH_QUERY: Search term (matches title, company, location)

    Example:
        job-automation discover search-jobs "Python"
        job-automation discover search-jobs "San Francisco"
    """
    with JobDiscoveryRepository(ctx.obj["db_path"]) as repo:
        jobs = repo.search_jobs(search_query, limit=limit)

    if not jobs:
        click.echo(f"No jobs found matching '{search_query}'.")
        return

    click.echo(f"🔍 Found {len(jobs)} jobs matching '{search_query}':\n")
    for i, job in enumerate(jobs, 1):
        click.echo(f"{i}. {job.title}")
        click.echo(f"   Company: {job.company}")
        click.echo(f"   Location: {job.location}")
        click.echo(f"   Source: {job.source}")
        click.echo(f"   URL: {job.url}")
        click.echo()


@discover_group.command(name="stats")
@click.pass_context
def discover_stats(ctx: click.Context) -> None:
    """Show job discovery statistics."""
    with JobDiscoveryRepository(ctx.obj["db_path"]) as repo:
        for source in ["indeed", "linkedin", "glassdoor", "ziprecruiter", "google_jobs"]:
            count = repo.get_job_count(source=source)
            status = repo.get_scraper_status(source)

            click.echo(f"\n{source.upper()}:")
            click.echo(f"  Jobs: {count}")
            if status:
                click.echo(f"  Last run: {status['last_run']}")
                click.echo(f"  Last success: {status['last_success']}")
                if status['error_count'] > 0:
                    click.echo(f"  Errors: {status['error_count']}")
                    if status['error_message']:
                        click.echo(f"  Last error: {status['error_message']}")


@discover_group.command(name="clean")
@click.option("--days", type=int, default=30, help="Delete jobs older than N days.")
@click.confirmation_option(prompt="Delete old jobs? This cannot be undone.")
@click.pass_context
def discover_clean(ctx: click.Context, days: int) -> None:
    """Delete old discovered jobs to save space.

    Example:
        job-automation discover clean --days 30
    """
    with JobDiscoveryRepository(ctx.obj["db_path"]) as repo:
        deleted = repo.delete_jobs_before(days)

    click.echo(f"✅ Deleted {deleted} jobs older than {days} days.")


@main.group(name="score")
@click.pass_context
def score_group(ctx: click.Context) -> None:
    """Score and rank job listings based on profile match."""
    pass


@score_group.command(name="jobs")
@click.option("--min-score", type=int, default=6, help="Minimum match score (1-10).")
@click.option("--top", type=int, default=10, help="Show top N matches.")
@click.option("--use-claude", is_flag=True, default=False, help="Use Claude AI for intelligent scoring.")
@click.option("--source", default=None, help="Filter by job board source.")
@click.pass_context
def score_jobs(
    ctx: click.Context, min_score: int, top: int, use_claude: bool, source: str
) -> None:
    """Score and rank discovered jobs based on your profile.

    Uses machine learning to match job requirements to your skills and experience.

    Example:
        job-automation score jobs --min-score 7 --top 20
        job-automation score jobs --use-claude  # Use Claude for better scoring
    """
    try:
        # Load profile
        profile_loader = ProfileLoader()
        if not profile_loader.validate_profile():
            raise click.ClickException(
                "Profile not found at ~/.job-automation/profile.json"
            )
        profile = profile_loader.load_profile()

        # Load discovered jobs
        with JobDiscoveryRepository(ctx.obj["db_path"]) as repo:
            jobs = repo.list_jobs(source=source, limit=1000)

        if not jobs:
            click.echo("No jobs found. Try running 'job-automation discover search' first.")
            return

        click.echo(f"🔍 Scoring {len(jobs)} jobs based on your profile...")
        if profile.skills:
            click.echo(f"   Your skills: {', '.join(profile.skills[:5])}")
        click.echo(f"   Target: {profile.target_role}")
        click.echo()

        # Rank jobs
        ranker = JobRanker()
        ranked = ranker.rank_jobs(
            jobs, profile, min_score=min_score, use_claude=use_claude
        )

        if not ranked:
            click.echo(f"No jobs matched your criteria (min score: {min_score}).")
            click.echo("Try lowering --min-score or running 'discover search' to find more jobs.")
            return

        # Display results
        click.echo(ranker.get_ranking_summary(ranked[:top]))

        # Save results
        click.echo(f"\n✅ Found {len(ranked)} matching jobs (showing top {min(top, len(ranked))})")

    except FileNotFoundError as e:
        raise click.ClickException(f"Configuration error: {e}")
    except Exception as e:
        raise click.ClickException(f"Scoring error: {e}")


@score_group.command(name="update-profile")
@click.option("--skills", multiple=True, help="Add skills (can use multiple times).")
@click.option("--experience", type=int, help="Years of experience.")
@click.option("--role", help="Target role/title.")
@click.option("--industries", multiple=True, help="Preferred industries.")
@click.option("--remote", type=click.Choice(["remote", "hybrid", "onsite"]), help="Remote preference.")
@click.pass_context
def score_update_profile(
    ctx: click.Context,
    skills: tuple,
    experience: int,
    role: str,
    industries: tuple,
    remote: str,
) -> None:
    """Update your profile for better job scoring.

    Example:
        job-automation score update-profile --skills Python --skills JavaScript \\
          --experience 5 --role "Senior Developer" --remote hybrid
    """
    try:
        profile_loader = ProfileLoader()
        if not profile_loader.validate_profile():
            raise click.ClickException("Profile not found")

        profile = profile_loader.load_profile()

        # Update profile fields
        if skills:
            profile.skills = list(skills)
            click.echo(f"✅ Skills updated: {', '.join(profile.skills)}")

        if experience is not None:
            profile.years_of_experience = experience
            click.echo(f"✅ Experience updated: {experience} years")

        if role:
            profile.target_role = role
            click.echo(f"✅ Target role updated: {role}")

        if industries:
            profile.preferred_industries = list(industries)
            click.echo(f"✅ Preferred industries: {', '.join(profile.preferred_industries)}")

        if remote:
            profile.remote_preference = remote
            click.echo(f"✅ Remote preference: {remote}")

        # Save updated profile
        profile_loader.save_profile(profile)
        click.echo("\n✅ Profile saved successfully!")

    except Exception as e:
        raise click.ClickException(f"Error updating profile: {e}")


if __name__ == "__main__":
    main()
