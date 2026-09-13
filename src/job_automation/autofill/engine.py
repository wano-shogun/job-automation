"""Main autofill engine that orchestrates the form filling process."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By

from job_automation.browser.detectors import detect_job_board_from_driver, JobBoard
from job_automation.forms.matcher import FieldMatch, FormMatcher
from job_automation.forms.parser import FieldType, Form, parse_forms_from_page
from job_automation.profile.loader import ProfileLoader


@dataclass
class AutofillPlan:
    """A plan for auto-filling a form."""

    job_board: JobBoard
    form: Form
    field_matches: list[FieldMatch]
    fillable_count: int
    confidence_score: float

    def get_fillable_matches(self) -> list[FieldMatch]:
        """Get only the matches we should fill (high confidence).

        Returns:
            List of FieldMatch with confidence >= 0.7.
        """
        return [m for m in self.field_matches if m.confidence >= 0.7]

    def __repr__(self) -> str:
        """Return a readable representation."""
        return (
            f"AutofillPlan(job_board={self.job_board}, fillable={self.fillable_count}, "
            f"confidence={self.confidence_score:.2f})"
        )


class AutofillEngine:
    """Main engine for job application autofill."""

    def __init__(self, profile_loader: ProfileLoader, driver: webdriver.Chrome):
        """Initialize the autofill engine.

        Args:
            profile_loader: ProfileLoader instance for getting profile/answers.
            driver: Selenium WebDriver instance.
        """
        self.profile_loader = profile_loader
        self.driver = driver
        self.matcher: Optional[FormMatcher] = None

    def create_autofill_plan(self) -> AutofillPlan:
        """Analyze the current page and create an autofill plan.

        This does NOT fill the form - it just creates a plan for review.

        Returns:
            An AutofillPlan with suggestions.
        """
        # Detect which job board we're on
        job_board = detect_job_board_from_driver(self.driver)

        # Parse forms from the page
        forms = parse_forms_from_page(self.driver)
        if not forms:
            raise ValueError("No forms found on the current page")

        # Use the first form (most job applications have one main form)
        form = forms[0]

        # Load profile and answers
        profile_dict = self.profile_loader.get_profile_dict()
        answers_dict = self.profile_loader.get_answers_dict()

        # Create matcher
        self.matcher = FormMatcher(profile_dict, answers_dict)

        # Match all form fields
        field_matches = self.matcher.match_fields(form.fields)

        # Calculate plan metrics
        fillable_matches = [m for m in field_matches if m.confidence >= 0.7]
        fillable_count = len(fillable_matches)
        confidence_score = (
            sum(m.confidence for m in fillable_matches) / len(fillable_matches)
            if fillable_matches
            else 0.0
        )

        return AutofillPlan(
            job_board=job_board,
            form=form,
            field_matches=field_matches,
            fillable_count=fillable_count,
            confidence_score=confidence_score,
        )

    def fill_form(self, plan: AutofillPlan) -> None:
        """Fill the form according to the plan.

        Args:
            plan: The AutofillPlan to execute.

        Raises:
            ValueError: If unable to fill a field.
        """
        fillable = plan.get_fillable_matches()

        for match in fillable:
            field = match.form_field
            value = match.suggested_value

            if not value or not field.element_id:
                continue

            try:
                element = self.driver.find_element(By.ID, field.element_id)
                self._fill_field(element, field, value)
            except Exception as e:
                # Log the error but continue with other fields
                print(f"Warning: Failed to fill field {field.name}: {e}")

    def _fill_field(self, element, field, value: str) -> None:
        """Fill a single form field.

        Args:
            element: The WebElement to fill.
            field: The FormField definition.
            value: The value to fill.
        """
        if field.field_type == FieldType.SELECT:
            # For select dropdowns, find and click the option
            from selenium.webdriver.support.select import Select

            select = Select(element)
            try:
                select.select_by_value(value)
            except Exception:
                # Try by visible text
                select.select_by_visible_text(value)

        elif field.field_type == FieldType.CHECKBOX:
            # Check the checkbox if the value indicates yes
            if value.lower() in ("yes", "true", "1", "on"):
                if not element.is_selected():
                    element.click()

        elif field.field_type == FieldType.RADIO:
            # Click the radio button
            element.click()

        elif field.field_type in (FieldType.TEXT, FieldType.EMAIL, FieldType.PHONE, FieldType.TEXTAREA):
            # Clear and fill text fields
            element.clear()
            element.send_keys(value)

        else:
            # Default: just send keys
            element.clear()
            element.send_keys(value)

    def print_plan(self, plan: AutofillPlan) -> None:
        """Print a human-readable plan for review.

        Args:
            plan: The AutofillPlan to print.
        """
        print(f"\n{'='*60}")
        print(f"AUTOFILL PLAN")
        print(f"{'='*60}")
        print(f"Job Board: {plan.job_board.value}")
        print(f"Form ID: {plan.form.form_id}")
        print(f"Total Fields: {len(plan.form.fields)}")
        print(f"Fillable Fields: {plan.fillable_count}")
        print(f"Average Confidence: {plan.confidence_score:.2%}")
        print(f"\n{'-'*60}")
        print("FIELD MATCHES:")
        print(f"{'-'*60}")

        for match in plan.field_matches:
            status = "✓ FILL" if match.confidence >= 0.7 else "✗ SKIP"
            print(f"\n{status} | {match.form_field.name}")
            print(f"    Label: {match.form_field.label}")
            print(f"    Type: {match.form_field.field_type.value}")
            if match.suggested_value:
                print(f"    Value: {match.suggested_value[:50]}...")
            print(f"    Confidence: {match.confidence:.2%}")
            print(f"    Reason: {match.reason}")

        print(f"\n{'='*60}")
        print("Review the plan above, then run 'autofill execute' to fill the form.")
        print("You will review the filled form before submission.")
        print(f"{'='*60}\n")
