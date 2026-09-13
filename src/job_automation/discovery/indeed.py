"""Scraper for Indeed job listings."""

from __future__ import annotations

from urllib.parse import quote, urljoin

from job_automation.models import Job
from job_automation.discovery.scraper_base import BaseScraper


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com job listings."""

    def __init__(self) -> None:
        """Initialize the Indeed scraper."""
        super().__init__(
            source="indeed",
            base_url="https://www.indeed.com",
            delay_between_requests=2.0,  # Be respectful to Indeed
        )

    def search(self, query: str, location: str = "", page: int = 1) -> list[Job]:
        """Search for jobs on Indeed.

        Args:
            query: Job title or keyword
            location: Job location
            page: Page number for pagination (starts at 1)

        Returns:
            List of Job objects
        """
        jobs = []

        # Build search URL
        # Indeed uses 'start' parameter for pagination (0, 10, 20, etc.)
        start = (page - 1) * 10
        search_url = f"{self.base_url}/jobs"
        params = {
            "q": query,
            "l": location,
            "start": start,
            "limit": 10,
        }

        response = self._get(search_url, params=params)
        if not response:
            print(f"Failed to fetch Indeed search results for {query}")
            return jobs

        soup = self._parse_html(response.text)

        # Find job cards on the search results page
        # Indeed's structure uses divs with specific classes for job listings
        job_cards = soup.find_all(
            "div", {"data-tn-component": "organicJob"}
        )

        if not job_cards:
            # Fallback selector in case Indeed changes their structure
            job_cards = soup.find_all("div", {"class": "jobsearch-SerpJobCard"})

        for card in job_cards:
            try:
                # Extract job title
                title_elem = card.find("h2", {"class": "jobCardTitle"})
                if not title_elem:
                    title_elem = card.find("a", {"data-jk": True})
                title = self.extract_text(title_elem)
                if not title:
                    continue

                # Extract company name
                company_elem = card.find("span", {"class": "companyName"})
                if not company_elem:
                    company_elem = card.find(
                        "span", {"data-testid": "company-name"}
                    )
                company = self.extract_text(company_elem)
                if not company:
                    continue

                # Extract location
                location_elem = card.find("div", {"class": "companyLocation"})
                location = self.extract_text(location_elem)

                # Extract job URL
                job_url = ""
                url_elem = card.find("a", {"data-jk": True})
                if url_elem:
                    job_key = url_elem.get("data-jk")
                    if job_key:
                        job_url = f"{self.base_url}/rc/clk?jk={job_key}"

                # Extract salary if available
                salary_elem = card.find("span", {"class": "salary-snippet"})
                salary = self.extract_text(salary_elem)

                # Extract job description snippet
                snippet_elem = card.find(
                    "div", {"class": "job-snippet"}
                )
                description = self.extract_text(snippet_elem)

                if title and company and job_url:
                    job = self.create_job(
                        job_id=job_url.split("jk=")[-1],  # Extract job key
                        title=title,
                        company=company,
                        location=location,
                        url=job_url,
                        salary=salary if salary else None,
                        description=description if description else None,
                    )
                    jobs.append(job)

            except Exception as e:
                print(f"Error parsing job card: {e}")
                continue

        return jobs

    def scrape_job_details(self, job_url: str) -> Job | None:
        """Scrape detailed information for a single job from Indeed.

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
            # Extract full job description
            description_elem = soup.find(
                "div", {"id": "jobDescriptionText"}
            )
            description = self.extract_text(description_elem)

            # Extract other details from the URL if needed
            # For now, return a job object with the description
            # In a full implementation, we'd extract more details

            return None  # Placeholder

        except Exception as e:
            print(f"Error scraping job details from {job_url}: {e}")
            return None
