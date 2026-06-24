# docs/HANDOFF.md — Current System State

_Last updated: 2026-05-09_

## Session summary (2026-05-09)

- `docs/` directory created with `CONTEXT.md`, `TODO.md`, `LEARNINGS.md`, `HANDOFF.md`
- `resume.pdf` uploaded to `~/ai-agent/resume.pdf`; `pypdf` installed into venv
- ResumeMatcher v2 deployed (`agents/analyzer/resume_matcher.py`) — 0–10 scale, skill categories + location + recency
- All 5,947 listings rescored under v2

## Database

- **Total listings:** 5,947
- **Applied:** 2
- **Scoring:** v2 live. `relevance_score` is now 0–10 (v1's 0–100 values are gone).

### Sanity check (2026-05-09)

| Metric | Value |
|--------|-------|
| Total listings | 5,947 |
| Min score | 0.0 |
| Max score | 5.0 |
| Avg score | 1.382 |
| Scored 0.0 (dealbreakers) | 710 |
| Scored > 4.0 (strong matches) | 76 |

### Score ceiling note (expected behaviour, not a bug)

Current top score is **5.0**. Best-case breakdown: 2.0 recency (age_days=0) + 1.5 location (PA/NJ/DE/NYC) + 1.5 strong title match = 5.0. Skill-category points (0–4.5) land near 0 for GitHub-sourced listings because README tables only store company/title/location — no description body for skill terms to match against. Scores above 5.0 will appear naturally as ATS listings or manually-added entries with richer descriptions accumulate.

## Running Services

| Service | Port | Status |
|---------|------|--------|
| FastAPI agent API | 8000 | Running |
| Web dashboard | 8001 | Running |
| Telegram bot | — | Running (long-polling) |
| Cron (8 AM + 6 PM daily) | — | Active via crontab |

Dashboard accessible at `http://100.98.50.85:8001` from local network.

## Outreach Pipeline

- Design is complete (threshold, dedup logic, email format documented in `docs/CONTEXT.md`)
- **Not yet deployed to indra** (the production host)
- Blocked on: `outreach_logs` table not yet created (v2 scorer is now live)
- See `docs/TODO.md` for the step-by-step deployment tasks

## Discovery Sources

All 5 GitHub repos are being polled. ATS monitoring (Greenhouse endpoints) is wired up but parsing reliability varies by employer — treat ATS results as supplementary.

## Known Gaps

- `agents/quality/` and `agents/applicant/` are empty stubs
- `agent_jobs` table in the DB is populated only when goals are submitted via `POST /jobs`; `/run-workflow` calls the orchestrator directly and does not write to `agent_jobs`
- In-memory `jobs = {}` dict in the API is lost on restart — no job history persists across restarts
