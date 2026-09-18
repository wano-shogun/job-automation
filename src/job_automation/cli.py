"""Command-line interface for job_automation.

Run `job-automation --help` (after an editable install) or
`python -m job_automation.cli --help` to see all commands.
"""

from __future__ import annotations

import click
from uuid import uuid4

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
from job_automation.apply import JobSubmitter
from job_automation.agent import AgentMode, ApplicationAgent
from job_automation.agent.journal import AgentJournal
from job_automation.discovery.ashby import search_ashby_board
from job_automation.web import create_server


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


@main.command(name="web")
@click.option("--port", default=8765, type=click.IntRange(1, 65535), show_default=True)
@click.pass_context
def web_preview(ctx: click.Context, port: int) -> None:
    """Start the local read-only web preview."""
    try:
        with create_server(ctx.obj["db_path"], port) as server:
            click.echo(f"ApplyPilot preview: http://127.0.0.1:{port}")
            server.serve_forever()
    except KeyboardInterrupt:
        click.echo("Preview stopped.")
    except OSError as exc:
        raise click.ClickException(f"Cannot start preview on port {port}: {exc}") from exc


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


@main.group(name="apply")
def apply_group() -> None:
    """Fill a live application in Chrome and optionally submit it."""


@main.group(name="agent")
def agent_group() -> None:
    """Search, rank, and prepare live job applications."""


@agent_group.command(name="run")
@click.argument("query")
@click.option("--location", default="", help="Job location or Remote.")
@click.option("--max-jobs", default=1, type=click.IntRange(1, 10), show_default=True)
@click.option("--min-score", default=6, type=click.IntRange(1, 10), show_default=True)
@click.option("--headless", is_flag=True, help="Run Chrome without showing a window.")
@click.option("--ashby-board", multiple=True, help="Search this public Ashby job board; repeat for more boards.")
@click.option("--resume", type=click.Path(exists=True, dir_okay=False), default=None, help="Resume to attach when requested.")
@click.pass_context
def agent_run(ctx: click.Context, query: str, location: str, max_jobs: int, min_score: int, headless: bool, ashby_board: tuple[str, ...], resume: str | None) -> None:
    """Search online, rank matches, and fill up to MAX_JOBS for review."""
    loader = ProfileLoader()
    if not loader.validate_profile() or not loader.validate_answers():
        raise click.ClickException("Create profile.json and answers.json in ~/.job-automation first.")
    if not ashby_board:
        raise click.ClickException("Provide at least one --ashby-board NAME. The agent needs direct application URLs; Indeed discovery currently returns listing URLs.")
    profile = loader.load_profile()
    click.echo(f"Using profile: {profile.name} ({profile.email})")

    def discover(search_query: str, search_location: str):
        jobs = []
        failures = []
        for board in ashby_board:
            try:
                jobs.extend(search_ashby_board(board, search_query, search_location))
            except Exception as exc:
                failures.append(f"{board}: {exc}")
        for failure in failures:
            click.echo(f"Board search failed: {failure}", err=True)
        if len(failures) == len(ashby_board):
            raise click.ClickException("Every configured Ashby board failed. No browser page was opened.")
        return jobs

    agent = ApplicationAgent(loader, discover)
    plan = agent.plan(query, location, max_jobs=max_jobs, min_score=min_score)
    if not plan.jobs:
        click.echo("No matching jobs found. No application page was opened.")
        return
    click.echo(f"Found {len(plan.jobs)} ranked job(s) (heuristic scores):")
    for item in plan.jobs:
        click.echo(f"  {item.score}/10 {item.job.title} at {item.job.company}: {item.job.url}")

    with AgentJournal(ctx.obj["db_path"]) as journal:
        run_id = uuid4().hex
        journal.create_plan(run_id, plan)
        browser = BrowserDriver(headless=headless)
        browser.start()
        try:
            result = agent.run(
                query,
                JobSubmitter(browser.get_driver(), loader),
                location,
                mode=AgentMode.HEADLESS if headless else AgentMode.VISIBLE,
                max_jobs=max_jobs,
                min_score=min_score,
                resume_path=resume,
                plan=plan,
                journal=journal,
                run_id=run_id,
            )
            click.echo(f"Run ID: {result.run_id}")
            filled = sum(bool(item.submission and item.submission.fields_filled) for item in result.items)
            click.echo(f"Filled {filled} application form(s); {result.ready_for_review} ready for review.")
            for item in result.items:
                click.echo(f"{item.job.title} at {item.job.company}: " + (item.error or item.stage.value))
                if item.submission:
                    click.echo(f"  Fields filled: {len(item.submission.fields_filled)}")
                if item.submission and item.submission.required_fields_needing_review:
                    click.echo("  Needs review: " + ", ".join(item.submission.required_fields_needing_review))
            if not headless:
                click.echo("Browser remains open for review. Press Ctrl+C to close it.")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
        finally:
            browser.stop()


@agent_group.command(name="status")
@click.pass_context
def agent_status(ctx: click.Context) -> None:
    """Show recently prepared application attempts and their last stage."""
    with AgentJournal(ctx.obj["db_path"]) as journal:
        rows = journal.latest()
    if not rows:
        click.echo("No agent attempts recorded yet.")
    for row in rows:
        click.echo(
            f"{str(row['run_id'])[:8]} {row['stage']} "
            f"{row['job_title']} at {row['company']} "
            f"({row['fields_filled']} fields filled)"
        )


@apply_group.command(name="fill")
@click.argument("url")
@click.option("--resume", type=click.Path(exists=True, dir_okay=False), default=None)
@click.option("--submit", is_flag=True, help="Click the final submit button after filling.")
@click.option("--headless", is_flag=True, help="Run Chrome without displaying a window.")
@click.pass_context
def apply_fill(ctx: click.Context, url: str, resume: str | None, submit: bool, headless: bool) -> None:
    """Fill URL from your profile and stop for review unless --submit is used."""
    loader = ProfileLoader()
    if not loader.validate_profile():
        raise click.ClickException("Profile not found at ~/.job-automation/profile.json")
    if not loader.validate_answers():
        raise click.ClickException("Answers not found at ~/.job-automation/answers.json")
    if submit and headless:
        raise click.ClickException("Final submission requires visible Chrome so the completed form can be reviewed.")

    browser = BrowserDriver(headless=headless)
    browser.start()
    try:
        submitter = JobSubmitter(browser.get_driver(), loader)
        result = submitter.submit_application(url, resume, submit=False)
        click.echo(f"Status: {result.status}")
        click.echo(f"Fields filled: {len(result.fields_filled)}")
        if result.required_fields_needing_review:
            click.echo("Needs review: " + ", ".join(result.required_fields_needing_review))
        if result.notes:
            click.echo(result.notes)
        if submit and result.status == "ready_for_review":
            click.echo("Review the completed application in Chrome before deciding to send it.")
            if click.confirm("Click the final Submit button now?"):
                result = submitter.submit_filled_application(result)
                click.echo(f"Final status: {result.status}")
        if result.status == "submitted":
            with JobRepository(ctx.obj["db_path"]) as repo:
                saved = repo.add(submitter.save_submission_record(result))
            click.echo(f"Saved application #{saved.id} to the tracker.")
        if not headless:
            click.echo("Browser remains open for review. Press Ctrl+C to close it.")
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
    finally:
        browser.stop()


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
