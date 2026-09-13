"""Scraper for Google Jobs listings."""

from __future__ import annotations

import json
import re
from urllib.parse import quote

from job_automation.models import Job
from job_automation.discovery.scraper_base import BaseScraper


class GoogleJobsScraper(BaseScraper):
    """Scraper for Google Jobs listings."""

    def __init__(self) -> None:
        """Initialize the Google Jobs scraper."""
        super().__init__(
            source="google_jobs",
            base_url="https://www.google.com/search",
            delay_between_requests=2.0,
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs using Google Jobs.

        Note: Google Jobs aggregates listings from multiple sources.
        This scraper has limited effectiveness due to JavaScript rendering.

        Args:
            query: Job title or keyword
            location: Job location
            page: Page number for pagination

        Returns:
            List of Job objects
        """
        jobs = []

        # Build search URL
        # Google Jobs format: ?q=jobs+...+in+...&ibp=htl;jobs
        search_term = f"jobs {query}"
        if location:
            search_term += f" in {location}"

        search_url = "https://www.google.com/search"
        params = {
            "q": search_term,
            "ibp": "htl;jobs",
            "start": (page - 1) * 10,
        }

        response = self._get(search_url, params=params)
        if not response:
            print(f"Failed to fetch Google Jobs results for {query}")
            return jobs

        soup = self._parse_html(response.text)

        # Find job listings
        # Google Jobs uses div with specific data attributes
        job_cards = soup.find_all(
            "div", {"data-sokoban-container": True}
        )

        for card in job_cards:
            try:
                # Extract job title
                title_elem = card.find("h2")
                title = self.extract_text(title_elem)
                if not title:
                    continue

                # Extract company name
                company_elem = card.find("div", {"class": "YwonT"})
                if not company_elem:
                    company_elem = card.find("span", {"class": "pJ9hpe"})
                company = self.extract_text(company_elem)
                if not company:
                    continue

                # Extract location
                location_elem = card.find("span", {"class": "OUJc6b"})
                if not location_elem:
                    location_elem = card.find("div", {"class": "qiXUec"})
                location = self.extract_text(location_elem)

                # Extract job URL (Google redirects through their search results)
                url_elem = card.find("a")
                job_url = self.extract_attr(url_elem, "href")

                if title and company:
                    job_id = job_url.split("/")[-1] if job_url else ""
                    job = self.create_job(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                    )
                    jobs.append(job)

            except Exception as e:
                print(f"Error parsing Google Jobs card: {e}")
                continue

        return jobs

    def scrape_job_details(self, job_url: str) -> Job | None:
        """Scrape detailed information for a job from Google Jobs.

        Note: Google Jobs aggregates data, so detailed scraping is limited.

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
                "div", {"class": "job-description"}
            )
            description = self.extract_text(description_elem)

            return None  # Placeholder

        except Exception as e:
            print(f"Error scraping Google Jobs details from {job_url}: {e}")
            return None
