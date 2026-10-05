# Scout

A self-hosted, mission-agnostic agent framework. Scout runs autonomous
discovery workflows: find things on the web, score them, store them,
and alert you about the good ones — for whatever mission you plug in.

## How it works

```
discover  →  dedupe/save  →  score  →  notify
```

The **core engine** (`core/`) is fully domain-agnostic. It provides:

- **Agent loop** (`core/agent.py`) — a ReAct-style LLM loop (Ollama) that
  pursues natural-language goals using registered tools.
- **Mission runner** (`core/orchestrator.py`) — the scheduled workflow:
  runs a mission's discovery tools, dedupes + saves results, scores them,
  then sends email/Telegram reports. Also exposed as the `run_mission` tool.
- **Tool layer** (`core/tools/`) — headless browser (Playwright), web search
  (Tavily), email (SMTP), filesystem, Telegram send, plus generic
  database save/query tools.
- **Storage** (`core/database.py`) — SQLite via SQLAlchemy, per-mission
  database files, shared `agent_jobs` table.
- **API** (`core/interfaces/api.py`) — FastAPI on :8000: `POST /jobs`
  (natural-language goal), `GET /jobs/{id}`, `POST /run-workflow`
  (direct mission run, used by cron).
- **Dashboard** (`core/interfaces/dashboard.py`) — FastAPI on :8001: a
  schema-driven CRUD UI (search, filter, sort, add/edit/delete, status
  workflow, run-mission button) rendered from the mission's field spec.
- **Telegram bot** (`core/tools/telegram_bot.py`) — long-polling command
  bot (`/health`, `/check`, `/backup`, `/help`); missions add their own
  commands.

A **mission** (`missions/<name>/`) is a plugin that defines the domain:

| Piece | What it defines |
|---|---|
| `mission.py` → `class Mission(MissionPlugin)` | identity, discovery tools, scoring, storage schema mapping, report formatting, dashboard fields, bot commands |
| `models.py` | SQLAlchemy model for discovered items |
| discovery / scoring / alerts | mission-specific tools and logic |

The active mission is selected with the `ACTIVE_MISSION` env var
(default: `internships`).

## Missions

- **`internships`** (reference mission) — discovers software internships
  from GitHub listing repos and company ATS boards, scores them against a
  resume with skill/location/recency weighting, and reports top matches
  via email + Telegram. Dashboard: "Internship Database".

## Running

Services (systemd, currently installed):

- `scout-api` — API on :8000 (`interfaces/api/main.py`)
- `scout-dashboard` — dashboard on :8001 (`interfaces/web/web_dashboard.py`)
- `scout-telegram` — Telegram command bot (`core/tools/telegram_bot.py`)

```bash
sudo systemctl start scout-api scout-dashboard scout-telegram
```

Scheduled workflow (`scripts/crontab.txt`): `run-workflow.sh` POSTs to
`:8000/run-workflow` at 8 AM / 6 PM; database backup at 3 AM.

## Adding a new mission

1. Create `missions/<name>/` with `mission.py` defining
   `class Mission(MissionPlugin)` and `models.py` with your SQLAlchemy model.
2. Implement the abstract members: `model`, `discovery_tools()`,
   `normalize_items()`, `save_new_items()`, `scorer()`,
   `recent_highlights()`, `format_report_html()`,
   `format_telegram_message()`, `dashboard_title`, `list_fields`.
   See `missions/internships/` for the complete reference.
3. Set `ACTIVE_MISSION=<name>` in `.env` and restart the services.

No changes to `core/` are needed — that is the point.
