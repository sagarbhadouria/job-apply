"""Fetch jobs from public ATS APIs. No auth, no scraping, no ToS risk.

Supported ATSs with public, unauthenticated endpoints:
  - greenhouse
  - lever
  - ashby
  - smartrecruiters
  - workday
  - breezy
  - bamboohr

Other platforms (jobvite, icims, taleo, adp, brassring, bullhorn, jazzhr,
jobdiva, successfactors) do not offer such public APIs or require per‑company
credentials. They are included in ENDPOINTS with a placeholder parser that
logs a warning and returns no jobs.
"""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, Iterable

import requests

UA = {"User-Agent": "jobfinder/1.0 (personal job search agent)"}
TIMEOUT = 20

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n{3,}")


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<\s*(br|/p|/div|/li|/h[1-6])\s*/?>", "\n", text, flags=re.I)
    text = _TAG.sub(" ", text)
    text = html.unescape(text)
    text = _WS.sub(" ", text)
    text = _NL.sub("\n\n", text)
    return text.strip()


@dataclass
class Job:
    job_id: str          # stable global id for dedupe: "<ats>:<slug>:<id>"
    ats: str
    company: str
    title: str
    location: str
    url: str
    description: str
    posted_at: str | None = None
    score: float | None = None
    salary: str | None = None
    raw: dict = field(default_factory=dict, repr=False)


# --- Parsers -----------------------------------------------------------------

def parse_greenhouse(slug: str, company: str, raw: dict) -> list[Job]:
    jobs = []
    for item in raw.get("jobs", []):
        jid = str(item.get("id"))
        title = (item.get("title") or "").strip()
        loc = (item.get("location", {}).get("name") or "").strip()
        url = item.get("absolute_url") or f"https://boards.greenhouse.io/{slug}/jobs/{jid}"
        content = strip_html(item.get("content"))
        posted = item.get("updated_at")
        if jid and title:
            jobs.append(Job(job_id=f"greenhouse:{slug}:{jid}", ats="greenhouse", company=company,
                            title=title, location=loc, url=url, description=content, posted_at=posted, raw=item))
    return jobs


def parse_lever(slug: str, company: str, raw: list | dict) -> list[Job]:
    postings = raw if isinstance(raw, list) else raw.get("postings", [])
    jobs = []
    for item in postings:
        jid = str(item.get("id"))
        title = (item.get("text") or "").strip()
        cats = item.get("categories") or {}
        loc = (cats.get("location") or "").strip()
        url = item.get("hostedUrl") or f"https://jobs.lever.co/{slug}/{jid}"

        desc_parts = [strip_html(item.get("descriptionPlain"))]
        for sec in item.get("lists") or []:
            content = sec.get("content", "")
            # content can be either raw HTML string or list of dicts
            if isinstance(content, str):
                desc_parts.append(f"\n{sec.get('text', '')}:\n{strip_html(content)}")
            else:
                desc_parts.append(f"\n{sec.get('text', '')}:\n" +
                                  "\n".join(f"- {i.get('text', '')}" for i in content))
        desc_parts.append(strip_html(item.get("additionalPlain")))
        desc = "\n\n".join(p for p in desc_parts if p).strip()

        created = item.get("createdAt")
        # Lever timestamps are in milliseconds
        posted = datetime.fromtimestamp(created / 1000).date().isoformat() if created else None
        if jid and title:
            jobs.append(Job(job_id=f"lever:{slug}:{jid}", ats="lever", company=company,
                            title=title, location=loc, url=url, description=desc, posted_at=posted, raw=item))
    return jobs


def parse_ashby(slug: str, company: str, raw: dict) -> list[Job]:
    jobs = []
    for item in raw.get("jobs", []):
        if not item.get("isListed", True):
            continue
        jid = str(item.get("id"))
        title = (item.get("title") or "").strip()
        loc = (item.get("location") or "").strip()
        url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}/{jid}"
        desc = strip_html(item.get("descriptionHtml") or item.get("descriptionPlain"))
        posted = item.get("publishedAt")
        salary = item.get("salary")
        if jid and title:
            jobs.append(Job(job_id=f"ashby:{slug}:{jid}", ats="ashby", company=company,
                            title=title, location=loc, url=url, description=desc, posted_at=posted, salary=salary, raw=item))
    return jobs


def parse_smartrecruiters(slug: str, company: str, raw: dict) -> list[Job]:
    jobs = []
    for item in raw.get("content", []):
        jid = str(item.get("id"))
        title = (item.get("name") or "").strip()
        loc_data = item.get("location") or {}
        city = loc_data.get("city", "")
        country = loc_data.get("country", "")
        remote = "Remote" if loc_data.get("remote") else ""
        loc = ", ".join(filter(None, [city, country, remote])) or "Unspecified"
        url = f"https://jobs.smartrecruiters.com/{slug}/{jid}"
        posted = item.get("releasedDate")
        if jid and title:
            jobs.append(Job(job_id=f"smartrecruiters:{slug}:{jid}", ats="smartrecruiters", company=company,
                            title=title, location=loc, url=url, description=title, posted_at=posted, raw=item))
    return jobs


def parse_workday(slug: str, company: str, raw: dict) -> list[Job]:
    jobs = []
    postings = raw.get("jobPostings", [])
    # Handle slug as tenant/board or tenant
    tenant = slug.split("/")[0]
    for item in postings:
        path = item.get("externalPath", "")
        jid = path.split("/")[-1] if path else item.get("bulletFields", [""])[0]
        title = (item.get("title") or "").strip()
        loc = item.get("locationsText") or ""
        url = f"https://{tenant}.myworkdayjobs.com{path}" if path else f"https://{tenant}.myworkdayjobs.com"
        posted = item.get("postedOn")
        if jid and title:
            jobs.append(Job(job_id=f"workday:{tenant}:{jid}", ats="workday", company=company,
                            title=title, location=loc, url=url, description=title, posted_at=posted, raw=item))
    return jobs


def parse_breezy(slug: str, company: str, raw: list | dict) -> list[Job]:
    items = raw if isinstance(raw, list) else []
    jobs = []
    for item in items:
        jid = str(item.get("_id") or item.get("id"))
        title = (item.get("name") or "").strip()
        loc = (item.get("location", {}).get("name") or "").strip()
        url = item.get("url") or f"https://{slug}.breezy.hr/p/{jid}"
        desc = strip_html(item.get("description"))
        posted = item.get("published_at")
        if jid and title:
            jobs.append(Job(job_id=f"breezy:{slug}:{jid}", ats="breezy", company=company,
                            title=title, location=loc, url=url, description=desc, posted_at=posted, raw=item))
    return jobs


def parse_bamboohr(slug: str, company: str, raw: dict) -> list[Job]:
    jobs = []
    items = raw.get("result", raw.get("jobs", []))
    for item in items:
        jid = str(item.get("id"))
        title = (item.get("jobTitle") or item.get("title") or "").strip()
        loc_data = item.get("location") or {}
        if isinstance(loc_data, dict):
            loc = ", ".join(filter(None, [loc_data.get("city"), loc_data.get("state")]))
        else:
            loc = str(loc_data)
        url = f"https://{slug}.bamboohr.com/careers/{jid}"
        if jid and title:
            jobs.append(Job(job_id=f"bamboohr:{slug}:{jid}", ats="bamboohr", company=company,
                            title=title, location=loc, url=url, description=title, posted_at=None, raw=item))
    return jobs

def parse_bamboohr_json(slug: str, company: str, raw: list | dict) -> list[Job]:
    """Parser for BambooHR's JSON feed: https://{slug}.bamboohr.com/jobs/index.php?format=json
    Expects a list of job objects with fields: id, title, location, etc.
    """
    jobs = []
    # The feed may return a list directly, or a dict with a "jobs" key
    items = raw if isinstance(raw, list) else raw.get("jobs", [])
    for item in items:
        jid = str(item.get("id", ""))
        title = (item.get("title") or item.get("jobTitle") or "").strip()
        # Location can be a string or object
        loc_data = item.get("location") or {}
        if isinstance(loc_data, dict):
            loc = ", ".join(filter(None, [loc_data.get("city"), loc_data.get("state")]))
        else:
            loc = str(loc_data)
        url = item.get("url") or f"https://{slug}.bamboohr.com/careers/{jid}"
        # Description may be available; fallback to title
        desc = strip_html(item.get("description") or "")
        if not desc:
            desc = title
        posted = item.get("postedAt") or item.get("datePosted")
        if jid and title:
            jobs.append(Job(
                job_id=f"bamboohr:{slug}:{jid}",
                ats="bamboohr",
                company=company,
                title=title,
                location=loc,
                url=url,
                description=desc,
                posted_at=posted,
                raw=item
            ))
    return jobs

def parse_breezy_json(slug: str, company: str, raw: list) -> list[Job]:
    """Parser for Breezy's public JSON feed at https://{slug}.breezy.hr/json."""
    jobs = []
    for item in raw:
        jid = str(item.get("id", ""))
        title = (item.get("name") or "").strip()

        # Location extraction
        loc_data = item.get("location") or {}
        loc = loc_data.get("name") or ""

        # URL
        url = item.get("url") or f"https://{slug}.breezy.hr/p/{jid}"

        # Description – the JSON feed doesn't include full description,
        # so we'll use title and location as a placeholder
        desc = f"{title} at {company} ({loc})"

        # Published date
        posted = item.get("published_date")

        if jid and title:
            jobs.append(Job(
                job_id=f"breezy:{slug}:{jid}",
                ats="breezy",
                company=company,
                title=title,
                location=loc,
                url=url,
                description=desc,
                posted_at=posted,
                raw=item
            ))
    return jobs

# ----------------------------------------------------------------------------
# Placeholder parser for unsupported ATSs that lack public, unauthenticated APIs
# ----------------------------------------------------------------------------
def parse_unsupported(slug: str, company: str, raw: dict) -> list[Job]:
    print(f"  ! {slug}: ATS not yet supported (no public API or requires credentials). Skipping.")
    return []


# --- Endpoint Configuration ---------------------------------------------------

ENDPOINTS = {
    "greenhouse": {
        "url": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
        "parser": parse_greenhouse
    },
    "lever": {
        "url": "https://api.lever.co/v0/postings/{slug}?mode=json",
        "parser": parse_lever
    },
    "ashby": {
        "url": "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
        "parser": parse_ashby
    },
    "smartrecruiters": {
        "url": "https://api.smartrecruiters.com/v1/companies/{slug}/postings",
        "parser": parse_smartrecruiters
    },
    "workday": {
        "url": "https://{tenant}.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs",
        "parser": parse_workday,
        "method": "POST",
        "json": {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "", "jobPostingLocale": "en_US"}
    },
    "breezy": {
        "url": "https://{slug}.breezy.hr/json",
        "parser": parse_breezy_json,
        # No custom headers needed – this endpoint works without them
    },
    "bamboohr": {
        "url": "https://{slug}.bamboohr.com/jobs/index.php?format=json",
        "parser": parse_bamboohr_json,
    },
    # --- New ATSs requested but not supportable without credentials or unofficial scraping ---
    "jobvite": {
        "url": "",  # requires API key + HMAC signature; not feasible for public use
        "parser": parse_unsupported
    },
    "icims": {
        "url": "",  # internal endpoints are undocumented and unstable; no public API
        "parser": parse_unsupported
    },
    "taleo": {
        "url": "",  # per‑company paths vary widely; no clean public pattern
        "parser": parse_unsupported
    },
    "adp": {
        "url": "",
        "parser": parse_unsupported
    },
    "brassring": {
        "url": "",
        "parser": parse_unsupported
    },
    "bullhorn": {
        "url": "",
        "parser": parse_unsupported
    },
    "jazzhr": {
        "url": "",
        "parser": parse_unsupported
    },
    "jobdiva": {
        "url": "",
        "parser": parse_unsupported
    },
    "successfactors": {
        "url": "",
        "parser": parse_unsupported
    },
}


def fetch_board(ats: str, slug: str, company: str | None = None,
                session: requests.Session | None = None) -> list[Job]:
    """Hit one company's public board. Returns [] on any failure (never raises)."""
    if ats not in ENDPOINTS:
        raise ValueError(f"unknown ATS: {ats}")

    spec = ENDPOINTS[ats]
    url_tpl = spec["url"]
    parser = spec["parser"]
    method = spec.get("method", "GET")
    json_payload = spec.get("json")

    sess = session or requests

    # --- Workday pagination (unchanged) ---
    if ats == "workday":
        parts = slug.split("/")
        if len(parts) == 1:
            subdomain = parts[0]
            path_tenant = parts[0]
            board = "External"
        elif len(parts) == 2:
            subdomain = parts[0]
            path_tenant = parts[1]
            board = "External"
        else:
            subdomain = parts[0]
            path_tenant = parts[1]
            board = parts[2]

        url = f"https://{subdomain}.myworkdayjobs.com/wday/cxs/{path_tenant}/{board}/jobs"
        all_jobs = []
        offset = 0
        limit = json_payload.get("limit", 20) if json_payload else 20
        max_pages = 50  # safety cap: 50 * 20 = 1000 jobs max

        for page in range(max_pages):
            payload = json_payload.copy() if json_payload else {}
            payload["offset"] = offset
            payload["limit"] = limit

            try:
                r = sess.post(url, json=payload, headers=UA, timeout=TIMEOUT)
            except Exception as e:
                print(f"  ! {ats}/{slug} page {page+1} -> {type(e).__name__}: {e}")
                break

            if r.status_code != 200:
                print(f"  ! {ats}/{slug} page {page+1} -> HTTP {r.status_code}")
                break

            try:
                data = r.json()
            except ValueError:
                print(f"  ! {ats}/{slug} page {page+1} -> invalid JSON")
                break

            postings = data.get("jobPostings", [])
            if not postings:
                break

            page_jobs = parser(slug, company or slug, data)
            all_jobs.extend(page_jobs)
            print(f"  {ats}/{slug} -> page {page+1}: {len(page_jobs)} jobs (total {len(all_jobs)})")

            if len(postings) < limit:
                break

            offset += limit
            time.sleep(0.5)

        return all_jobs

    # --- All other ATSs (single request) ---
    try:
        if not url_tpl:
            return parser(slug, company or slug, {})

        # Build the full URL
        url = url_tpl.format(slug=slug)

        # Build headers: start with default UA, then add custom headers (e.g., for Breezy)
        headers = UA.copy()
        if spec.get("headers"):
            for key, value in spec["headers"].items():
                # Replace {slug} placeholder if present
                if "{slug}" in value:
                    value = value.format(slug=slug)
                headers[key] = value

        if method == "POST":
            r = sess.post(url, json=json_payload, headers=headers, timeout=TIMEOUT)
        else:
            r = sess.get(url, headers=headers, timeout=TIMEOUT)

        if r.status_code != 200:
            print(f"  ! {ats}/{slug} -> HTTP {r.status_code}")
            return []
        return parser(slug, company or slug, r.json())
    except Exception as e:
        print(f"  ! {ats}/{slug} -> {type(e).__name__}: {e}")
        return []


def fetch_all(companies: Iterable[dict], sleep: float = 0.2) -> list[Job]:
    jobs: list[Job] = []
    sess = requests.Session()
    for c in companies:
        ats = c.get("ats", "").strip().lower()
        slug = c.get("slug", "").strip()
        name = c.get("name")
        if not ats or not slug:
            continue
        b_jobs = fetch_board(ats, slug, company=name, session=sess)
        print(f"  {ats}/{slug} -> {len(b_jobs)} jobs")
        jobs.extend(b_jobs)
        if sleep:
            time.sleep(sleep)
    return jobs