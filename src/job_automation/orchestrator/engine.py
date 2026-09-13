"""ApplyPilot orchestration engine - master controller."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_automation.discovery import IndeedScraper
from job_automation.scoring import JobRanker
from job_automation.resume import ResumeTailor, ResumeParser, ResumeGenerator
from job_automation.cover_letter import CoverLetterGenerator
from job_automation.apply import JobSubmitter, ScreeningAnswerer
from job_automation.db import JobDiscoveryRepository
from job_automation.models import Job
from job_automation.profile.loader import ProfileLoader


@dataclass
class ApplicationPlan:
    """Plan for applying to a set of jobs."""

    job_count: int
    ranked_jobs: list
    tailored_resumes: dict[str, str]
    cover_letters: dict[str, str]
    estimated_time_hours: float
    ready_to_apply: bool = False


class ApplyPilotEngine:
    """Main orchestration engine for job applications."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize ApplyPilot engine.

        Args:
            db_path: Path to job database
        """
        self.profile_loader = ProfileLoader()
        self.db_path = db_path
        self.ranker = JobRanker()
        self.resume_tailor = ResumeTailor()
        self.cover_letter_gen = CoverLetterGenerator()
        self.screening_answerer = ScreeningAnswerer()

    def discover_and_rank(
        self,
        query: str,
        location: str = "",
        min_score: int = 6,
        use_claude: bool = True,
    ) -> list:
        """Discover jobs and rank by fit.

        Args:
            query: Job search query
            location: Job location
            min_score: Minimum match score
            use_claude: Use Claude for scoring

        Returns:
            List of ranked jobs
        """
        # Load profile
        profile = self.profile_loader.load_profile()

        # Discover jobs
        scraper = IndeedScraper()
        jobs = scraper.search(query, location)
        scraper.close()

        if not jobs:
            return []

        # Rank jobs
        ranked = self.ranker.rank_jobs(jobs, profile, min_score=min_score, use_claude=use_claude)

        return ranked

    def create_application_plan(
        self,
        ranked_jobs: list,
        resume_path: Optional[str | Path] = None,
    ) -> ApplicationPlan:
        """Create a plan for applying to ranked jobs.

        Args:
            ranked_jobs: List of ranked jobs
            resume_path: Path to resume file

        Returns:
            Application plan
        """
        if not resume_path:
            profile = self.profile_loader.load_profile()
            resume_path = profile.resume

        if not resume_path or not Path(resume_path).exists():
            raise FileNotFoundError(f"Resume not found: {resume_path}")

        # Parse resume
        parser = ResumeParser()
        parsed = parser.parse_resume(resume_path)

        # Generate tailored resumes
        print("Tailoring resumes...")
        tailored_resumes = self.resume_tailor.generate_resume_variants(
            parsed, [job.job for job in ranked_jobs[:10]]
        )

        # Generate cover letters
        print("Generating cover letters...")
        profile = self.profile_loader.load_profile()
        cover_letters = {}
        for job in ranked_jobs[:10]:
            try:
                letter = self.cover_letter_gen.generate_cover_letter(job.job, profile)
                cover_letters[job.job.job_id] = letter
            except Exception as e:
                print(f"Error generating letter for {job.job.company}: {e}")

        # Estimate time (2 minutes per application)
        estimated_time = (len(ranked_jobs) * 2) / 60  # In hours

        return ApplicationPlan(
            job_count=len(ranked_jobs),
            ranked_jobs=ranked_jobs,
            tailored_resumes=tailored_resumes,
            cover_letters=cover_letters,
            estimated_time_hours=estimated_time,
            ready_to_apply=True,
        )

    def preview_application(
        self,
        ranked_job,
        plan: ApplicationPlan,
    ) -> dict:
        """Preview an application before submitting.

        Args:
            ranked_job: Job to preview
            plan: Application plan

        Returns:
            Preview data
        """
        job = ranked_job.job
        resume_preview = plan.tailored_resumes.get(
            job.job_id, "No tailored resume"
        )[:500]
        letter_preview = plan.cover_letters.get(job.job_id, "No cover letter")[:500]

        return {
            "job": f"{job.title} at {job.company}",
            "match_score": ranked_job.match_score,
            "location": job.location,
            "resume_preview": resume_preview + "...",
            "letter_preview": letter_preview + "...",
        }

    def execute_application_plan(
        self,
        plan: ApplicationPlan,
        output_dir: Optional[str | Path] = None,
        auto_submit: bool = False,
    ) -> dict:
        """Execute an application plan (generate files).

        Args:
            plan: Application plan to execute
            output_dir: Output directory for generated files
            auto_submit: Auto-submit (requires browser)

        Returns:
            Execution results
        """
        if not output_dir:
            output_dir = Path.home() / ".job-automation" / "applications" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        results = {"generated_files": [], "submitted": [], "errors": []}

        generator = ResumeGenerator()

        for job in plan.ranked_jobs[:10]:
            try:
                job_dir = output_dir / f"{job.job.company}_{job.job.job_id}"
                job_dir.mkdir(parents=True, exist_ok=True)

                # Save resume
                if job.job.job_id in plan.tailored_resumes:
                    resume_text = plan.tailored_resumes[job.job.job_id]
                    resume_path = generator.to_pdf(
                        resume_text,
                        job_dir / "resume.pdf",
                    )
                    results["generated_files"].append(str(resume_path))

                # Save cover letter
                if job.job.job_id in plan.cover_letters:
                    letter_text = plan.cover_letters[job.job.job_id]
                    letter_path = (job_dir / "cover_letter.txt")
                    letter_path.write_text(letter_text)
                    results["generated_files"].append(str(letter_path))

            except Exception as e:
                results["errors"].append(
                    f"Error processing {job.job.company}: {e}"
                )

        return results

    def generate_application_summary(self, plan: ApplicationPlan) -> str:
        """Generate a summary of the application plan.

        Args:
            plan: Application plan

        Returns:
            Summary text
        """
        summary = f"""
📊 APPLICATION PLAN SUMMARY
{'='*60}

Total Jobs: {plan.job_count}
Tailored Resumes: {len(plan.tailored_resumes)}
Cover Letters: {len(plan.cover_letters)}
Estimated Time: {plan.estimated_time_hours:.1f} hours

TOP MATCHES:
"""
        for i, job in enumerate(plan.ranked_jobs[:5], 1):
            summary += f"\n{i}. {job.job.title} at {job.job.company}"
            summary += f"   Match: {job.match_score}/10 | Location: {job.job.location}"
            summary += f"   Skills: {', '.join(job.matched_skills)}\n"

        summary += "\nREADY TO APPLY!"

        return summary
