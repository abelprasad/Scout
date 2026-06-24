# docs/CONTEXT.md — Architecture, Stack & Owner Context

## Owner

**Abel Prasad** — CS student at Penn State Abington, graduating December 2026. Based in Northeast Philadelphia, PA.

**Target:** Summer 2026 SWE/full-stack internships. System runs continuously to discover and surface the best matches.

**Resume skills:** Python, FastAPI, Next.js, React, PostgreSQL, SQLite, MongoDB, LLM/RAG, Ollama, Docker, Linux, Playwright, Supabase

**Outreach email:** abelprasad4@gmail.com (configured via `EMAIL_SENDER` in `.env`)

---

## Architecture Overview

```
GitHub/ATS Sources
    ↓
[Scout Agents — Monitor & Extract]
    ↓
Raw internships (company, position, location, url, age_days)
    ↓
[DatabaseTool — Deduplicate & Save]
    ↓
SQLite internship_listings
    ↓
[ResumeMatcher — Score]
    ↓
relevance_score written back to DB
    ↓
[Orchestrator — Notify]
    ├→ Email HTML report → EMAIL_RECIPIENT
    └→ Telegram alert → TELEGRAM_CHAT_ID
    ↓
[Web Dashboard — port 8001]
    └→ Browse, filter, CRUD, trigger new runs
```

---

## Agent Loop (`agent.py`)

The core `Agent` class drives a ReAct-style loop using Ollama (llama3.1:8b). It maintains `conversation_history`, calls tools based on JSON responses from the LLM, and caps execution at 15 iterations.

LLM must respond with exactly one of:
- `{"tool": "tool_name", "args": {...}}` — execute a tool
- `{"done": true, "summary": "..."}` — signal completion

---

## Tool System

All tools extend `BaseTool` (`shared/tools/base.py`) and must implement:
```python
def execute(self, **kwargs) -> dict:
    # Returns {"success": True, "data": ...} or {"success": False, "error": ...}
```

Tools are registered by passing instances to `Agent(tools=[...])`.

### Shared Tools (`shared/tools/`)

| File | Tool name | What it does |
|------|-----------|--------------|
| `websearch.py` | `web_search` | Tavily API, returns 10 results |
| `browser.py` | `browser_action` | Playwright headless Chrome; `extract_text` or `screenshot` |
| `database.py` | `save_to_database` / `query_database` | SQLAlchemy CRUD on `InternshipListing` |
| `email_tool.py` | `send_email` | Gmail SMTP via starttls on port 587 |
| `telegram.py` | `send_telegram` | HTTP POST to Telegram Bot API |
| `telegram_bot.py` | — | Standalone polling bot; handles `/health`, `/status`, `/check`, `/backup` commands |
| `filesystem.py` | `write_file` | Writes to `output/` directory |

### Scout Agents (`agents/scout/`)

**`github_monitor.py` — `GitHubInternshipMonitor`**

Monitors 5 GitHub repos via the GitHub API, fetches raw README markdown, and parses internship tables with 6 regex patterns:

1. SimplifyJobs HTML `<tr><td><strong><a>` format — extracts `age_days`
2. Markdown `| [Company](url) | Position | Location | [Apply](url) |`
3. Simple markdown `| Company | Position | Location | [Apply](url) |`
4. VanshB03 HTML with `<img alt="Apply">` links
5. Summer2026 `[Apply Here](url)` variant
6. Canadian badge-link `[![Apply](badge)](url)` variant

Repos tracked: SimplifyJobs, Pitt-CSC, SpeedyApply, VanshB03, Summer2026. Default limit: 500 per run.

**`github_monitor.py` — `GitHubChangeDetector`**

Wraps `GitHubInternshipMonitor`; checks DB for URL uniqueness and flags truly new postings for alerts.

**`ats_monitor.py` — `ATSMonitorTool` / `ATSChangeDetectorTool`**

Hits Greenhouse ATS JSON endpoints (`{base_url}/jobs?format=json`) for: stripe, reddit, twitch, robinhood, coinbase, square, dropbox, notion. Filters by internship keywords. Parsing reliability varies by employer.

**`instant_alert.py` — `InstantAlertTool`**

Sends immediate Telegram alerts on new discoveries. Auto-splits messages at 4000 chars. Also logs to `output/instant_alerts.log`.

### Analyzer Agent (`agents/analyzer/`)

**`resume_matcher.py` — `ResumeMatcher`**

Loads `~/ai-agent/resume.txt`; falls back to a hardcoded default skill list if missing.

**Scoring v1 — current formula (0–100):**

```
IF any NEGATIVE_KEYWORD in title → return 2.0

role_score  = min(35,  role_hits_in_text×5  + role_hits_in_title×8)
skill_score = min(45,  title_skill_hits×3   + body_skill_hits×1)
company_score = 15 if company in BONUS_COMPANIES else 0

final = min(100, 5 + role_score + skill_score + company_score)
```

Key lists: `CORE_SKILLS` (30 items), `ROLE_KEYWORDS` (8 patterns), `NEGATIVE_KEYWORDS` (hardware/PhD/clearance), `BONUS_COMPANIES` (25+ tier-1 names).

**Scoring v2 — planned (0–10 scale):**

| Dimension | Max | Rule |
|-----------|-----|------|
| Resume skill match | 6 | Match against Abel's actual resume skills |
| Location | 2 | Remote / NYC / Philly / relocation-friendly |
| Recency | 2 | `age_days <= 14`; penalize stale posts |

Sort order: `relevance_score DESC`, then `discovered_at DESC`.

Auto cold-email threshold: score >= 7.0.

### Orchestrator (`agents/orchestrator/orchestrator_agent.py`)

`OrchestratorAgent` is itself a `BaseTool` (`name = "orchestrate_workflow"`). This is what `POST /run-workflow` invokes directly (bypassing the LLM loop).

Pipeline:
1. `GitHubInternshipMonitor.execute()` — discover
2. `DatabaseTool.execute()` — deduplicate and save
3. `ResumeMatcher.execute()` — score all unscored rows
4. Email HTML report (top matches ≥ 20, all new listings up to 50)
5. Telegram alert for first 5 matches scoring ≥ 30

### Stub Agents (not yet implemented)

- `agents/quality/` — intended for post-discovery review/filtering
- `agents/applicant/` — intended for auto-application

---

## Interfaces

**`interfaces/api/main.py`** — FastAPI on port 8000

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/jobs` | Submit natural-language goal; runs `Agent` in `BackgroundTask` |
| GET | `/jobs/{job_id}` | Poll job status |
| GET | `/` | System info |
| POST | `/run-workflow` | Directly invoke `OrchestratorAgent` (no LLM) |

Job state is in-memory (`jobs = {}`); lost on restart.

**`interfaces/web/web_dashboard.py`** — FastAPI on port 8001

Dark-themed HTML dashboard. Supports search, status filter, sort (best match / recently posted / recently found / A-Z), CRUD modals, "Mark Applied", and "Run Scout" (proxies to `POST localhost:8000/run-workflow`).

Internal API routes: `/api/stats`, `/api/internships`, `/api/internships/{id}` (GET/PUT/DELETE), `/api/internships/{id}/apply`, `/api/run-scout`.

---

## Database Schema (`shared/database/database.py`)

SQLite at `internships.db` (path resolved relative to project root — portable).

**`internship_listings`**

| Column | Type | Notes |
|--------|------|-------|
| id | Integer PK | |
| agent_job_id | String | Links to `AgentJob` that found it |
| title | String | |
| company | String | Strip HTML before insert |
| url | String UNIQUE | Primary dedup key |
| location | String | |
| description | Text | Capped at ~500 chars from GitHub sources |
| requirements | Text | Usually empty from GitHub |
| deadline | String | |
| salary_min / salary_max | Float nullable | |
| discovered_at | DateTime | Auto: utcnow |
| applied | Boolean | Default False |
| application_date | DateTime nullable | Set when status → applied |
| application_status | String | `not_applied` → `applied` → `interviewing` → `rejected` / `offer` |
| notes | Text | |
| relevance_score | Float | v1: 0–100; v2 target: 0–10 (default 0.0) |
| interest_level | Integer | 1–5 scale (default 0) |
| age_days | Integer nullable | Days since GitHub posting (Pattern 1 only) |

**`agent_jobs`**

| Column | Type |
|--------|------|
| job_id | String UNIQUE |
| goal | Text |
| status | String (`queued` / `running` / `completed` / `failed`) |
| result_summary | Text |
| created_at / completed_at | DateTime |

**Missing table (needed before outreach):** `outreach_logs` — must be added to `database.py` before the auto cold-email pipeline is enabled.

---

## Outreach Rules

- Threshold: score >= 7.0 (v2 scale)
- Send from: abelprasad4@gmail.com
- Never email the same company twice — check `outreach_logs` before every send
- `outreach_logs` table does not yet exist; create it as part of the outreach deployment task

---

## Path Notes

`interfaces/api/main.py` hard-codes `sys.path.append('/home/abel/ai-agent')`. If the project is moved, update these. `shared/database/database.py` uses `__file__`-relative resolution and is portable.
