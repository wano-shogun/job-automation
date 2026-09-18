"""Browser-based application filling with an explicit submission boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select

from job_automation.adapters import get_adapter
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
        adapter = get_adapter(self.driver.current_url)
        if adapter:
            values = adapter.prepare_values(values)
        role = self._first_text("h1") or self.driver.title or "Unknown role"
        submission = ApplicationSubmission(
            job_id=_job_id_from_url(job_url),
            company=_company_from_url(job_url),
            role=role,
            submitted_at=datetime.now(),
            resume_path=str(resume) if resume else None,
            cover_letter_path=str(cover_letter_path) if cover_letter_path else None,
            screening_answers=supplied_answers,
        )

        for control in self.driver.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
            try:
                self._fill_one(control, values, resume, submission, adapter)
            except Exception as exc:
                submission.required_fields_needing_review.append(
                    f"{self._identity(control, adapter)} ({type(exc).__name__}: {exc})"
                )

        submission.required_fields_needing_review = list(dict.fromkeys(submission.required_fields_needing_review))
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
        if result.required_fields_needing_review or not result.fields_filled:
            result.status = "needs_review"
            if not result.fields_filled:
                result.notes = "No application fields were filled. Check that this is an application form."
        else:
            result.status = "ready_for_review"
        if not submit or result.status != "ready_for_review":
            return result
        button = self._submit_button()
        if button is None:
            result.status = "needs_review"
            result.notes = "No enabled submit button found."
            return result
        previous_url = self.driver.current_url
        previous_text = self.driver.find_element(By.TAG_NAME, "body").text.casefold()
        button.click()
        try:
            WebDriverWait(self.driver, 10).until(
                lambda driver: _submission_confirmed(driver, previous_url, previous_text)
            )
            result.status = "submitted"
        except Exception:
            result.status = "submission_unconfirmed"
            result.notes = "Submit was clicked, but the site did not show a confirmation. Check the browser before retrying."
        return result

    def save_submission_record(self, submission: ApplicationSubmission) -> Application:
        """Return a tracker record for a browser submission result."""
        if submission.status != "submitted":
            raise ValueError("Only confirmed submissions can be recorded as applied")
        return Application(
            company=submission.company,
            role=submission.role,
            status=ApplicationStatus.APPLIED,
            notes=submission.notes or f"Browser status: {submission.status}",
        )

    def _fill_one(self, control: Any, values: dict[str, str], resume: Path | None, result: ApplicationSubmission, adapter: Any | None = None) -> None:
        input_type = (control.get_attribute("type") or "").casefold()
        if not control.is_enabled():
            return
        if input_type != "file" and not control.is_displayed():
            return
        if input_type in {"hidden", "submit", "button", "reset"}:
            return
        identity = self._identity(control, adapter)
        required = bool(control.get_attribute("required")) or control.get_attribute("aria-required") == "true"
        if input_type == "file":
            if resume and self._looks_like_resume(identity):
                control.send_keys(str(resume.resolve()))
                result.fields_filled.append(identity)
            elif required:
                result.required_fields_needing_review.append(identity)
            return
        if input_type in {"checkbox", "radio"}:
            answer = self._lookup_value(identity, values)
            if answer is not None:
                if self._fill_choice(control, answer):
                    result.fields_filled.append(identity)
                elif required:
                    result.required_fields_needing_review.append(identity)
            elif required:
                result.required_fields_needing_review.append(identity)
            return
        value = self._lookup_value(identity, values)
        if value is None:
            if required:
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

    def _identity(self, control: Any, adapter: Any | None = None) -> str:
        control_id = control.get_attribute("id") or ""
        label = ""
        if control_id:
            try:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{control_id}']").text
            except Exception:
                pass
        parts = [label, control.get_attribute("aria-label") or "", control.get_attribute("placeholder") or "", control.get_attribute("name") or "", control_id]
        fallback = " ".join(part for part in parts if part).strip() or "unnamed field"
        return adapter.identity(self.driver, control, fallback) if adapter else fallback

    @staticmethod
    def _looks_like_resume(identity: str) -> bool:
        return any(word in identity.casefold() for word in ("resume", "cv", "curriculum vitae"))

    @staticmethod
    def _lookup_value(identity: str, values: dict[str, str]) -> str | None:
        normal = _normalise_key(identity)
        if normal in values:
            return values[normal]
        # Only match a complete label, id, or name token. Substring matching
        # confuses fields such as "statement" with "state".
        for key in sorted(values, key=len, reverse=True):
            if len(key) > 3 and re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", identity.casefold()):
                return values[key]
        return None

    @staticmethod
    def _fill_choice(control: Any, value: str) -> bool:
        expected = value.casefold().strip()
        option = (control.get_attribute("value") or "").casefold().strip()
        is_match = (expected in {"yes", "true", "1", "on"} and option in {"yes", "true", "1", "on"}) or (expected in {"no", "false", "0", "off"} and option in {"no", "false", "0", "off"})
        if is_match and not control.is_selected():
            control.click()
        return is_match

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
    parsed = urlparse(url)
    host = parsed.netloc.removeprefix("www.")
    if host == "jobs.ashbyhq.com":
        board = parsed.path.strip("/").split("/")[0]
        return unquote(board).replace("-", " ").title() or "Unknown company"
    return host.split(".")[0].replace("-", " ").title() or "Unknown company"


def _job_id_from_url(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    if parts and parts[-1].casefold() in {"application", "apply"}:
        parts.pop()
    return parts[-1] if parts else urlparse(url).netloc


def _submission_confirmed(driver: Any, previous_url: str, previous_text: str) -> bool:
    """Accept only an explicit success signal after a final submit click."""
    current = driver.current_url.casefold()
    if current != previous_url.casefold() and any(word in current for word in ("thank", "success", "confirmation", "submitted")):
        return True
    text = (driver.find_element(By.TAG_NAME, "body").text or "").casefold()
    return any(
        phrase in text and phrase not in previous_text
        for phrase in (
            "application submitted",
            "application received",
            "thank you for applying",
            "thanks for applying",
        )
    )
