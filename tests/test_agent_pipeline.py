from job_automation.agent.pipeline import AgentMode, ApplicationAgent
from job_automation.models import Job
from job_automation.profile.models import Profile
from job_automation.scoring.ranker import JobRanker


class FakeProfileLoader:
    def load_profile(self):
        return Profile(name="Jane Dev", email="jane@example.com", phone="555-0100", skills=["Python", "React"], years_of_experience=5)


class FakeSubmitter:
    def __init__(self):
        self.urls = []

    def submit_application(self, url, resume_path, *, submit):
        self.urls.append((url, resume_path, submit))
        return type("Result", (), {"status": "ready_for_review"})()


def test_agent_searches_ranks_and_prepares_without_submission():
    job = Job(source="test", job_id="1", title="Python Developer", company="Example", location="Remote", description="Python React", url="https://example.com/apply")
    agent = ApplicationAgent(FakeProfileLoader(), lambda query, location: [job], JobRanker())
    submitter = FakeSubmitter()

    run = agent.run("Python Developer", submitter, mode=AgentMode.HEADLESS, max_jobs=1, min_score=1)

    assert run.ready_for_review == 1
    assert submitter.urls == [("https://example.com/apply", None, False)]
