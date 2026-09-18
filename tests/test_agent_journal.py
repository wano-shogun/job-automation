"""Checks durable agent handoffs and failure recording."""

from job_automation.agent import ApplicationAgent, ApplicationStage
from job_automation.agent.journal import AgentJournal
from job_automation.models import Job
from job_automation.profile.models import Profile
from job_automation.scoring.ranker import JobRanker


class ProfileSource:
    def load_profile(self):
        return Profile(
            name="Jane Developer", email="jane@example.com", phone="555-0100",
            skills=["Python"], years_of_experience=5,
        )


def _job():
    return Job(
        source="ashby", job_id="abc", title="Python Developer",
        company="Example", location="Remote", description="Python developer",
        url="https://jobs.ashbyhq.com/example/abc/application",
    )


def test_plan_deduplicates_and_journal_survives_reopen(tmp_path):
    job = _job()
    agent = ApplicationAgent(ProfileSource(), lambda query, location: [job, job], JobRanker())
    plan = agent.plan("Python Developer", min_score=1)
    assert len(plan.jobs) == 1

    path = tmp_path / "runs.db"
    with AgentJournal(path) as journal:
        journal.create_plan("run-1", plan)
        journal.create_plan("run-1", plan)
        assert journal.latest()[0]["stage"] == "ranked"

    with AgentJournal(path) as journal:
        assert journal.latest()[0]["job_title"] == "Python Developer"
        count = journal.connection.execute("SELECT count(*) FROM agent_events").fetchone()[0]
        assert count == 1


def test_browser_failure_is_recorded_as_failed(tmp_path):
    class BrokenSubmitter:
        def submit_application(self, url, resume_path, *, submit):
            raise RuntimeError("Browser navigation failed")

    agent = ApplicationAgent(ProfileSource(), lambda query, location: [_job()], JobRanker())
    plan = agent.plan("Python Developer", min_score=1)
    with AgentJournal(tmp_path / "runs.db") as journal:
        result = agent.run("Python Developer", BrokenSubmitter(), plan=plan, journal=journal)
        assert result.items[0].stage == ApplicationStage.FAILED
        assert journal.latest()[0]["stage"] == "failed"
        events = journal.connection.execute(
            "SELECT stage FROM agent_events ORDER BY id"
        ).fetchall()
        assert events == [("ranked",), ("filling",), ("failed",)]
