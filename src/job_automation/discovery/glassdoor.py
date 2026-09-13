"""Scraper for Glassdoor job listings."""

from __future__ import annotations

from urllib.parse import quote

from job_automation.models import Job
from job_automation.discovery.scraper_base import BaseScraper


class GlassdoorScraper(BaseScraper):
    """Scraper for Glassdoor.com job listings."""

    def __init__(self) -> None:
        """Initialize the Glassdoor scraper."""
        super().__init__(
            source="glassdoor",
            base_url="https://www.glassdoor.com",
            delay_between_requests=2.5,
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs on Glassdoor.

        Note: Glassdoor heavily relies on JavaScript rendering.
        Consider using Selenium for better results.

        Args:
            query: Job title or keyword
            location: Job location
            page: Page number for pagination

        Returns:
            List of Job objects
        """
        jobs = []

        # Build search URL
        # Glassdoor search format: /Job/jobs.htm?keyword=...&location=...
        search_url = f"{self.base_url}/Job/jobs.htm"
        params = {
            "keyword": query,
            "location": location,
            "fromage": "any",
            "pageNum": page,
        }

        response = self._get(search_url, params=params)
        if not response:
            print(f"Failed to fetch Glassdoor search results for {query}")
            return jobs

        soup = self._parse_html(response.text)

        # Find job listings
        # Glassdoor uses various selectors for job cards
        job_cards = soup.find_all("li", {"class": "jl"})

        if not job_cards:
            # Fallback selector
            job_cards = soup.find_all("div", {"class": "jobCard"})

        for card in job_cards:
            try:
                # Extract job title
                title_elem = card.find("a", {"class": "jobTitle"})
                title = self.extract_text(title_elem)
                if not title:
                    continue

                # Extract company name
                company_elem = card.find("a", {"class": "employer"})
                company = self.extract_text(company_elem)
                if not company:
                    continue

                # Extract location
                location_elem = card.find("span", {"class": "location"})
                location = self.extract_text(location_elem)

                # Extract job URL
                url_elem = card.find("a", {"class": "jobTitle"})
                job_url = self.extract_attr(url_elem, "href")
                if job_url and not job_url.startswith("http"):
                    job_url = f"{self.base_url}{job_url}"

                # Extract salary if available
                salary_elem = card.find("span", {"class": "salary"})
                salary = self.extract_text(salary_elem)

                # Extract job ID from URL
                job_id = job_url.split("/")[-1] if job_url else ""

                if title and company and job_url:
                    job = self.create_job(
                        job_id=job_id,
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        salary=salary if salary else None,
                    )
                    jobs.append(job)

            except Exception as e:
                print(f"Error parsing Glassdoor job card: {e}")
                continue

        return jobs

    def scrape_job_details(self, job_url: str) -> Job | None:
        """Scrape detailed information for a single job from Glassdoor.

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
                "div", {"class": "jobDescriptionContent"}
            )
            description = self.extract_text(description_elem)

            return None  # Placeholder

        except Exception as e:
            print(f"Error scraping Glassdoor job details from {job_url}: {e}")
            return None
