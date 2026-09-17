"""Tests for the job discovery database repository."""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from job_automation.db import JobDiscoveryRepository
from job_automation.models import Job


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield db_path


@pytest.fixture
def repo(temp_db):
    """Create a JobDiscoveryRepository for testing."""
    repository = JobDiscoveryRepository(temp_db)
    try:
        yield repository
    finally:
        # SQLite keeps the database file locked on Windows until its connection
        # is closed.  Closing here lets TemporaryDirectory remove test.db.
        repository.close()


@pytest.fixture
def sample_job():
    """Create a sample job for testing."""
    return Job(
        source="indeed",
        job_id="job123",
        title="Python Developer",
        company="Tech Corp",
        location="San Francisco, CA",
        salary="$100k-$150k",
        description="Looking for a Python developer",
        url="https://indeed.com/jobs/123",
    )


class TestJobDiscoveryRepository:
    """Tests for JobDiscoveryRepository."""

    def test_repository_creation(self, temp_db):
        """Test that repository creates database."""
        repo = JobDiscoveryRepository(temp_db)
        assert temp_db.exists()
        repo.close()

    def test_add_job(self, repo, sample_job):
        """Test adding a job to the database."""
        added_job = repo.add_job(sample_job)
        assert added_job.id is not None
        assert added_job.job_id == "job123"
        assert added_job.source == "indeed"

    def test_get_job(self, repo, sample_job):
        """Test retrieving a job from the database."""
        added_job = repo.add_job(sample_job)
        retrieved_job = repo.get_job("job123")

        assert retrieved_job is not None
        assert retrieved_job.id == added_job.id
        assert retrieved_job.title == "Python Developer"

    def test_add_multiple_jobs(self, repo, sample_job):
        """Test adding multiple jobs."""
        jobs = [
            sample_job,
            Job(
                source="linkedin",
                job_id="job456",
                title="Data Scientist",
                company="AI Corp",
                location="New York, NY",
                url="https://linkedin.com/jobs/456",
            ),
        ]

        added_jobs = repo.add_jobs(jobs)
        assert len(added_jobs) == 2
        assert all(job.id is not None for job in added_jobs)

    def test_list_jobs(self, repo, sample_job):
        """Test listing jobs from the database."""
        repo.add_job(sample_job)
        repo.add_job(Job(
            source="linkedin",
            job_id="job456",
            title="Data Scientist",
            company="AI Corp",
            location="New York, NY",
            url="https://linkedin.com/jobs/456",
        ))

        jobs = repo.list_jobs()
        assert len(jobs) == 2

    def test_list_jobs_by_source(self, repo, sample_job):
        """Test listing jobs filtered by source."""
        repo.add_job(sample_job)
        repo.add_job(Job(
            source="linkedin",
            job_id="job456",
            title="Data Scientist",
            company="AI Corp",
            location="New York, NY",
            url="https://linkedin.com/jobs/456",
        ))

        indeed_jobs = repo.list_jobs(source="indeed")
        linkedin_jobs = repo.list_jobs(source="linkedin")

        assert len(indeed_jobs) == 1
        assert len(linkedin_jobs) == 1
        assert indeed_jobs[0].source == "indeed"
        assert linkedin_jobs[0].source == "linkedin"

    def test_search_jobs(self, repo, sample_job):
        """Test searching jobs by title, company, or location."""
        repo.add_job(sample_job)
        repo.add_job(Job(
            source="linkedin",
            job_id="job456",
            title="Senior Python Developer",
            company="AI Corp",
            location="San Francisco, CA",
            url="https://linkedin.com/jobs/456",
        ))

        # Search by title
        results = repo.search_jobs("Python")
        assert len(results) == 2

        # Search by company
        results = repo.search_jobs("Tech Corp")
        assert len(results) == 1

        # Search by location
        results = repo.search_jobs("San Francisco")
        assert len(results) == 2

    def test_get_job_count(self, repo, sample_job):
        """Test getting job count."""
        repo.add_job(sample_job)
        repo.add_job(Job(
            source="linkedin",
            job_id="job456",
            title="Data Scientist",
            company="AI Corp",
            location="New York, NY",
            url="https://linkedin.com/jobs/456",
        ))

        total_count = repo.get_job_count()
        indeed_count = repo.get_job_count(source="indeed")
        linkedin_count = repo.get_job_count(source="linkedin")

        assert total_count == 2
        assert indeed_count == 1
        assert linkedin_count == 1

    def test_delete_job(self, repo, sample_job):
        """Test deleting a job."""
        repo.add_job(sample_job)
        assert repo.get_job("job123") is not None

        repo.delete_job("job123")
        assert repo.get_job("job123") is None

    def test_update_scraper_status(self, repo):
        """Test updating scraper status."""
        repo.update_scraper_status("indeed", success=True)
        status = repo.get_scraper_status("indeed")

        assert status is not None
        assert status["source"] == "indeed"
        assert status["last_run"] is not None
        assert status["last_success"] is not None
        assert status["error_count"] == 0

    def test_update_scraper_status_with_error(self, repo):
        """Test updating scraper status with an error."""
        repo.update_scraper_status("indeed", success=False, error_message="Connection failed")
        status = repo.get_scraper_status("indeed")

        assert status is not None
        assert status["error_count"] >= 1
        assert status["error_message"] == "Connection failed"

    def test_duplicate_job_update(self, repo, sample_job):
        """Test that adding a duplicate job updates it."""
        job1 = repo.add_job(sample_job)

        # Add same job with updated title
        updated_job = sample_job.model_copy(update={"title": "Senior Python Developer"})
        job2 = repo.add_job(updated_job)

        # IDs should be the same (OR REPLACE behavior)
        retrieved = repo.get_job("job123")
        assert retrieved.title == "Senior Python Developer"

    def test_pagination(self, repo):
        """Test pagination when listing jobs."""
        # Add 25 jobs
        for i in range(25):
            repo.add_job(Job(
                source="indeed",
                job_id=f"job{i}",
                title=f"Job {i}",
                company="Tech Corp",
                location="San Francisco",
                url=f"https://indeed.com/jobs/{i}",
            ))

        # Get first page (10 jobs)
        page1 = repo.list_jobs(limit=10, offset=0)
        assert len(page1) == 10

        # Get second page (10 jobs)
        page2 = repo.list_jobs(limit=10, offset=10)
        assert len(page2) == 10

        # Get third page (5 jobs)
        page3 = repo.list_jobs(limit=10, offset=20)
        assert len(page3) == 5

        # Jobs should be different across pages
        assert page1[0].job_id != page2[0].job_id
        assert page2[0].job_id != page3[0].job_id

    def test_context_manager(self, temp_db):
        """Test repository context manager."""
        with JobDiscoveryRepository(temp_db) as repo:
            repo.add_job(Job(
                source="indeed",
                job_id="job123",
                title="Python Developer",
                company="Tech Corp",
                location="San Francisco",
                url="https://indeed.com/jobs/123",
            ))
        # Repository should be closed after context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
