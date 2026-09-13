"""Tailor resumes for specific jobs while maintaining accuracy."""

from __future__ import annotations

from anthropic import Anthropic

from job_automation.models import Job
from job_automation.resume.parser import ParsedResume


class ResumeTailor:
    """Tailor resumes for specific jobs."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize tailor."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def tailor_resume(
        self, parsed_resume: ParsedResume, job: Job, include_cover_letter: bool = False
    ) -> str:
        """Tailor a parsed resume for a specific job.

        Args:
            parsed_resume: Parsed resume data
            job: Target job
            include_cover_letter: Include cover letter intro

        Returns:
            Tailored resume text
        """
        prompt = f"""Tailor this resume for the following job while maintaining 100% factual accuracy:

ORIGINAL RESUME:
{parsed_resume.raw_text}

TARGET JOB:
Title: {job.title}
Company: {job.company}
Description: {job.description}

Instructions:
1. Reorder experience/skills to highlight job-relevant achievements
2. Use keywords from job description (skills, tools, frameworks)
3. Emphasize relevant projects and accomplishments
4. Maintain 100% accuracy - don't add false experience
5. Keep the same length and structure
6. Highlight transferable skills
7. Make it ATS-friendly (simple formatting)

Provide the tailored resume text only, no explanations."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def generate_resume_variants(
        self, parsed_resume: ParsedResume, jobs: list[Job], top_n: int = 5
    ) -> dict[str, str]:
        """Generate tailored versions for top N jobs.

        Args:
            parsed_resume: Parsed resume
            jobs: List of jobs (should be pre-ranked)
            top_n: Number of variants to generate

        Returns:
            Dictionary mapping job_id to tailored resume
        """
        variants = {}
        for job in jobs[:top_n]:
            try:
                tailored = self.tailor_resume(parsed_resume, job)
                variants[job.job_id] = tailored
            except Exception as e:
                print(f"Error tailoring for {job.title}: {e}")
                continue

        return variants

    def extract_keywords(self, job: Job) -> list[str]:
        """Extract important keywords from job description."""
        if not job.description:
            return []

        prompt = f"""Extract the top 15 most important keywords/skills from this job description:

{job.description}

Return as a comma-separated list, most important first."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        return [kw.strip() for kw in text.split(",") if kw.strip()]

    def get_optimization_suggestions(
        self, parsed_resume: ParsedResume, job: Job
    ) -> dict[str, str]:
        """Get suggestions for optimizing resume for a job.

        Args:
            parsed_resume: Parsed resume
            job: Target job

        Returns:
            Dictionary of suggestions
        """
        prompt = f"""Analyze this resume for the given job and provide 5 specific optimization suggestions:

RESUME SUMMARY:
{parsed_resume.summary}

JOB TITLE: {job.title}
JOB DESCRIPTION: {job.description}

Provide specific, actionable suggestions to better match the job requirements while staying factual."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )

        return {"suggestions": response.content[0].text}
