"""Browser-based application filling with an explicit submission boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

from job_automation.models import Application, ApplicationStatus
from job_automation.profile.loader import ProfileLoader


@dataclass
class ApplicationSubmission:
    """A browser-fill result and, optionally, an actual submission."""

    job_id: str
    company: str
    role: str
    submitted_at: datetime
    resume_path: str | None = None
    cover_letter_path: str | None = None
    screening_answers: dict[str, str] = field(default_factory=dict)
    status: str = "filled"
    notes: str = ""
    fields_filled: list[str] = field(default_factory=list)
    required_fields_needing_review: list[str] = field(default_factory=list)


class JobSubmitter:
    """Fill common ATS controls in a live Selenium browser.

    ``fill_application`` never sends an application. A caller must request the
    final browser click with ``submit=True``.
    """

    def __init__(self, browser_driver: Any, profile_loader: ProfileLoader | None = None) -> None:
        if browser_driver is None:
            raise ValueError("A running Selenium browser driver is required")
        self.driver = browser_driver
        self.profile_loader = profile_loader or ProfileLoader()
        self.submissions: list[ApplicationSubmission] = []

    def fill_application(
        self,
        job_url: str,
        resume_path: str | Path | None = None,
        cover_letter_path: str | Path | None = None,
        screening_answers: dict[str, str] | None = None,
    ) -> ApplicationSubmission:
        """Open a job URL and fill recognised fields without submitting."""
        profile = self.profile_loader.get_profile_dict()
        answers = self.profile_loader.get_answers_dict()
        supplied_answers = screening_answers or {}
        values = _normalise_values({**profile, **answers, **supplied_answers})

        if resume_path is None:
            resume_path = profile.get("resume")
        resume = Path(resume_path).expanduser() if resume_path else None
        if resume and not resume.is_file():
            raise FileNotFoundError(f"Resume file not found: {resume}")

        self.driver.get(job_url)
        self._wait_for_document()
        role = self._first_text("h1") or self.driver.title or "Unknown role"
        submission = ApplicationSubmission(
            job_id=job_url.rstrip("/").split("/")[-1] or urlparse(job_url).netloc,
            company=_company_from_url(job_url),
            role=role,
            submitted_at=datetime.now(),
            resume_path=str(resume) if resume else None,
            cover_letter_path=str(cover_letter_path) if cover_letter_path else None,
            screening_answers=supplied_answers,
        )

        for control in self.driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
            try:
                self._fill_one(control, values, resume, submission)
            except Exception as exc:
                if control.get_attribute("required"):
                    submission.required_fields_needing_review.append(
                        f"{self._identity(control)} ({exc})"
                    )

        if cover_letter_path:
            submission.notes = f"Cover letter prepared at {cover_letter_path}; attach it if the site asks."
        self.submissions.append(submission)
        return submission

    def submit_application(
        self,
        job_url: str,
        resume_path: str | Path | None = None,
        cover_letter_path: str | Path | None = None,
        screening_answers: dict[str, str] | None = None,
        *,
        submit: bool = False,
    ) -> ApplicationSubmission:
        """Fill an application and only send it when ``submit=True``."""
        result = self.fill_application(job_url, resume_path, cover_letter_path, screening_answers)
        if not submit:
            result.status = "ready_for_review"
            return result
        if result.required_fields_needing_review:
            result.status = "needs_review"
            result.notes = "Required fields still need review: " + ", ".join(result.required_fields_needing_review)
            return result
        button = self._submit_button()
        if button is None:
            result.status = "needs_review"
            result.notes = "No enabled submit button found."
            return result
        button.click()
        result.status = "submitted"
        return result

    def save_submission_record(self, submission: ApplicationSubmission) -> Application:
        """Return a tracker record for a browser submission result."""
        return Application(
            company=submission.company,
            role=submission.role,
            status=ApplicationStatus.APPLIED,
            notes=submission.notes or f"Browser status: {submission.status}",
        )

    def _fill_one(self, control: Any, values: dict[str, str], resume: Path | None, result: ApplicationSubmission) -> None:
        if not control.is_displayed() or not control.is_enabled():
            return
        input_type = (control.get_attribute("type") or "").casefold()
        if input_type in {"hidden", "submit", "button", "reset"}:
            return
        identity = self._identity(control)
        if input_type == "file":
            if resume and self._looks_like_resume(identity):
                control.send_keys(str(resume.resolve()))
                result.fields_filled.append(identity)
            elif control.get_attribute("required"):
                result.required_fields_needing_review.append(identity)
            return
        if input_type in {"checkbox", "radio"}:
            answer = self._lookup_value(identity, values)
            if answer is not None:
                self._fill_choice(control, answer)
                result.fields_filled.append(identity)
            elif control.get_attribute("required"):
                result.required_fields_needing_review.append(identity)
            return
        value = self._lookup_value(identity, values)
        if value is None:
            if control.get_attribute("required"):
                result.required_fields_needing_review.append(identity)
            return
        self._fill_control(control, value)
        result.fields_filled.append(identity)

    def _wait_for_document(self) -> None:
        WebDriverWait(self.driver, 15).until(
            lambda driver: driver.execute_script("return document.readyState !== 'loading';")
            and len(driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")) > 0
        )

    def _first_text(self, selector: str) -> str | None:
        try:
            text = self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
            return text or None
        except Exception:
            return None

    def _identity(self, control: Any) -> str:
        control_id = control.get_attribute("id") or ""
        label = ""
        if control_id:
            try:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{control_id}']").text
            except Exception:
                pass
        parts = [label, control.get_attribute("aria-label") or "", control.get_attribute("placeholder") or "", control.get_attribute("name") or "", control_id]
        return " ".join(part for part in parts if part).strip() or "unnamed field"

    @staticmethod
    def _looks_like_resume(identity: str) -> bool:
        return any(word in identity.casefold() for word in ("resume", "cv", "curriculum vitae"))

    @staticmethod
    def _lookup_value(identity: str, values: dict[str, str]) -> str | None:
        normal = _normalise_key(identity)
        if normal in values:
            return values[normal]
        # Check longer keys first: "firstname" must win over the generic
        # "name" when both appear in a combined label/name/id identity.
        for key in sorted(values, key=len, reverse=True):
            value = values[key]
            if len(key) > 3 and (key in normal or normal in key):
                return value
        return None

    @staticmethod
    def _fill_choice(control: Any, value: str) -> None:
        expected = value.casefold().strip()
        option = (control.get_attribute("value") or "").casefold().strip()
        is_match = (expected in {"yes", "true", "1", "on"} and option in {"yes", "true", "1", "on"}) or (expected in {"no", "false", "0", "off"} and option in {"no", "false", "0", "off"})
        if is_match and not control.is_selected():
            control.click()

    @staticmethod
    def _fill_control(control: Any, value: str) -> None:
        if control.tag_name.casefold() == "select":
            select = Select(control)
            try:
                select.select_by_visible_text(value)
            except Exception:
                select.select_by_value(value)
            return
        control.clear()
        control.send_keys(value)

    def _submit_button(self) -> Any | None:
        for selector in ("button[type='submit']", "input[type='submit']", "button"):
            for button in self.driver.find_elements(By.CSS_SELECTOR, selector):
                text = (button.text or button.get_attribute("value") or "").casefold()
                if button.is_displayed() and button.is_enabled() and "submit" in text:
                    return button
        return None


def _normalise_key(value: str) -> str:
    return "".join(char for char in value.casefold() if char.isalnum())


def _normalise_values(values: dict[str, Any]) -> dict[str, str]:
    normalised = {
        _normalise_key(key): str(value)
        for key, value in values.items()
        if value not in (None, "", [], {})
    }
    # Profiles commonly keep only a full name. Native ATS forms frequently
    # split that value into two required fields, so derive them when they were
    # not supplied explicitly.
    name = normalised.get("name", "").split()
    if name:
        normalised.setdefault("firstname", name[0])
        if len(name) > 1:
            normalised.setdefault("lastname", " ".join(name[1:]))
    return normalised


def _company_from_url(url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    return host.split(".")[0].replace("-", " ").title() or "Unknown company"
