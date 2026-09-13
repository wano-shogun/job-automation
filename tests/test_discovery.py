"""Tests for the job discovery module."""

import pytest
from unittest.mock import Mock, patch

from job_automation.discovery.scraper_base import BaseScraper
from job_automation.discovery.indeed import IndeedScraper
from job_automation.discovery.linkedin import LinkedInScraper
from job_automation.discovery.glassdoor import GlassdoorScraper
from job_automation.discovery.ziprecruiter import ZipRecruiterScraper
from job_automation.discovery.google_jobs import GoogleJobsScraper
from job_automation.models import Job


class ConcreteBaseScraper(BaseScraper):
    """Concrete implementation of BaseScraper for testing."""

    def search(self, query: str, location: str = "", page: int = 1):
        return []

    def scrape_job_details(self, job_url: str):
        return None


class TestBaseScraper:
    """Tests for the BaseScraper base class."""

    def test_scraper_initialization(self):
        """Test scraper initialization."""
        scraper = ConcreteBaseScraper(
            source="test",
            base_url="https://test.com",
            delay_between_requests=1.0,
        )
        assert scraper.source == "test"
        assert scraper.base_url == "https://test.com"
        assert scraper.delay_between_requests == 1.0

    def test_create_job(self):
        """Test creating a Job object."""
        scraper = ConcreteBaseScraper(
            source="test",
            base_url="https://test.com",
        )

        job = scraper.create_job(
            job_id="123",
            title="Python Developer",
            company="Tech Corp",
            location="San Francisco, CA",
            url="https://test.com/jobs/123",
            salary="$100k-$150k",
            description="Looking for a Python developer",
        )

        assert job.job_id == "123"
        assert job.title == "Python Developer"
        assert job.company == "Tech Corp"
        assert job.location == "San Francisco, CA"
        assert job.salary == "$100k-$150k"
        assert job.source == "test"

    def test_extract_text(self):
        """Test text extraction from HTML elements."""
        from bs4 import BeautifulSoup

        scraper = ConcreteBaseScraper(
            source="test",
            base_url="https://test.com",
        )

        html = '<div class="title"><h1>Job Title</h1></div>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.find("div", {"class": "title"})

        text = scraper.extract_text(element, "h1")
        assert text == "Job Title"

    def test_extract_attr(self):
        """Test attribute extraction from HTML elements."""
        from bs4 import BeautifulSoup

        scraper = ConcreteBaseScraper(
            source="test",
            base_url="https://test.com",
        )

        html = '<div><a href="https://example.com">Link</a></div>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.find("div")

        url = scraper.extract_attr(element, "href", "a")
        assert url == "https://example.com"

    def test_context_manager(self):
        """Test scraper context manager."""
        scraper = ConcreteBaseScraper(
            source="test",
            base_url="https://test.com",
        )

        with scraper as s:
            assert s.source == "test"


class TestIndeedScraper:
    """Tests for the Indeed scraper."""

    def test_indeed_initialization(self):
        """Test Indeed scraper initialization."""
        scraper = IndeedScraper()
        assert scraper.source == "indeed"
        assert "indeed.com" in scraper.base_url
        assert scraper.delay_between_requests >= 2.0

    def test_indeed_search_returns_list(self):
        """Test that search returns a list."""
        scraper = IndeedScraper()
        # Without mocking actual HTTP requests, this will fail or return empty
        # but we're testing the interface
        result = scraper.search("Python Developer", "San Francisco")
        assert isinstance(result, list)

    def test_indeed_scraper_close(self):
        """Test scraper cleanup."""
        scraper = IndeedScraper()
        scraper.close()
        # Session should be closed


class TestLinkedInScraper:
    """Tests for the LinkedIn scraper."""

    def test_linkedin_initialization(self):
        """Test LinkedIn scraper initialization."""
        scraper = LinkedInScraper()
        assert scraper.source == "linkedin"
        assert "linkedin.com" in scraper.base_url
        assert scraper.delay_between_requests >= 3.0

    def test_linkedin_custom_headers(self):
        """Test that LinkedIn scraper sets custom headers."""
        scraper = LinkedInScraper()
        assert "Accept-Language" in scraper.session.headers
        assert "en-US" in scraper.session.headers["Accept-Language"]


class TestGlassdoorScraper:
    """Tests for the Glassdoor scraper."""

    def test_glassdoor_initialization(self):
        """Test Glassdoor scraper initialization."""
        scraper = GlassdoorScraper()
        assert scraper.source == "glassdoor"
        assert "glassdoor.com" in scraper.base_url


class TestZipRecruiterScraper:
    """Tests for the ZipRecruiter scraper."""

    def test_ziprecruiter_initialization(self):
        """Test ZipRecruiter scraper initialization."""
        scraper = ZipRecruiterScraper()
        assert scraper.source == "ziprecruiter"
        assert "ziprecruiter.com" in scraper.base_url


class TestGoogleJobsScraper:
    """Tests for the Google Jobs scraper."""

    def test_google_jobs_initialization(self):
        """Test Google Jobs scraper initialization."""
        scraper = GoogleJobsScraper()
        assert scraper.source == "google_jobs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
