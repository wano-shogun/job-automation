"""Submit job applications automatically."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_automation.models import Application, ApplicationStatus


@dataclass
class ApplicationSubmission:
    """Record of a submitted application."""

    job_id: str
    company: str
    role: str
    submitted_at: datetime
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    screening_answers: dict = None
    status: str = "submitted"
    notes: str = ""


class JobSubmitter:
    """Submit job applications."""

    def __init__(self, browser_driver=None) -> None:
        """Initialize submitter.

        Args:
            browser_driver: Selenium WebDriver for form submission
        """
        self.driver = browser_driver
        self.submissions: list[ApplicationSubmission] = []

    def submit_application(
        self,
        job_url: str,
        resume_path: str | Path,
        cover_letter_path: Optional[str | Path] = None,
        screening_answers: Optional[dict] = None,
        auto_review: bool = False,
    ) -> ApplicationSubmission:
        """Submit a job application.

        Args:
            job_url: URL to job posting
            resume_path: Path to resume file
            cover_letter_path: Optional path to cover letter
            screening_answers: Answers to screening questions
            auto_review: Auto-review before submitting

        Returns:
            ApplicationSubmission record
        """
        if not self.driver:
            raise ValueError("No browser driver configured")

        submission = ApplicationSubmission(
            job_id=job_url.split("/")[-1],
            company="Unknown",  # Parse from page
            role="Unknown",  # Parse from page
            submitted_at=datetime.now(),
            resume_path=str(resume_path),
            cover_letter_path=str(cover_letter_path) if cover_letter_path else None,
            screening_answers=screening_answers or {},
        )

        # Navigate to job
        self.driver.get(job_url)

        # Parse job details
        # ... form filling logic ...

        # Submit
        # ... submission logic ...

        self.submissions.append(submission)
        return submission

    def submit_batch(
        self,
        jobs_with_docs: list[tuple],
        screening_answerer=None,
    ) -> list[ApplicationSubmission]:
        """Submit applications for multiple jobs.

        Args:
            jobs_with_docs: List of (job, resume_path, cover_letter_path)
            screening_answerer: Optional screening question answerer

        Returns:
            List of submission records
        """
        results = []
        for job, resume, cover_letter in jobs_with_docs:
            try:
                answers = {}
                if screening_answerer:
                    answers = screening_answerer.answer_screening_questions(job)

                submission = self.submit_application(
                    job.url,
                    resume,
                    cover_letter,
                    answers,
                )
                results.append(submission)

            except Exception as e:
                print(f"Error submitting to {job.company}: {e}")
                continue

        return results

    def save_submission_record(self, submission: ApplicationSubmission) -> Application:
        """Save submission to application tracker.

        Args:
            submission: Application submission

        Returns:
            Application record
        """
        return Application(
            company=submission.company,
            role=submission.role,
            status=ApplicationStatus.APPLIED,
            url=f"https://example.com",  # Parse from submission
            notes=(
                f"Auto-submitted. Resume: {submission.resume_path}. "
                f"Cover Letter: {submission.cover_letter_path}"
            ),
        )
