from datetime import datetime, timedelta, timezone
from .fetch import (parse_greenhouse, parse_lever, parse_ashby,
                    parse_smartrecruiters, parse_workday, parse_breezy, parse_bamboohr, Job)

def _ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _gh(days: int) -> str:
    """Greenhouse: ISO 8601 with an offset."""
    return _ago(days).strftime("%Y-%m-%dT%H:%M:%S-04:00")


def _lever(days: int) -> int:
    """Lever: epoch MILLISECONDS. Seconds here silently dates every posting
    to 1970 and the freshness filter eats the entire board."""
    return int(_ago(days).timestamp() * 1000)


def _ashby(days: int) -> str:
    """Ashby: ISO 8601 UTC string."""
    return _ago(days).strftime("%Y-%m-%dT%H:%M:%SZ")

MOCK_PAYLOADS = {
    "greenhouse": {
        "coinbase": {
            "jobs": [
                {
                    "id": 102,
                    "title": "Software Development Engineer, Core Infra",
                    "updated_at": _gh(2),
                    "absolute_url": "https://boards.greenhouse.io/coinbase/jobs/102",
                    "location": {"name": "Remote - India"},
                    "content": (
                        "&lt;p&gt;Work on multi-region Kafka clusters, PostgreSQL routing, "
                        "and cloud infrastructure.&lt;/p&gt;"
                    ),
                },
                {
                    "id": 103,
                    "title": "Senior Software Engineer, Platform",
                    "updated_at": _gh(40),  # Stale! Filtered out by freshness gate.
                    "absolute_url": "https://boards.greenhouse.io/coinbase/jobs/103",
                    "location": {"name": "Bengaluru, India"},
                    "content": "&lt;p&gt;Legacy platform infra maintenance.&lt;/p&gt;",
                },
                {
                    "id": 104,
                    "title": "Frontend Engineer, UI/UX",
                    "updated_at": _gh(1),  # Excluded discipline.
                    "absolute_url": "https://boards.greenhouse.io/coinbase/jobs/104",
                    "location": {"name": "Bengaluru, India"},
                    "content": "&lt;p&gt;React, Next.js, and CSS design systems.&lt;/p&gt;",
                },
                {
                    "id": 105,
                    "title": "Software Engineer, Mobile",
                    "updated_at": _gh(1),  # Excluded location.
                    "absolute_url": "https://boards.greenhouse.io/coinbase/jobs/105",
                    "location": {"name": "San Francisco, CA"},
                    "content": "&lt;p&gt;iOS and Android native applications.&lt;/p&gt;",
                },
            ]
        },
        "acme-edge": {
            "jobs": [
                {
                    "id": 5501001,
                    "title": "Software Engineer II, Distributed Systems",
                    "updated_at": _gh(1),
                    "absolute_url": "https://boards.greenhouse.io/acmeedge/jobs/5501001",
                    "location": {"name": "Bangalore, India"},
                    "content": "&lt;p&gt;Build distributed services with Go and Rust. Work on consensus algorithms, distributed tracing, and high-performance systems.&lt;/p&gt;",
                },
                {
                    "id": 5501002,
                    "title": "Site Reliability Engineer",
                    "updated_at": _gh(1),
                    "absolute_url": "https://boards.greenhouse.io/acmeedge/jobs/5501002",
                    "location": {"name": "Bengaluru, India"},
                    "content": "&lt;p&gt;Operate and scale infrastructure. Kubernetes, Terraform, monitoring, and on-call rotations.&lt;/p&gt;",
                }
            ]
        }
    },
    "lever": {
        "cloudflare": [
            {
                "id": "201",
                "text": "Backend Engineer (Go)",
                "createdAt": _lever(1),
                "hostedUrl": "https://jobs.lever.co/cloudflare/201",
                "categories": {
                    "location": "Bengaluru, India",
                    "team": "Engineering",
                },
                "description": "<p>High performance network services in Go and Rust.</p>",
                "lists": [
                    {
                        "text": "Requirements",
                        "content": "<li>3+ years Go experience</li>",
                    }
                ],
                "additionalPlain": "Focus on distributed caching and edge networks.",
            },
            {
                "id": "202",
                "text": "Account Executive, Enterprise Sales",
                "createdAt": _lever(1),  # Excluded role function.
                "hostedUrl": "https://jobs.lever.co/cloudflare/202",
                "categories": {
                    "location": "Bengaluru, India",
                    "team": "Sales",
                },
                "description": "<p>Enterprise quota-carrying sales role.</p>",
                "lists": [],
                "additionalPlain": "B2B SaaS experience required.",
            },
            {
                "id": "203",
                "text": "Software Engineer, Edge Platform",
                "createdAt": _lever(1),  # Wrong city (no remote option).
                "hostedUrl": "https://jobs.lever.co/cloudflare/203",
                "categories": {
                    "location": "San Francisco, CA",
                    "team": "Engineering",
                },
                "description": "<p>Edge computing systems.</p>",
                "lists": [],
                "additionalPlain": "On-site role in San Francisco.",
            },
        ],
        "quantstack": [
            {
                "id": "401",
                "text": "Backend Engineer (Go)",
                "createdAt": _lever(2),
                "hostedUrl": "https://jobs.lever.co/quantstack/401",
                "categories": {
                    "location": "Bengaluru, India",
                    "team": "Engineering",
                },
                "descriptionPlain": "Build scalable market data pipeline.",
                "lists": [
                    {
                        "text": "Requirements",
                        "content": "<li>2-5 years backend experience</li>",
                    }
                ],
                "additionalPlain": "No take-home assignments.",
            }
        ]
    },
    "ashby": {
        "helioscale": {
            "jobs": [
                {
                    "id": "9f8e7d6c-2222-4bbb-8888-000000000002",
                    "title": "Software Engineer, Networking",
                    "location": "Bengaluru, India",
                    "isListed": False,  # Draft posting — parser must ignore this.
                    "jobUrl": "https://jobs.ashbyhq.com/helioscale/unlisted",
                    "publishedAt": _ashby(1),
                    "descriptionPlain": "Draft posting that should never surface.",
                },
                {
                    "id": "9f8e7d6c-2222-4bbb-8888-000000000003",
                    "title": "Software Engineer, Networking",
                    "location": "Bengaluru, India",
                    "isListed": True,
                    "jobUrl": "https://jobs.ashbyhq.com/helioscale/9f8e7d6c-2222-4bbb-8888-000000000003",
                    "publishedAt": _ashby(1),
                    "descriptionPlain": "Packet processing, kernel systems, and networking stack in C++ and Go.",
                    "salary": "₹32L – ₹48L",
                },
                {
                    "id": "9f8e7d6c-2222-4bbb-8888-000000000004",
                    "title": "Data Scientist, Growth",
                    "location": "Bengaluru, India",
                    "isListed": True,
                    "jobUrl": "https://jobs.ashbyhq.com/helioscale/9f8e7d6c-2222-4bbb-8888-000000000004",
                    "publishedAt": _ashby(1),
                    "descriptionHtml": "<p>Causal inference, experimentation, SQL &amp; Python.</p>",
                },
            ]
        }
    },
    "smartrecruiters": {
        "visa": {
            "content": [
                {
                    "id": "sr-101",
                    "name": "Backend Engineer (Go)",
                    "location": {"city": "Bengaluru", "country": "India", "remote": True},
                    "releasedDate": _ago(1).isoformat()
                }
            ]
        }
    },
    "workday": {
        "nvidia/NVIDIA_Careers": {
            "jobPostings": [
                {
                    "externalPath": "/job/JR1982001",
                    "title": "Infrastructure Engineer",
                    "locationsText": "Hyderabad, India",
                    "postedOn": _ago(1).strftime("%Y-%m-%d")
                }
            ]
        }
    },
    "breezy": {
        "acme": [
            {
                "_id": "bz-201",
                "name": "Systems Software Engineer",
                "location": {"name": "Bengaluru, India"},
                "published_at": _ago(1).isoformat(),
                "description": "<p>Low latency C++ systems programming.</p>"
            }
        ]
    },
    "bamboohr": {
        "testco": {
            "result": [
                {
                    "id": "301",
                    "jobTitle": "Site Reliability Engineer",
                    "location": {"city": "Gurgaon", "state": "HR"}
                }
            ]
        }
    }
}

# Convenience attributes for tests
GREENHOUSE = MOCK_PAYLOADS["greenhouse"]
LEVER = MOCK_PAYLOADS["lever"]
ASHBY = MOCK_PAYLOADS["ashby"]

def fetch_all_mock(companies=None) -> list[Job]:
    jobs: list[Job] = []
    jobs.extend(parse_greenhouse("coinbase", "Coinbase", MOCK_PAYLOADS["greenhouse"]["coinbase"]))
    jobs.extend(parse_greenhouse("acme-edge", "Acme Edge", MOCK_PAYLOADS["greenhouse"]["acme-edge"]))
    jobs.extend(parse_lever("cloudflare", "Cloudflare", MOCK_PAYLOADS["lever"]["cloudflare"]))
    jobs.extend(parse_ashby("helioscale", "Helioscale", MOCK_PAYLOADS["ashby"]["helioscale"]))
    return jobs