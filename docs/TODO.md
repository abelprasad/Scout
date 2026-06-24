# docs/TODO.md — Current Tasks

## Done

- [x] **Deploy ResumeMatcher v2** — Live as of 2026-05-09. `agents/analyzer/resume_matcher.py` now uses the 0–10 rubric (skill categories + location + recency). PDF parsing via `pypdf` reads `resume.pdf` directly.

- [x] **Rescore existing listings** — All 5,947 rows rescored on v2. `relevance_score` column holds v2 values.

## In Progress / Next Up

- [ ] **Add `outreach_logs` table** — Add a new SQLAlchemy model to `shared/database/database.py`. Minimum columns: `id`, `company` (string), `email_address` (string), `sent_at` (datetime), `internship_id` (FK to `internship_listings`), `status` (sent / bounced / replied).

- [ ] **Wire outreach into orchestrator** — After scoring in `OrchestratorAgent.execute()`, query listings with `relevance_score >= 7.0` and `application_status == "not_applied"`, check `outreach_logs` for prior contact with that company, then send cold email via `EmailTool`.

- [ ] **Test dry_run mode** — Add a `dry_run=True` flag to the outreach step so the orchestrator can log what it *would* send without actually emailing. Verify deduplication logic against `outreach_logs`.
