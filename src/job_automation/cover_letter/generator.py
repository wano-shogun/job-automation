"""Generate personalized cover letters for job applications."""

from __future__ import annotations

from anthropic import Anthropic

from job_automation.models import Job
from job_automation.profile.models import Profile


class CoverLetterGenerator:
    """Generate personalized cover letters."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize generator."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def generate_cover_letter(
        self, job: Job, profile: Profile, company_info: str = ""
    ) -> str:
        """Generate a personalized cover letter.

        Args:
            job: Target job
            profile: User profile
            company_info: Optional company research/details

        Returns:
            Generated cover letter text
        """
        prompt = f"""Generate a professional, personalized cover letter for this job application.

APPLICANT PROFILE:
Name: {profile.name}
Target Role: {profile.target_role}
Experience: {profile.years_of_experience} years
Skills: {', '.join(profile.skills[:10])}
LinkedIn: {profile.linkedIn or 'N/A'}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description: {job.description}

COMPANY INFO:
{company_info or 'Unknown - research if possible'}

Requirements for the cover letter:
1. Professional format (3-4 paragraphs)
2. Personalized to the specific job and company
3. Highlight relevant skills and experience
4. Show enthusiasm and cultural fit
5. Clear call to action
6. Maintain 1-page length
7. Use proper business letter format
8. Mention specific details from job posting

Generate only the letter body, no "Cover Letter" header."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    def generate_multiple_letters(
        self, jobs: list[Job], profile: Profile, company_info_map: dict = None
    ) -> dict[str, str]:
        """Generate cover letters for multiple jobs.

        Args:
            jobs: List of jobs
            profile: User profile
            company_info_map: Optional mapping of company names to info

        Returns:
            Dictionary mapping job_id to cover letter
        """
        if company_info_map is None:
            company_info_map = {}

        letters = {}
        for job in jobs:
            try:
                company_info = company_info_map.get(job.company, "")
                letter = self.generate_cover_letter(job, profile, company_info)
                letters[job.job_id] = letter
            except Exception as e:
                print(f"Error generating letter for {job.company}: {e}")
                continue

        return letters

    def generate_with_format(
        self, job: Job, profile: Profile, format_type: str = "standard"
    ) -> str:
        """Generate cover letter in specific format.

        Args:
            job: Target job
            profile: User profile
            format_type: Format (standard, casual, technical)

        Returns:
            Formatted cover letter
        """
        tone_map = {
            "standard": "professional and formal",
            "casual": "friendly and personable",
            "technical": "technical and detailed",
        }

        tone = tone_map.get(format_type, "professional")

        prompt = f"""Generate a {tone} cover letter for this job:

Job: {job.title} at {job.company}
Applicant: {profile.name} ({profile.years_of_experience} years experience)
Skills: {', '.join(profile.skills[:5])}

Requirements: {job.description}

Generate a {tone} cover letter appropriate for this role."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
