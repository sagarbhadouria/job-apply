"""Fetch jobs from JSearch API - auto-discovers companies, no manual setup needed.

JSearch aggregates jobs from all ATS platforms (Greenhouse, Lever, Ashby, etc).
No need to maintain companies.yaml — just query by location + role + preferences.

Get a free API key: https://rapidapi.com/laimoon/api/jsearch (100 calls/month)
Or upgrade: https://www.jsearch.io (unlimited enterprise)
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from .fetch import Job, strip_html

UA = {"User-Agent": "jobfinder/1.0 (personal job search agent)"}
TIMEOUT = 30


def parse_jsearch_job(raw: dict[str, Any]) -> Job | None:
    """Convert JSearch API response to Job dataclass.

    JSearch returns jobs from all ATS platforms with normalized fields.
    Returns None if required fields are missing.
    """
    try:
        job_id = raw.get("job_id")
        company = raw.get("employer_name") or ""
        title = raw.get("job_title") or ""
        url = raw.get("job_apply_link") or raw.get("job_google_link") or ""

        # Build location from city, state, country
        city = raw.get("job_city") or ""
        state = raw.get("job_state") or ""
        country = raw.get("job_country") or ""
        parts = [p for p in [city, state, country] if p]
        location = ", ".join(parts) if parts else "—"

        description = raw.get("job_description") or ""
        posted = raw.get("job_posted_at_datetime_utc")

        salary = raw.get("job_salary_string") or None

        if not (job_id and company and title and url and description):
            return None

        # Infer ATS from URL (optional, best-effort)
        ats = "unknown"
        url_lower = url.lower()
        if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
            ats = "greenhouse"
        elif "lever.co" in url_lower or "jobs.lever" in url_lower:
            ats = "lever"
        elif "ashbyhq.com" in url_lower or "jobs.ashbyhq" in url_lower:
            ats = "ashby"
        elif "linkedin.com" in url_lower:
            ats = "linkedin"
        elif "indeed.com" in url_lower:
            ats = "indeed"

        return Job(
            job_id=f"jsearch:{job_id}",  # unique across runs
            ats=ats,
            company=company.strip(),
            title=title.strip(),
            location=location.strip() or "—",
            url=url.strip(),
            description=strip_html(description).strip(),
            posted_at=posted,
            salary=salary,
        )
    except Exception as e:
        return None


def fetch_jsearch(
    query: str,
    location: str | None = None,
    country: str | None = None,
    date_posted: str | None = None,
    remote: bool | None = None,
    job_requirements: str | None = None,
    exclude_job_publishers: str | None = None,
    results_limit: int = 50,
    api_key: str | None = None,
    sleep: float = 0.5,
) -> list[Job]:
    """Fetch jobs from JSearch API with full parameter support.

    Args:
        query: Job title/role to search (required).
        location: Location (e.g., "bangalore", "india", "remote").
        country: Country code (e.g., "in", "us") – overrides location-based detection.
        date_posted: "all", "today", "3days", "week", "month".
        remote: If True, only show remote jobs.
        job_requirements: e.g., "more_than_3_years_experience".
        exclude_job_publishers: Comma-separated list of publishers to exclude.
        results_limit: Maximum jobs to fetch (capped by API).
        api_key: JSearch API key. Falls back to JSEARCH_API_KEY env var.
        sleep: Delay before request (be nice to the API).

    Returns:
        list[Job] with standardized fields.

    Raises:
        ValueError: If API key is missing or query is invalid.
    """
    if api_key is None:
        api_key = os.environ.get("JSEARCH_API_KEY")

    if not api_key:
        raise ValueError(
            "JSearch API key missing. Set JSEARCH_API_KEY env var or pass it directly.\n"
            "Get free key: https://rapidapi.com/laimoon/api/jsearch (100 calls/month)\n"
            "Or paid: https://www.jsearch.io (unlimited)"
        )

    url = "https://jsearch.p.rapidapi.com/search-v2"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "jsearch.p.rapidapi.com",
        **UA,
    }

    # Build params – only include non-None values
    params: dict[str, Any] = {
        "query": query,
        "num_pages": max(1, (results_limit + 9) // 10),  # pages of 10 jobs
    }
    if location:
        params["location"] = location
    if country:
        params["country"] = country
    if date_posted:
        params["date_posted"] = date_posted
    if remote is not None:
        params["remote"] = "true" if remote else "false"
    if job_requirements:
        params["job_requirements"] = job_requirements
    if exclude_job_publishers:
        params["exclude_job_publishers"] = exclude_job_publishers

    print(f"  jsearch: fetching '{query}' in '{location or country or 'any'}' "
          f"(remote={remote}, limit={results_limit})")

    try:
        time.sleep(sleep)  # be nice to rate limits
        r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)

        if r.status_code == 429:
            print("  ! jsearch rate limit hit – try again later")
            return []
        if r.status_code != 200:
            raise ValueError(f"HTTP {r.status_code}: {r.text[:200]}")

        payload = r.json()
        data = payload.get("data", {})
        raw_jobs = data.get("jobs", []) if isinstance(data, dict) else []

        jobs = []
        for raw in raw_jobs:
            job = parse_jsearch_job(raw)
            if job:
                jobs.append(job)

        print(f"    -> parsed {len(jobs)} valid jobs (from {len(raw_jobs)} results)")
        return jobs

    except requests.exceptions.RequestException as e:
        print(f"  ! jsearch network error: {type(e).__name__}: {e}")
        return []
    except (ValueError, KeyError) as e:
        print(f"  ! jsearch parse error: {e}")
        return []


def fetch_jsearch_multi(
    queries: list[dict] | None = None,
    api_key: str | None = None,
) -> list[Job]:
    """Fetch from multiple search queries in one run.

    Useful for exploring different roles/locations simultaneously.

    Args:
        queries: List of dicts with keys:
            - query (required): job title/role
            - location, country, date_posted, remote, job_requirements,
              exclude_job_publishers, results (or limit)
        api_key: JSearch API key

    Returns:
        Combined list of unique jobs (deduped by job_id).

    Example:
        >>> queries = [
        ...     {"query": "backend engineer", "location": "bangalore"},
        ...     {"query": "devops engineer", "location": "india", "results": 30},
        ...     {"query": "platform engineer", "remote": True},
        ... ]
        >>> jobs = fetch_jsearch_multi(queries)
    """
    if queries is None:
        queries = [
            {"query": "backend engineer", "location": "india", "date_posted": "3days"},
            {"query": "software engineer", "location": "bangalore", "date_posted": "3days"},
            {"query": "platform engineer", "remote": True, "date_posted": "week"},
        ]

    all_jobs = []
    seen_ids = set()

    for q in queries:
        # Extract known parameters
        query = q.get("query")
        if not query:
            print("  ! skipping query without 'query' field")
            continue

        # Map common keys
        kwargs = {
            "query": query,
            "location": q.get("location"),
            "country": q.get("country"),
            "date_posted": q.get("date_posted"),
            "remote": q.get("remote"),
            "job_requirements": q.get("job_requirements"),
            "exclude_job_publishers": q.get("exclude_job_publishers"),
            "results_limit": q.get("results") or q.get("limit") or 50,
        }
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        try:
            jobs = fetch_jsearch(api_key=api_key, **kwargs)
            for job in jobs:
                if job.job_id not in seen_ids:
                    all_jobs.append(job)
                    seen_ids.add(job.job_id)
        except ValueError as e:
            print(f"  ! skipping query '{query}': {e}")

    print(f"\nfetch_jsearch_multi: {len(all_jobs)} unique jobs across all queries")
    return all_jobs