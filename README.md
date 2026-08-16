# JobFinder: AI-Powered Job Scout

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge&logoSize=auto)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/sagarbhadouria/job-apply?style=for-the-badge)](https://github.com/sagarbhadouria/job-apply)

![Project Logo](https://raw.githubusercontent.com/sagarbhadouria/job-apply/main/assets/logo.png)

_A sophisticated automation and intelligence engine for navigating the modern job search process. JobFinder is designed to dramatically reduce the time and effort spent searching for the right job. Instead of visiting multiple job boards and company career pages every day, JobFinder brings relevant opportunities together, analyzes them against your profile, and prepares the information you need to apply._

## 🌐 Live Project

Try out the live generator here:

🔗 **[JobFinder Demo](https://job-finder-demo.vercel.app)**


## ✨ Features

- AI-powered job discovery and filtering from multiple ATS platforms
- Intelligent deterministic pre-filtering to minimize LLM costs
- Two-stage LLM intelligence balancing cost and quality
- Multi-source integration with Greenhouse, Workday, Lever, Ashby, JSearch, and more
- Configurable candidate profiles and search filters
- Batch processing for high-volume job description screening
- Application kit generation with a job fit summary, tailored resume bullets, identified gaps, a customizable cover note, and questions for the employer.
- Remote-friendly location logic and recency checking
- Job tracker with dedup to never review the same job twice (automatically recognizes previously seen/applied positions)

## 🧠 How It Works

The project follows a **five-stage funnel**:

### 1. Fetch
Jobs are sourced from public ATS APIs (Greenhouse, Workday, Lever, Ashby, SmartRecruiters, Breezy) or the JSearch aggregator. No auth, no scraping, no ToS risk. If `--jsearch` is used, companies are auto-discovered from a role/location query; otherwise `companies.yaml` lists the boards to scrape.

### 2. Prefilter (deterministic, free)
Before any LLM call, a cheap deterministic filter drops jobs that don't match:
- **Title filter**: includes/exclude keywords
- **Location filter**: city/region match or remote allowance
- **Freshness filter**: max age in days since posting

This reduces ~2000 raw jobs to ~40 candidates for ~0 cost, so the LLM only ever reads jobs that already passed title + location + freshness checks.

### 3. Screen (cheap LLM pass)
The first LLM stage scores every surviving job 0–10 on genuine fit using the candidate profile. Batches of ~8 jobs are processed with the JD truncated to ~1400 chars and the cheapest available model. Output: `score` + one-sentence `reason`.

### 4. Draft (expensive LLM pass)
Only the top-scoring jobs (default threshold 7.0, max 5) advance to the drafting stage. One LLM call per job with ~6000 chars of JD and the best model. Output: `fit_summary`, `tailored_bullets`, `gaps`, `cover_note`, `questions_to_ask`. Hard rule: never invent experience — every claim traces to the profile, gaps are listed honestly.

### 5. Digest (HTML output)
The final HTML digest renders each shortlisted job as a card showing:
- Title + score badge
- Company + location + ATS tag
- "Why it fits" summary
- 3–4 tailored resume bullets
- Honest gaps + how to address them
- Cover note (edit before submitting)
- 2 sharp questions to ask the employer
- "Open & apply →" link to the original posting

The digest also includes a tracker CSV and stats on scanned/filtered/new jobs.

## 🎯 Day-to-Day Benefits

1. **One Place to Find Jobs**
   </br>JobFinder fetches postings from major ATS platforms (Greenhouse, Workday, Lever, Ashby, SmartRecruiters, Breezy) and JSearch mode — eliminating the need to manually search across multiple sites.

2. **Jobs That Fit Your Profile**
   </br>LLM-powered screening evaluates each role against your skills, experience, and preferences, prioritizing opportunities where you're the strongest candidate.

3. **Application Ready for Every Match**
   </br>Shortlisted jobs get a fit summary, tailored resume bullets, identified gaps, a customizable cover note, and interview questions — all grounded in your profile.

4. **Never Review the Same Job Twice**
   </br>Job tracker automatically recognizes previously seen/ applied positions, so regular runs only surface new, relevant opportunities.

5. **Fully Configurable Search**
   </br>Almost everything — companies, keywords, locations, remote jobs, freshness, filtering — is adjustable via `config.yaml` for targeted or market‑exploration mode.

6. **Spend Less Time Searching, More Time Applying**
   </br>Automates job discovery, filtering, profile matching, application prep, and tracking — turning hours of manual hunting into a focused shortlist of high-quality opportunities.

## 🔀 Core Workflow

```mermaid
graph LR
    A[Raw Source Selection] --> B{Source Type}
    B -- Direct ATS --> C[Fetch & Parse]
    B -- JSearch API --> D[Batch Search]
    C --> E[Pre-filter Layer]
    D --> E
    E --> F{Candidate Screening}
    subgraph "LLM Pipeline"
    F -->|Batch Processing| G[Quantify Match Score]
    G --> H{Score > 7.0?}
    H -->|Yes| I[Deep Drafting Stage]
    end
    I --> J[Application Kit Generation]
    J --> K[Output: Digest & Tracker]

    style F fill:#f96,stroke:#333,stroke-width:2px
    style I fill:#f96,stroke:#333,stroke-width:2px
```

## 🚀 Quick Demo

<details>
<summary>Expand to view quick demo</summary>

|                                                                               Demo                                                                               |
|:----------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| ![Demo](https://raw.githubusercontent.com/sagarbhadouria/job-apply/main/assets/demo.gif) |

</details>


## 🧭 Getting Started

### 🔧 Prerequisites

- Python 3.9+
- pip (Python package manager)

### ⬇️ Clone Repository

```bash
# Clone the repo
git clone https://github.com/sagarbhadouria/job-apply.git
cd job-apply
```

### 🛠️ Setup Project

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\activate

# Install dependencies
python -m pip install -r requirements.txt

# Test installation (If you see a mock job search and a generated digest, your installation is working)
python -m jobfinder run --mock --scorer keyword

# Generate a profile (profile.json) from your resume (PDF or text)
python -m jobfinder profile --resume path/to/your/resume.pdf

# Set up environment variables (supply your own API keys in .env)
cp .env.example .env
````

### ▶️ Run Application

```bash
# Run the application in standard mode with limited job search (no email notifications)
python -m jobfinder run --limit 10

# Run the application in standard mode with full job search (no email notifications)
python -m jobfinder run

# Run the application in standard mode with full job search and send email notifications (ensure SMTP settings are configured in .env)
python -m jobfinder run --send

# Run the application in JSearch mode for broad market exploration (no email notifications)
python -m jobfinder run --jsearch

# Run the application in JSearch mode for broad market exploration and send email notifications (ensure SMTP settings are configured in .env)
python -m jobfinder run --jsearch --send
```

## 📚 Usage Guide

1. **Configure Profiles**: Edit `config.yaml` to define your title keywords, locations, and filters
2. **Prepare Profile**: Run the system to generate your `profile.json` from your resume (PDF or text)
3. **Run Pipelines**:
   - Use standard mode for targeted company hunting
   - Use `--jsearch` mode for broad-scale market exploration

## 🗂️ Project Structure

```
job-apply/
├── README.md                                    # Project documentation & usage guide
├── companies.yaml                               # ATS company configurations (slugs, board names)
├── config.yaml                                  # Pipeline settings (filters, thresholds, LLM configs)
├── jobfinder/                                     # Main Python package
│   ├── __init__.py                              # Package initialization
│   ├── __main__.py                              # Entry point (`python -m jobfinder`)
│   ├── cli.py                                   # CLI argument parser and pipeline orchestrator
│   ├── digest.py                                # HTML digest builder with inline CSS
│   ├── fetch.py                                 # ATS API fetchers (Greenhouse, Workday, Lever, etc.)
│   ├── jsearch.py                               # JSearch aggregator API client
│   ├── llm.py                                   # Two-stage LLM screening & drafting
│   ├── mailer.py                                # Email sending functionality
│   ├── mock.py                                  # Mock data for testing without API keys
│   ├── providers.py                             # LLM provider abstraction (Anthropic, Gemini, Groq, Ollama)
│   └── store.py                                 # seen.json dedupe index + tracker CSV export
├── profile.example.json                         # Sample profile JSON for reference
├── requirements.txt                             # Python dependencies
├── seen.json                                    # Dedupe index + application tracker
└── tests/
    ├── __pycache__
    ├── test_llm.py                              # LLM unit tests
    └── test_parsers.py                          # ATS parser unit tests
```

## ⚙️ Tech Stack

- **Backend**: Python, LLMs (Anthropic, OpenAI)
- **Tools**: JSearch API, Scrapy-style parsing, Regex
- **Deployment**: Vercel

## 📄 License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).


## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests to improve features, fix bugs, or suggest enhancements.

## 📜 Credits for Derivatives

If you create a new project or application by modifying or building on top of this code, please include the following in your README:

> This project is based on [Spring Boot Project Generator](https://github.com/callme-ocean/spring-project-generator) created by Sagar Bhadouria </br>
> Licensed under the [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html).

This helps preserve proper attribution while complying with license requirements.

## 🤔 Future Steps

- Improve UI/UX
- Add more ATS platform integrations
- Implement advanced filtering options
- Enhance LLM prompt engineering for better output quality
