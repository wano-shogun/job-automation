"""Job ranking and scoring system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from job_automation.models import Job
from job_automation.profile.models import Profile
from job_automation.scoring.matcher import JobMatcher, MatchResult


@dataclass
class RankedJob:
    """A job with its match score and ranking information."""

    job: Job
    match_score: int  # 1-10
    rank: int  # Position in ranking
    matched_skills: list[str]
    missing_skills: list[str]
    reasoning: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    def __repr__(self) -> str:
        """String representation of ranked job."""
        return (
            f"RankedJob(rank={self.rank}, score={self.match_score}, "
            f"title={self.job.title}, company={self.job.company})"
        )


class JobRanker:
    """Ranks and scores jobs based on profile match."""

    def __init__(self) -> None:
        """Initialize the job ranker."""
        self.matcher = JobMatcher()

    def rank_jobs(
        self,
        jobs: list[Job],
        profile: Profile,
        min_score: int = 5,
        use_claude: bool = True,
    ) -> list[RankedJob]:
        """Rank jobs based on profile match.

        Args:
            jobs: List of jobs to rank
            profile: User profile for matching
            min_score: Minimum score to include (1-10)
            use_claude: Use Claude for intelligent scoring (vs heuristics only)

        Returns:
            List of RankedJob objects, sorted by score (highest first)
        """
        ranked_jobs = []

        for job in jobs:
            try:
                if use_claude:
                    # Use Claude for intelligent matching
                    match_result = self.matcher.match_job_to_profile(
                        job, profile
                    )
                    score = match_result.match_score
                    matched_skills = match_result.matched_skills
                    missing_skills = match_result.missing_skills
                    reasoning = match_result.reasoning
                else:
                    # Use heuristic scoring
                    score, matched_skills, missing_skills, reasoning = (
                        self._score_job_heuristic(job, profile)
                    )

                if score >= min_score:
                    # Extract salary range if available
                    salary_min, salary_max = self._parse_salary(job.salary)

                    ranked_job = RankedJob(
                        job=job,
                        match_score=score,
                        rank=0,  # Will be set after sorting
                        matched_skills=matched_skills,
                        missing_skills=missing_skills,
                        reasoning=reasoning,
                        salary_min=salary_min,
                        salary_max=salary_max,
                    )
                    ranked_jobs.append(ranked_job)

            except Exception as e:
                print(f"Error ranking job {job.title} at {job.company}: {e}")
                continue

        # Sort by score (highest first)
        ranked_jobs.sort(key=lambda x: x.match_score, reverse=True)

        # Set rank positions
        for i, ranked_job in enumerate(ranked_jobs, 1):
            ranked_job.rank = i

        return ranked_jobs

    @staticmethod
    def _score_job_heuristic(
        job: Job, profile: Profile
    ) -> tuple[int, list[str], list[str], str]:
        """Score a job using heuristics (no Claude).

        Args:
            job: Job to score
            profile: User profile

        Returns:
            Tuple of (score, matched_skills, missing_skills, reasoning)
        """
        if not job.description:
            return 5, [], [], "No description available"

        # Simple heuristic: count skill matches
        description_lower = job.description.lower()
        title_lower = job.title.lower()

        matched = []
        for skill in profile.skills:
            if skill.lower() in description_lower or skill.lower() in title_lower:
                matched.append(skill)

        # Calculate score based on matches
        score = min(10, 3 + len(matched))  # Base 3, +1 per matched skill

        # Check experience level requirements
        if "senior" in title_lower and profile.years_of_experience < 5:
            score -= 2
        elif "junior" in title_lower and profile.years_of_experience > 3:
            score -= 1
        elif "entry" in title_lower and profile.years_of_experience > 0:
            score -= 1

        # Estimate missing skills (common ones not mentioned)
        common_missing = [
            skill
            for skill in profile.skills
            if skill.lower() not in description_lower
        ]
        missing = common_missing[:3]

        reasoning = (
            f"Matched {len(matched)} of your skills. "
            f"Job is seeking a {profile.target_role} role."
        )

        return max(1, score), matched[:3], missing, reasoning

    @staticmethod
    def _parse_salary(salary_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
        """Parse salary range from string.

        Args:
            salary_str: Salary string (e.g., "$100k-$150k", "$100,000 - $150,000")

        Returns:
            Tuple of (min_salary, max_salary) in thousands, or (None, None)
        """
        if not salary_str:
            return None, None

        import re

        # Find numbers (with optional k, comma, etc)
        matches = re.findall(r"\$?([\d,]+)(?:k|K|000)?", salary_str)
        if len(matches) >= 2:
            try:
                min_sal = int(matches[0].replace(",", ""))
                max_sal = int(matches[1].replace(",", ""))
                # Normalize to thousands
                if min_sal > 100:
                    min_sal = min_sal // 1000
                if max_sal > 100:
                    max_sal = max_sal // 1000
                return min_sal, max_sal
            except ValueError:
                return None, None
        return None, None

    def get_top_matches(
        self,
        jobs: list[Job],
        profile: Profile,
        top_n: int = 10,
        min_score: int = 6,
    ) -> list[RankedJob]:
        """Get top N matching jobs.

        Args:
            jobs: List of jobs to rank
            profile: User profile
            top_n: Number of top matches to return
            min_score: Minimum score (1-10)

        Returns:
            Top N ranked jobs
        """
        ranked = self.rank_jobs(jobs, profile, min_score=min_score)
        return ranked[:top_n]

    def filter_by_score(
        self, jobs: list[Job], profile: Profile, min_score: int = 7
    ) -> list[RankedJob]:
        """Filter jobs to only those meeting minimum score.

        Args:
            jobs: List of jobs to filter
            profile: User profile
            min_score: Minimum score (1-10)

        Returns:
            Filtered and ranked jobs
        """
        return self.rank_jobs(jobs, profile, min_score=min_score)

    def get_ranking_summary(self, ranked_jobs: list[RankedJob]) -> str:
        """Get a text summary of job rankings.

        Args:
            ranked_jobs: List of ranked jobs

        Returns:
            Formatted summary string
        """
        if not ranked_jobs:
            return "No matching jobs found."

        summary = f"📊 Job Ranking Summary ({len(ranked_jobs)} matches)\n"
        summary += "=" * 70 + "\n\n"

        for job in ranked_jobs[:10]:  # Show top 10
            summary += f"{job.rank}. {job.job.title} at {job.job.company}\n"
            summary += f"   Score: {job.match_score}/10 | "
            if job.salary_min and job.salary_max:
                summary += f"Salary: ${job.salary_min}k-${job.salary_max}k\n"
            else:
                summary += "Salary: Not listed\n"
            summary += f"   Matched Skills: {', '.join(job.matched_skills)}\n"
            summary += f"   Missing: {', '.join(job.missing_skills)}\n"
            summary += f"   {job.reasoning}\n\n"

        if len(ranked_jobs) > 10:
            summary += f"... and {len(ranked_jobs) - 10} more jobs\n"

        return summary
