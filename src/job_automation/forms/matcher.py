"""Match form fields to user profile and answer data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from job_automation.forms.parser import FieldType, FormField


@dataclass
class FieldMatch:
    """A matched form field with a suggested value."""

    form_field: FormField
    matched_key: Optional[str]  # The key from profile/answers that matched
    suggested_value: Optional[str]  # The value to fill
    confidence: float  # 0.0 to 1.0, how sure we are about this match
    reason: str  # Why this match was made

    def __repr__(self) -> str:
        """Return a readable representation."""
        return (
            f"FieldMatch(field={self.form_field.name}, key={self.matched_key}, "
            f"confidence={self.confidence}, reason={self.reason})"
        )


class FormMatcher:
    """Match form fields to profile/answer data."""

    def __init__(self, profile: dict[str, Any], answers: dict[str, Any]):
        """Initialize the matcher with profile and answers.

        Args:
            profile: Profile data (name, email, phone, etc.).
            answers: Answers to common questions.
        """
        self.profile = profile
        self.answers = answers
        self._field_mappings = self._build_field_mappings()

    def _build_field_mappings(self) -> dict[str, list[str]]:
        """Build keyword mappings for common field types.

        Returns:
            A dict mapping field keywords to profile/answer keys.
        """
        return {
            "name": ["name", "fullName", "full_name"],
            "firstName": ["firstName", "first_name"],
            "lastName": ["lastName", "last_name"],
            "email": ["email"],
            "phone": ["phone", "phoneNumber", "phone_number"],
            "address": ["address", "street", "city", "state", "zip"],
            "linkedIn": ["linkedin", "linkedin_url"],
            "github": ["github", "github_url"],
            "portfolio": ["portfolio", "portfolio_url", "website"],
            "resume": ["resume"],
            "coverLetter": ["cover_letter", "coverLetter"],
        }

    def match_field(self, field: FormField) -> FieldMatch:
        """Match a single form field to profile/answer data.

        Args:
            field: The FormField to match.

        Returns:
            A FieldMatch with suggested value and confidence.
        """
        # Normalize the field name/label for matching
        search_terms = self._normalize_field_name(field.name, field.label)

        # Try to find a match in profile or answers
        best_match = None
        best_confidence = 0.0
        best_reason = ""

        # Check profile data
        for search_term in search_terms:
            for key, pattern_list in self._field_mappings.items():
                if search_term.lower() in [p.lower() for p in pattern_list]:
                    if key in self.profile:
                        value = self.profile[key]
                        confidence = self._calculate_confidence(field, key, value)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = (key, value, f"Matched field '{field.name}' to profile key '{key}'")

        # Check answers data
        for search_term in search_terms:
            if search_term.lower() in self.answers:
                value = self.answers[search_term.lower()]
                confidence = 0.85  # Answers are generally high confidence
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = (search_term, value, f"Matched field '{field.name}' to answer '{search_term}'")

        if best_match:
            matched_key, value, reason = best_match
            return FieldMatch(
                form_field=field,
                matched_key=matched_key,
                suggested_value=str(value),
                confidence=best_confidence,
                reason=reason,
            )
        else:
            return FieldMatch(
                form_field=field,
                matched_key=None,
                suggested_value=None,
                confidence=0.0,
                reason=f"No match found for field '{field.name}'",
            )

    def match_fields(self, fields: list[FormField]) -> list[FieldMatch]:
        """Match multiple form fields.

        Args:
            fields: List of FormField objects.

        Returns:
            List of FieldMatch objects.
        """
        return [self.match_field(field) for field in fields]

    def _normalize_field_name(self, name: str, label: Optional[str]) -> list[str]:
        """Normalize a field name and label into search terms.

        Args:
            name: The field's name attribute.
            label: The field's label text.

        Returns:
            List of search terms to try.
        """
        terms = []

        # Add the name and label
        if name:
            terms.extend(name.split("_"))
            terms.extend(name.split("-"))

        if label:
            terms.extend(label.lower().split())

        # Clean up terms
        terms = [t.strip().lower() for t in terms if t.strip()]
        return list(dict.fromkeys(terms))  # Remove duplicates while preserving order

    def _calculate_confidence(self, field: FormField, key: str, value: Any) -> float:
        """Calculate confidence for a match based on field type and data.

        Args:
            field: The FormField.
            key: The matched profile key.
            value: The value from profile.

        Returns:
            Confidence score from 0.0 to 1.0.
        """
        confidence = 0.8

        # Boost confidence for type matches
        if field.field_type == FieldType.EMAIL and key == "email":
            confidence = 0.95
        elif field.field_type == FieldType.PHONE and "phone" in key.lower():
            confidence = 0.95
        elif field.field_type == FieldType.TEXTAREA and key in ["coverLetter", "cover_letter"]:
            confidence = 0.9

        # Check if value is non-empty
        if not value:
            confidence *= 0.5

        return confidence
