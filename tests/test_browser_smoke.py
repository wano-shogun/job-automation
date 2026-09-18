"""Run with APPLYPILOT_BROWSER_TEST=1 to exercise Chrome on the local form."""

import os
from pathlib import Path

import pytest
from selenium.webdriver.common.by import By

from job_automation.apply.submitter import JobSubmitter
from job_automation.browser.driver import BrowserDriver


@pytest.mark.skipif(os.environ.get("APPLYPILOT_BROWSER_TEST") != "1", reason="opt-in browser smoke test")
def test_local_form_is_filled_and_never_submitted():
    class DemoLoader:
        def get_profile_dict(self):
            return {"name": "Jane Developer", "email": "jane@example.com", "phone": "555-0100"}

        def get_answers_dict(self):
            return {"experience": "Five years building web apps", "availability": "Two weeks"}

    url = (Path(__file__).parents[1] / "test_form.html").as_uri()
    with BrowserDriver(headless=True) as browser:
        driver = browser.get_driver()
        result = JobSubmitter(driver, DemoLoader()).submit_application(url)
        assert result.status == "ready_for_review"
        assert driver.find_element(By.ID, "firstName").get_attribute("value") == "Jane"
        assert driver.find_element(By.ID, "lastName").get_attribute("value") == "Developer"
        assert driver.find_element(By.ID, "email").get_attribute("value") == "jane@example.com"
        assert result.required_fields_needing_review == []
