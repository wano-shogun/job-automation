from unittest.mock import Mock

import pytest

from job_automation.apply.submitter import ApplicationSubmission, JobSubmitter, _submission_confirmed
from job_automation.discovery.ashby import search_ashby_board


def test_ashby_discovery_returns_direct_listed_application_urls():
    response = Mock()
    response.json.return_value = {
        "jobs": [
            {
                "title": "Director of Engineering",
                "descriptionPlain": "Leads a Full Stack Developer team",
                "location": "Toronto, Canada",
                "isRemote": True,
                "isListed": True,
                "applyUrl": "https://jobs.ashbyhq.com/example/director/application",
            },
            {
                "title": "Senior Full Stack Developer",
                "descriptionPlain": "Build Python and React services",
                "location": "Toronto, Canada",
                "isRemote": True,
                "isListed": True,
                "applyUrl": "https://jobs.ashbyhq.com/example/abc/application",
            },
            {
                "title": "Senior Full Stack Developer",
                "descriptionPlain": "Build Python and React services",
                "location": "Toronto, Canada",
                "isRemote": True,
                "isListed": False,
                "applyUrl": "https://jobs.ashbyhq.com/example/private/application",
            },
        ]
    }
    session = Mock()
    session.get.return_value = response

    jobs = search_ashby_board("example", "Full Stack", "Remote", session=session)

    assert len(jobs) == 1
    assert jobs[0].url == "https://jobs.ashbyhq.com/example/abc/application"
    assert jobs[0].job_id == "abc"


def test_field_matching_does_not_confuse_state_with_statement():
    assert JobSubmitter._lookup_value("Personal statement", {"state": "CA"}) is None
    assert JobSubmitter._lookup_value("First Name firstName", {"firstname": "Jane", "name": "Jane Dev"}) == "Jane"


def test_unconfirmed_application_cannot_be_tracked_as_applied():
    from datetime import datetime

    submitter = JobSubmitter(Mock())
    result = ApplicationSubmission(job_id="1", company="Example", role="Developer", submitted_at=datetime.now(), status="submission_unconfirmed")
    with pytest.raises(ValueError, match="confirmed"):
        submitter.save_submission_record(result)


def test_empty_fill_cannot_trigger_submission():
    from datetime import datetime

    submitter = JobSubmitter(Mock())
    submitter.fill_application = Mock(return_value=ApplicationSubmission(
        job_id="1", company="Example", role="Developer", submitted_at=datetime.now()
    ))
    submitter._submit_button = Mock()

    result = submitter.submit_application("https://example.com/apply", submit=True)

    assert result.status == "needs_review"
    submitter._submit_button.assert_not_called()


def test_fresh_required_field_blocks_final_click():
    from datetime import datetime

    driver = Mock(current_url="https://jobs.ashbyhq.com/example/abc/application")
    submitter = JobSubmitter(driver)
    submitter._unfilled_required = Mock(return_value=["New required question"])
    submitter._submit_button = Mock()
    result = ApplicationSubmission(
        job_id="abc", company="Example", role="Developer",
        submitted_at=datetime.now(), status="ready_for_review", fields_filled=["Name"],
    )

    submitter.submit_filled_application(result)

    assert result.status == "needs_review"
    assert result.required_fields_needing_review == ["New required question"]
    submitter._submit_button.assert_not_called()


def test_existing_thank_you_text_is_not_a_submission_confirmation():
    from selenium.webdriver.common.by import By

    driver = Mock(current_url="https://example.com/apply")
    driver.find_element.return_value.text = "Thank you for applying. Application form below."
    assert not _submission_confirmed(driver, driver.current_url, driver.find_element(By.TAG_NAME, "body").text.casefold())
