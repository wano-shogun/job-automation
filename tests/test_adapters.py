from job_automation.adapters import get_adapter
from job_automation.browser.detectors import JobBoard, detect_job_board_from_url


def test_detects_ashby_and_selects_adapter():
    url = "https://jobs.ashbyhq.com/example/123/application"
    assert detect_job_board_from_url(url) is JobBoard.ASHBY
    adapter = get_adapter(url)
    assert adapter is not None
    assert adapter.name == "ashby"


def test_ashby_adds_location_and_system_field_aliases():
    adapter = get_adapter("https://jobs.ashbyhq.com/example/123/application")
    values = adapter.prepare_values(
        {"name": "John Developer", "email": "john@example.com", "city": "Toronto", "state": "ON"}
    )
    assert values["currentlocation"] == "Toronto, ON"
    assert values["_systemfieldname"] == "John Developer"
    assert values["_systemfieldemail"] == "john@example.com"


def test_unknown_site_uses_generic_fallback():
    assert get_adapter("https://careers.example.com/apply") is None
