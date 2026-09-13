"""Job board detection from URL or page content."""

from __future__ import annotations

from enum import Enum
from urllib.parse import urlparse

from selenium import webdriver


class JobBoard(str, Enum):
    """Supported job boards."""

    INDEED = "indeed"
    LINKEDIN = "linkedin"
    GREENHOUSE = "greenhouse"
    WORKABLE = "workable"
    UNKNOWN = "unknown"


def detect_job_board_from_url(url: str) -> JobBoard:
    """Detect job board from a URL.

    Args:
        url: The URL to analyze.

    Returns:
        The detected JobBoard enum value.
    """
    parsed = urlparse(url.lower())
    domain = parsed.netloc

    if "indeed.com" in domain:
        return JobBoard.INDEED
    elif "linkedin.com" in domain:
        return JobBoard.LINKEDIN
    elif "greenhouse.io" in domain or "greenhouse" in domain:
        return JobBoard.GREENHOUSE
    elif "workable.com" in domain:
        return JobBoard.WORKABLE
    else:
        return JobBoard.UNKNOWN


def detect_job_board_from_driver(driver: webdriver.Chrome) -> JobBoard:
    """Detect job board from the current page in the driver.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        The detected JobBoard enum value.
    """
    current_url = driver.current_url
    return detect_job_board_from_url(current_url)


def get_job_title_from_page(driver: webdriver.Chrome) -> str | None:
    """Extract the job title from the current page.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        The job title if found, None otherwise.
    """
    try:
        # Try common title patterns
        title_element = driver.find_element("tag name", "h1")
        if title_element:
            return title_element.text
    except Exception:
        pass

    try:
        # Fallback to page title
        return driver.title
    except Exception:
        return None


def get_company_name_from_page(driver: webdriver.Chrome) -> str | None:
    """Extract the company name from the current page.

    Args:
        driver: The Selenium WebDriver instance.

    Returns:
        The company name if found, None otherwise.
    """
    try:
        # Try to find a company link or header
        company_element = driver.find_element("class name", "company")
        if company_element:
            return company_element.text
    except Exception:
        pass

    return None
