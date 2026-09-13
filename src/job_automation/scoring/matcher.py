"""Job-to-profile matching for skill and requirement analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic

from job_automation.models import Job
from job_automation.profile.models import Profile


@dataclass
class MatchResult:
    """Result of matching a job to a user profile."""

    job_id: str
    job_title: str
    company: str
    match_score: int  # 1-10
    matched_skills: list[str]  # Skills user has that job wants
    missing_skills: list[str]  # Skills job wants that user lacks
    reasoning: str
    key_requirements: list[str]  # Top 3 job requirements
    salary_range: str | None = None


class JobMatcher:
    """Matches jobs to user profiles using heuristics and Claude API."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the job matcher.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.conversation_history: list[dict[str, str]] = []

    def extract_requirements(self, job: Job) -> dict[str, Any]:
        """Extract requirements from a job description using Claude.

        Args:
            job: Job object to analyze

        Returns:
            Dictionary with extracted requirements
        """
        if not job.description:
            return {
                "skills": [],
                "experience_level": "Unknown",
                "years_required": 0,
                "key_responsibilities": [],
                "nice_to_have": [],
            }

        # Build context for Claude
        prompt = f"""Analyze this job posting and extract key requirements:

Job Title: {job.title}
Company: {job.company}
Description: {job.description}

Extract and return:
1. Required skills (programming languages, tools, frameworks, etc)
2. Experience level (Junior, Mid, Senior, Lead)
3. Years of experience required
4. Key responsibilities
5. Nice-to-have skills

Format as a structured analysis."""

        self.conversation_history.append({"role": "user", "content": prompt})

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=self.conversation_history,
        )

        assistant_message = response.content[0].text
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )

        # Parse Claude's response
        return self._parse_requirements(assistant_message)

    def match_job_to_profile(self, job: Job, profile: Profile) -> MatchResult:
        """Match a job to a user profile.

        Args:
            job: Job to evaluate
            profile: User profile with skills and experience

        Returns:
            MatchResult with score and analysis
        """
        # Extract job requirements
        requirements = self.extract_requirements(job)

        # Ask Claude to score the match
        prompt = f"""Score how well this candidate matches this job (1-10 scale):

Candidate Profile:
- Skills: {', '.join(profile.skills)}
- Experience: {profile.years_of_experience} years
- Target Role: {profile.target_role}
- Preferred Industries: {', '.join(profile.preferred_industries) if profile.preferred_industries else 'Any'}

Job:
- Title: {job.title}
- Company: {job.company}
- Required Skills: {', '.join(requirements.get('skills', []))}
- Experience Required: {requirements.get('years_required', 0)} years
- Level: {requirements.get('experience_level', 'Unknown')}

Provide:
1. Match score (1-10)
2. Top 3 matched skills
3. Top 3 missing skills
4. Brief reasoning (2-3 sentences)"""

        self.conversation_history.append({"role": "user", "content": prompt})

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=self.conversation_history,
        )

        assistant_message = response.content[0].text
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )

        # Parse the scoring response
        return self._parse_match_result(
            job, requirements, assistant_message
        )

    def _parse_requirements(self, text: str) -> dict[str, Any]:
        """Parse Claude's requirement extraction response."""
        return {
            "skills": self._extract_list(text, "skills"),
            "experience_level": self._extract_level(text),
            "years_required": self._extract_years(text),
            "key_responsibilities": self._extract_list(text, "responsib"),
            "nice_to_have": self._extract_list(text, "nice"),
        }

    def _parse_match_result(
        self, job: Job, requirements: dict[str, Any], text: str
    ) -> MatchResult:
        """Parse Claude's match scoring response."""
        score = self._extract_score(text)
        matched = self._extract_list(text, "matched")
        missing = self._extract_list(text, "missing")

        return MatchResult(
            job_id=job.job_id,
            job_title=job.title,
            company=job.company,
            match_score=score,
            matched_skills=matched[:3],
            missing_skills=missing[:3],
            reasoning=self._extract_reasoning(text),
            key_requirements=requirements.get("skills", [])[:3],
            salary_range=job.salary,
        )

    @staticmethod
    def _extract_score(text: str) -> int:
        """Extract score (1-10) from text."""
        match = re.search(r"(?:score|rating)[:\s]*(\d+)", text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return min(10, max(1, score))
        return 5  # Default middle score

    @staticmethod
    def _extract_list(text: str, keyword: str) -> list[str]:
        """Extract list of items matching keyword."""
        pattern = rf"{keyword}[:\s]*([^\n]+(?:\n[^\n]+)*?)(?=\n\n|\n[A-Z]|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            items_text = match.group(1)
            # Split by newlines or commas
            items = re.split(r"[,\n]", items_text)
            return [
                item.strip() for item in items if item.strip() and len(item.strip()) > 2
            ]
        return []

    @staticmethod
    def _extract_level(text: str) -> str:
        """Extract experience level from text."""
        for level in ["lead", "senior", "mid", "junior", "entry"]:
            if level.lower() in text.lower():
                return level.capitalize()
        return "Unknown"

    @staticmethod
    def _extract_years(text: str) -> int:
        """Extract years of experience from text."""
        match = re.search(r"(\d+)\s*(?:years?|yrs?)", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def _extract_reasoning(text: str) -> str:
        """Extract reasoning from text."""
        # Find the reasoning section
        match = re.search(
            r"(?:reasoning|reason|why)[:\s]*(.+?)(?=\n[A-Z]|\Z)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1).strip()[:500]  # Max 500 chars
        return "See score and skills above."

    def reset_conversation(self) -> None:
        """Reset conversation history for a new matching session."""
        self.conversation_history = []
