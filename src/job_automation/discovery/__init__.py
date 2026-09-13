"""Job discovery module for scraping job listings from multiple sources."""

from job_automation.discovery.scraper_base import BaseScraper
from job_automation.discovery.indeed import IndeedScraper
from job_automation.discovery.linkedin import LinkedInScraper
from job_automation.discovery.glassdoor import GlassdoorScraper
from job_automation.discovery.ziprecruiter import ZipRecruiterScraper
from job_automation.discovery.google_jobs import GoogleJobsScraper

__all__ = [
    "BaseScraper",
    "IndeedScraper",
    "LinkedInScraper",
    "GlassdoorScraper",
    "ZipRecruiterScraper",
    "GoogleJobsScraper",
]
