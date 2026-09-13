"""Base class for job board scrapers with common functionality."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from job_automation.models import Job


class BaseScraper(ABC):
    """Abstract base class for job board scrapers."""

    def __init__(
        self,
        source: str,
        base_url: str,
        delay_between_requests: float = 1.0,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize the scraper.

        Args:
            source: Name of the job board (e.g., "indeed", "linkedin")
            base_url: Base URL of the job board
            delay_between_requests: Seconds to wait between requests (rate limiting)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.source = source
        self.base_url = base_url
        self.delay_between_requests = delay_between_requests
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_time = 0.0

        # Set up session with proper headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

    def __enter__(self) -> BaseScraper:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def _rate_limit(self) -> None:
        """Apply rate limiting to avoid overwhelming the server."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay_between_requests:
            time.sleep(self.delay_between_requests - elapsed)
        self.last_request_time = time.time()

    def _get(self, url: str, **kwargs: Any) -> requests.Response | None:
        """Make a GET request with rate limiting and retries.

        Args:
            url: URL to request
            **kwargs: Additional arguments to pass to requests.get

        Returns:
            Response object or None if all retries failed
        """
        self._rate_limit()

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(
                    url, timeout=self.timeout, **kwargs
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    print(f"Error fetching {url} after {self.max_retries} retries: {e}")
                    return None
                wait_time = (attempt + 1) * 2  # Exponential backoff
                print(f"Request failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

        return None

    def _parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content.

        Args:
            html: HTML content as string

        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html, "html.parser")

    @abstractmethod
    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs.

        Args:
            query: Job title or keyword
            location: Job location (optional)
            page: Page number for pagination

        Returns:
            List of Job objects
        """
        pass

    @abstractmethod
    def scrape_job_details(self, job_url: str) -> Job | None:
        """Scrape detailed information for a single job.

        Args:
            job_url: URL of the job listing

        Returns:
            Job object or None if scraping failed
        """
        pass

    def extract_text(self, element: Any, selector: str = "") -> str:
        """Extract and clean text from an element.

        Args:
            element: BeautifulSoup element
            selector: CSS selector to find element within element

        Returns:
            Cleaned text
        """
        if selector:
            element = element.select_one(selector)
        if not element:
            return ""
        return element.get_text(strip=True)

    def extract_attr(self, element: Any, attr: str, selector: str = "") -> str:
        """Extract an attribute value from an element.

        Args:
            element: BeautifulSoup element
            attr: Attribute name
            selector: CSS selector to find element within element

        Returns:
            Attribute value or empty string
        """
        if selector:
            element = element.select_one(selector)
        if not element:
            return ""
        return element.get(attr, "")

    def create_job(
        self,
        job_id: str,
        title: str,
        company: str,
        location: str,
        url: str,
        salary: str | None = None,
        description: str | None = None,
        posted_date: str | None = None,
    ) -> Job:
        """Create a Job object with common defaults.

        Args:
            job_id: Unique ID from the source
            title: Job title
            company: Company name
            location: Job location
            url: Job posting URL
            salary: Salary information (optional)
            description: Job description (optional)
            posted_date: Posted date as ISO format string (optional)

        Returns:
            Job object
        """
        return Job(
            source=self.source,
            job_id=job_id,
            title=title,
            company=company,
            location=location,
            salary=salary,
            description=description,
            url=url,
            posted_date=posted_date,
            discovered_date=datetime.now(),
            scraped_at=datetime.now(),
        )
