"""Load profile and answers from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from job_automation.profile.models import Answers, Profile


class ProfileLoader:
    """Load and cache profile and answers data."""

    def __init__(
        self,
        profile_path: Optional[Path | str] = None,
        answers_path: Optional[Path | str] = None,
    ):
        """Initialize the loader.

        Args:
            profile_path: Path to profile.json. Defaults to ~/.job-automation/profile.json
            answers_path: Path to answers.json. Defaults to ~/.job-automation/answers.json
        """
        if profile_path is None:
            profile_path = Path.home() / ".job-automation" / "profile.json"
        if answers_path is None:
            answers_path = Path.home() / ".job-automation" / "answers.json"

        self.profile_path = Path(profile_path)
        self.answers_path = Path(answers_path)

        self._profile: Optional[Profile] = None
        self._answers: Optional[Answers] = None

    def load_profile(self) -> Profile:
        """Load profile from file.

        Returns:
            The Profile object.

        Raises:
            FileNotFoundError: If profile.json doesn't exist.
            ValueError: If profile.json is invalid.
        """
        if self._profile is not None:
            return self._profile

        if not self.profile_path.exists():
            raise FileNotFoundError(f"Profile file not found: {self.profile_path}")

        with open(self.profile_path) as f:
            data = json.load(f)

        self._profile = Profile(**data)
        return self._profile

    def load_answers(self) -> Answers:
        """Load answers from file.

        Returns:
            The Answers object.

        Raises:
            FileNotFoundError: If answers.json doesn't exist.
            ValueError: If answers.json is invalid.
        """
        if self._answers is not None:
            return self._answers

        if not self.answers_path.exists():
            raise FileNotFoundError(f"Answers file not found: {self.answers_path}")

        with open(self.answers_path) as f:
            data = json.load(f)

        self._answers = Answers(**data)
        return self._answers

    def load_all(self) -> tuple[Profile, Answers]:
        """Load both profile and answers.

        Returns:
            A tuple of (Profile, Answers).
        """
        return self.load_profile(), self.load_answers()

    def get_profile_dict(self) -> dict[str, Any]:
        """Get profile as a dictionary.

        Returns:
            Profile as a dict (useful for form matching).
        """
        profile = self.load_profile()
        return profile.model_dump(exclude_none=True)

    def get_answers_dict(self) -> dict[str, Any]:
        """Get answers as a dictionary.

        Returns:
            Answers as a dict (useful for form matching).
        """
        answers = self.load_answers()
        return answers.model_dump(exclude_none=True)

    def validate_profile(self) -> bool:
        """Check if profile file is valid.

        Returns:
            True if profile is valid, False otherwise.
        """
        try:
            self.load_profile()
            return True
        except Exception:
            return False

    def validate_answers(self) -> bool:
        """Check if answers file is valid.

        Returns:
            True if answers are valid, False otherwise.
        """
        try:
            self.load_answers()
            return True
        except Exception:
            return False


def create_sample_profile(path: Path | str = None) -> None:
    """Create a sample profile.json file.

    Args:
        path: Where to create the sample. Defaults to ~/.job-automation/profile.json
    """
    if path is None:
        path = Path.home() / ".job-automation" / "profile.json"

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    sample_profile = {
        "name": "John Doe",
        "firstName": "John",
        "lastName": "Doe",
        "email": "john@example.com",
        "phone": "555-123-4567",
        "linkedIn": "https://linkedin.com/in/johndoe",
        "github": "https://github.com/johndoe",
        "portfolio": "https://johndoe.com",
        "address": "123 Main St",
        "city": "San Francisco",
        "state": "CA",
        "zip": "94105",
        "country": "United States",
        "resume": "/path/to/resume.pdf",
    }

    with open(path, "w") as f:
        json.dump(sample_profile, f, indent=2)


def create_sample_answers(path: Path | str = None) -> None:
    """Create a sample answers.json file.

    Args:
        path: Where to create the sample. Defaults to ~/.job-automation/answers.json
    """
    if path is None:
        path = Path.home() / ".job-automation" / "answers.json"

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    sample_answers = {
        "whyInterested": "I'm excited about the opportunity to work with cutting-edge technology and contribute to meaningful projects.",
        "whyCompany": "Your company's mission aligns with my values, and I admire your track record of innovation.",
        "experience": "I have 5+ years of experience in full-stack development, with expertise in Python, JavaScript, and cloud technologies.",
        "availability": "2 weeks",
        "workAuthorization": "Yes, I'm a US citizen",
        "sponsorship": "No, I don't require sponsorship",
    }

    with open(path, "w") as f:
        json.dump(sample_answers, f, indent=2)
