"""Selenium WebDriver management for browser automation."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BrowserType(str, Enum):
    """Supported browser types."""

    CHROME = "chrome"
    FIREFOX = "firefox"


class BrowserDriver:
    """Manages Selenium WebDriver lifecycle."""

    def __init__(self, browser_type: BrowserType = BrowserType.CHROME, headless: bool = False):
        """Initialize a browser driver.

        Args:
            browser_type: Type of browser to use (chrome or firefox).
            headless: If True, run browser in headless mode.
        """
        self.browser_type = browser_type
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def start(self) -> webdriver.Chrome:
        """Start the browser driver.

        Returns:
            The Selenium WebDriver instance.
        """
        if self.browser_type == BrowserType.CHROME:
            options = ChromeOptions()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            self.driver = webdriver.Chrome(options=options)
        else:
            raise NotImplementedError(f"Browser {self.browser_type} not yet supported")

        return self.driver

    def stop(self) -> None:
        """Stop the browser driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def get_driver(self) -> webdriver.Chrome:
        """Get the current driver instance.

        Raises:
            RuntimeError: If driver is not running.
        """
        if self.driver is None:
            raise RuntimeError("Driver not started. Call start() first.")
        return self.driver

    def navigate_to(self, url: str) -> None:
        """Navigate to a URL.

        Args:
            url: The URL to navigate to.
        """
        driver = self.get_driver()
        driver.get(url)

    def wait_for_element(
        self, by: By, value: str, timeout: int = 10
    ) -> Optional[webdriver.remote.webelement.WebElement]:
        """Wait for an element to appear on the page.

        Args:
            by: The locator strategy (e.g., By.ID, By.CLASS_NAME).
            value: The locator value.
            timeout: Maximum seconds to wait.

        Returns:
            The WebElement if found, None otherwise.
        """
        driver = self.get_driver()
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception:
            return None

    def __enter__(self) -> BrowserDriver:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.stop()
