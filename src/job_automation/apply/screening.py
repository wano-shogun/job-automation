"""Answer screening questions using Claude."""

from __future__ import annotations

from anthropic import Anthropic

from job_automation.models import Job
from job_automation.profile.models import Profile


class ScreeningAnswerer:
    """Answer screening questions intelligently."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize answerer."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def answer_screening_questions(
        self, job: Job, profile: Profile, questions: list[str] | None = None
    ) -> dict[str, str]:
        """Answer screening questions for a job.

        Args:
            job: Target job
            profile: User profile
            questions: Optional list of specific questions

        Returns:
            Dictionary mapping questions to answers
        """
        if not questions:
            # Common screening questions
            questions = [
                "Why are you interested in this position?",
                "What experience do you have with the required technologies?",
                "Why do you want to work at this company?",
                "What are your salary expectations?",
                "When can you start?",
            ]

        answers = {}

        for question in questions:
            prompt = f"""Answer this screening question based on the candidate profile.

CANDIDATE:
Name: {profile.name}
Experience: {profile.years_of_experience} years
Skills: {', '.join(profile.skills)}
Target Role: {profile.target_role}

JOB:
Title: {job.title}
Company: {job.company}

QUESTION: {question}

Provide a concise, honest answer (1-2 sentences) that's suitable for a screening question."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )

            answers[question] = response.content[0].text

        return answers

    def validate_answers(self, answers: dict[str, str]) -> dict[str, bool]:
        """Validate if answers are appropriate.

        Args:
            answers: Dictionary of question: answer pairs

        Returns:
            Validation results
        """
        results = {}

        for question, answer in answers.items():
            prompt = f"""Is this a good answer to a job screening question?

QUESTION: {question}
ANSWER: {answer}

Respond with yes or no, and explain why."""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            is_valid = "yes" in response.content[0].text.lower()[:10]
            results[question] = is_valid

        return results
