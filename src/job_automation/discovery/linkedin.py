"""Scraper for LinkedIn job listings."""

from __future__ import annotations

import re
from urllib.parse import quote

from job_automation.models import Job
from job_automation.discovery.scraper_base import BaseScraper


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn job listings."""

    def __init__(self) -> None:
        """Initialize the LinkedIn scraper."""
        super().__init__(
            source="linkedin",
            base_url="https://www.linkedin.com",
            delay_between_requests=3.0,  # LinkedIn is stricter about rate limiting
        )
        # LinkedIn requires specific headers
        self.session.headers.update(
            {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs on LinkedIn.

        Note: LinkedIn has JavaScript-rendered content, so this scraper
        may have limited effectiveness. Consider using Selenium for better results.

        Args:
            query: Job title or keyword
            location: Job location
            page: Page number for pagination

        Returns:
            List of Job objects
        """
        jobs = []

        # Build search URL
        # LinkedIn uses keywords and location in the search
        start = (page - 1) * 25  # LinkedIn shows 25 results per page
        search_url = f"{self.base_url}/jobs/search"
        params = {
            "keywords": query,
            "location": location,
            "start": start,
        }

        response = self._get(search_url, params=params)
        if not response:
            print(f"Failed to fetch LinkedIn search results for {query}")
            return jobs

        soup = self._parse_html(response.text)

        # Find job listings
        # LinkedIn's structure varies, but we look for job card elements
        job_cards = soup.find_all(
            "div", {"class": "base-card"}
        )

        for card in job_cards:
            try:
                # Extract job title
                title_elem = card.find("h3", {"class": "base-search-card__title"})
                title = self.extract_text(title_elem)
                if not title:
                    continue

                # Extract company name
                company_elem = card.find(
                    "h4", {"class": "base-search-card__subtitle"}
                )
                company = self.extract_text(company_elem)
                if not company:
                    continue

                # Extract location
                location_elem = card.find(
                    "span", {"class": "job-search-card__location"}
                )
                location = self.extract_text(location_elem)

                # Extract job URL
                url_elem = card.find("a", {"class": "base-card__full-link"})
                job_url = self.extract_attr(url_elem, "href")
                if not job_url:
                    continue

                # Extract job ID from URL
                job_id_match = re.search(r"jobId=(\d+)", job_url)
                job_id = job_id_match.group(1) if job_id_match else job_url.split("/")[-1]

                job = self.create_job(
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    url=job_url,
                )
                jobs.append(job)

            except Exception as e:
                print(f"Error parsing LinkedIn job card: {e}")
                continue

        return jobs

    def scrape_job_details(self, job_url: str) -> Job | None:
        """Scrape detailed information for a single job from LinkedIn.

        Args:
            job_url: URL of the job listing

        Returns:
            Job object with full details or None if scraping failed
        """
        response = self._get(job_url)
        if not response:
            return None

        soup = self._parse_html(response.text)

        try:
            # Extract job description
            description_elem = soup.find(
                "div", {"class": "show-more-less-html__markup"}
            )
            description = self.extract_text(description_elem)

            # Note: Due to LinkedIn's JavaScript rendering, this will be limited
            # Full implementation would require Selenium or Playwright

            return None  # Placeholder

        except Exception as e:
            print(f"Error scraping LinkedIn job details from {job_url}: {e}")
            return None
