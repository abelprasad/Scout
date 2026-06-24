# docs/LEARNINGS.md — Gotchas & Patterns

## LLM / Agent Loop

**llama3.1:8b JSON parsing failures**
The model occasionally returns freeform text instead of valid JSON despite `format="json"` being set. The agent loop catches `json.JSONDecodeError` and aborts the run. Mitigation: keep the system prompt's format examples as close to the top as possible and repeat the constraint at the bottom.

## Browser Automation

**Playwright `--no-sandbox` required on Linux**
Running Playwright as a non-root user inside certain Linux environments (especially systemd-managed services) requires launching Chromium with `--no-sandbox`. Without it the browser silently fails to start. Set in `BrowserTool` launch args.

## Web Search

**DuckDuckGo rate limits**
Earlier versions used DuckDuckGo search (via `duckduckgo_search` / `ddgs`). It rate-limits aggressively in automated contexts and returns empty results with no error. Replaced with Tavily API (`TAVILY_API_KEY`) which is reliable for agent use.

## Database

**HTML in company names — 876 rows fixed**
GitHub README tables for some repos embed HTML tags (e.g., `<strong>`, `<a href=...>`) inside the company cell. These were ingested raw, polluting the `company` column. Fixed by stripping HTML before insert in `DatabaseTool`. Existing rows were cleaned with a one-off migration script (`fix_urls.py`, `fix_remaining_urls.py`).

**`NULLS LAST` on `age_days` sort**
When sorting by "recently posted" (`age_days ASC`), rows with `age_days IS NULL` bubble to the top in SQLite by default (NULLs sort before any value in ASC order). Use `asc(InternshipListing.age_days).nullslast()` (SQLAlchemy) or `ORDER BY age_days ASC NULLS LAST` (raw SQL) to push them to the bottom.

**`not_applied` vs NULL status filter**
Early rows were inserted without an explicit `application_status`, leaving the column NULL rather than `"not_applied"`. Dashboard filters that check `application_status == "not_applied"` miss these rows. Always filter with `OR application_status IS NULL` when querying for unapplied listings, or run a one-time migration to backfill NULLs to `"not_applied"`.
