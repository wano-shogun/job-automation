"""Public Ashby job board feed with direct application URLs."""

from __future__ import annotations

from urllib.parse import quote, urlparse
import math

import requests

from job_automation.models import Job


def search_ashby_board(
    board: str, query: str, location: str = "", *, session: requests.Session | None = None
) -> list[Job]:
    """Search one public Ashby board for listed jobs with application links."""
    if not board or "/" in board or ".." in board:
        raise ValueError("Ashby board must be a single job board name")
    client = session or requests.Session()
    response = client.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{quote(board, safe='')}",
        params={"includeCompensation": "true"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    terms = query.casefold().split()
    location_filter = location.casefold().strip()
    jobs: list[Job] = []
    for item in payload.get("jobs", []):
        title = item.get("title") or ""
        description = item.get("descriptionPlain") or ""
        place = item.get("location") or ""
        apply_url = item.get("applyUrl") or ""
        host = urlparse(apply_url).hostname or ""
        if not item.get("isListed", True) or host != "jobs.ashbyhq.com":
            continue
        if not title or not apply_url:
            continue
        title_text = title.casefold()
        # The job description may mention many unrelated roles. Require the
        # role query to match the actual title before ranking the job.
        if terms and sum(term in title_text for term in terms) < math.ceil(len(terms) * 0.6):
            continue
        if location_filter and location_filter not in place.casefold():
            if not (location_filter == "remote" and item.get("isRemote")):
                continue
        compensation = item.get("compensation") or {}
        jobs.append(
            Job(
                source="ashby",
                job_id=apply_url.rstrip("/").split("/")[-2],
                title=title,
                company=board,
                location=place or ("Remote" if item.get("isRemote") else ""),
                salary=compensation.get("scrapeableCompensationSalarySummary"),
                description=description,
                url=apply_url,
                posted_date=item.get("publishedAt"),
            )
        )
    return jobs
