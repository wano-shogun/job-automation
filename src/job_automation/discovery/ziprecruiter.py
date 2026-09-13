"""Scraper for ZipRecruiter job listings."""

from __future__ import annotations

import re
from urllib.parse import quote

from job_automation.models import Job
from job_automation.discovery.scraper_base import BaseScraper


class ZipRecruiterScraper(BaseScraper):
    """Scraper for ZipRecruiter.com job listings."""

    def __init__(self) -> None:
        """Initialize the ZipRecruiter scraper."""
        super().__init__(
            source="ziprecruiter",
            base_url="https://www.ziprecruiter.com",
            delay_between_requests=2.0,
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs on ZipRecruiter.

        Args:
            query: Job title or keyword
            location: Job location
            page: Page number for pagination

        Returns:
            List of Job objects
        """
        jobs = []

        # Build search URL
        # ZipRecruiter format: /jobs/search?search=...&location=...
        search_url = f"{self.base_url}/jobs/search"
        params = {
            "search": query,
            "location": location,
            "p": page,
        }

        response = self._get(search_url, params=params)
        if not response:
            print(f"Failed to fetch ZipRecruiter search results for {query}")
            return jobs

        soup = self._parse_html(response.text)

        # Find job listings
        # ZipRecruiter uses article elements for job listings
        job_cards = soup.find_all("article", {"class": "job_result"})

        if not job_cards:
            # Fallback selector
            job_cards = soup.find_all("div", {"class": "job_item"})

        for card in job_cards:
            try:
                # Extract job title
                title_elem = card.find("a", {"class": "job_title"})
                if not title_elem:
                    title_elem = card.find("h2")
                title = self.extract_text(title_elem)
                if not title:
                    continue

                # Extract company name
                company_elem = card.find(
                    "a", {"class": "result_link company_name"}
                )
                if not company_elem:
                    company_elem = card.find("span", {"class": "company"})
                company = self.extract_text(company_elem)
                if not company:
                    continue

                # Extract location
                location_elem = card.find("span", {"class": "location"})
                location = self.extract_text(location_elem)

                # Extract job URL
                url_elem = card.find("a", {"class": "job_title"})
                job_url = self.extract_attr(url_elem, "href")
                if job_url and not job_url.startswith("http"):
                    job_url = f"{self.base_url}{job_url}"

                # Extract salary if available
                salary_elem = card.find("span", {"class": "salary"})
                salary = self.extract_text(salary_elem)

                # Extract job snippet/description
                snippet_elem = card.find("div", {"class": "job_snippet"})
                description = self.extract_text(snippet_elem)

                # Extract job ID from URL
                job_id_match = re.search(r"job[jid]*[=_]?(\d+)", job_url)
                job_id = (
                    job_id_match.group(1)
                    if job_id_match
                    else job_url.split("/")[-1]
                )

                if title and company and job_url:
                    job = self.create_job(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        salary=salary if salary else None,
                        description=description if description else None,
                    )
                    jobs.append(job)

            except Exception as e:
                print(f"Error parsing ZipRecruiter job card: {e}")
                continue

        return jobs

    def scrape_job_details(self, job_url: str) -> Job | None:
        """Scrape detailed information for a single job from ZipRecruiter.

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
                "div", {"class": "job_description"}
            )
            if not description_elem:
                description_elem = soup.find("div", {"id": "job_description"})
            description = self.extract_text(description_elem)

            return None  # Placeholder

        except Exception as e:
            print(f"Error scraping ZipRecruiter job details from {job_url}: {e}")
            return None
