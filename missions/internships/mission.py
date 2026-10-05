# Internships mission: the reference MissionPlugin implementation.
# Discovers software internships from GitHub repos + ATS boards, scores them
# against a resume, and reports via email/Telegram/dashboard.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime as dt, timedelta

from core.mission import MissionPlugin
from missions.internships.models import InternshipListing, get_db_session


class Mission(MissionPlugin):
    name = "internships"
    display_name = "Internship Hunter"
    description = (
        "Discovers software internships from GitHub listing repos and "
        "company ATS boards, scores them against your resume, and alerts "
        "you to the best matches."
    )

    # ---- storage ----
    @property
    def model(self):
        return InternshipListing

    @property
    def db_filename(self):
        return "internships.db"

    # ---- discovery ----
    def discovery_tools(self):
        from missions.internships.github_monitor import GitHubInternshipMonitor
        from missions.internships.ats_monitor import ATSMonitorTool
        return [GitHubInternshipMonitor(), ATSMonitorTool()]

    def normalize_items(self, tool_name, result_data):
        items = []
        if tool_name == "monitor_github_internships":
            for repo in result_data.get("repo_data", []):
                for it in repo.get("sample_internships", []):
                    items.append({
                        "title": it.get("position", ""),
                        "company": it.get("company", ""),
                        "location": it.get("location", ""),
                        "url": it.get("url", ""),
                        "description": "",
                        "source": it.get("source", "GitHub"),
                        "age_days": it.get("age_days"),
                    })
        elif tool_name == "monitor_ats":
            for job in result_data.get("jobs", []):
                items.append({
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "location": job.get("location", ""),
                    "url": job.get("url", ""),
                    "description": job.get("description", ""),
                    "source": job.get("ats_source", "ATS"),
                    "age_days": None,
                })
        return items

    # ---- persistence ----
    def save_new_items(self, session, items, job_id):
        import re
        saved_count = 0
        duplicate_count = 0
        for data in items:
            if not isinstance(data, dict):
                continue
            title = data.get("title", "")
            company_raw = data.get("company", "")
            company = re.sub(r"<[^>]+>", "", company_raw).strip() if company_raw else ""
            url = data.get("url", "")
            if not title or not company:
                continue
            existing = session.query(InternshipListing).filter(
                (InternshipListing.url == url) |
                ((InternshipListing.title == title) & (InternshipListing.company == company))
            ).first()
            if existing:
                duplicate_count += 1
                continue
            age = data.get("age_days")
            try:
                age_days = int(age) if age not in (None, "") else None
            except (TypeError, ValueError):
                age_days = None
            row = InternshipListing(
                agent_job_id=job_id or "mission",
                title=title,
                company=company,
                url=url,
                location=data.get("location", ""),
                description=(data.get("description", "") or "")[:500],
                requirements="",
                deadline="",
                application_status="not_applied",
                applied=False,
                discovered_at=dt.utcnow(),
                age_days=age_days,
            )
            session.add(row)
            saved_count += 1
        session.commit()
        return {"saved_count": saved_count, "duplicate_count": duplicate_count}

    # ---- scoring ----
    def scorer(self):
        from missions.internships.scoring import ResumeMatcher
        return ResumeMatcher()

    def agent_tools(self):
        from missions.internships.instant_alert import InstantAlertTool
        return [self.scorer(), InstantAlertTool()]

    # ---- reporting ----
    def recent_highlights(self, session, hours=2, limit=10):
        cutoff = dt.utcnow() - timedelta(hours=hours)
        return (
            session.query(InternshipListing)
            .filter(InternshipListing.discovered_at >= cutoff)
            .filter(InternshipListing.relevance_score >= 20)
            .order_by(InternshipListing.relevance_score.desc())
            .limit(limit)
            .all()
        )

    def _recent_items(self, session, hours=2, limit=50):
        cutoff = dt.utcnow() - timedelta(hours=hours)
        return (
            session.query(InternshipListing)
            .filter(InternshipListing.discovered_at >= cutoff)
            .order_by(InternshipListing.relevance_score.desc())
            .limit(limit)
            .all()
        )

    @property
    def dashboard_url(self):
        return os.getenv("DASHBOARD_URL", "http://localhost:8001")

    def format_report_html(self, stats, highlights):
        from missions.internships.alerts import build_report_html
        session = get_db_session()
        try:
            recent = self._recent_items(session)
            return build_report_html(stats, highlights, recent, self.dashboard_url)
        finally:
            session.close()

    def format_telegram_message(self, stats, highlights):
        from missions.internships.alerts import build_telegram_message
        return build_telegram_message(stats, highlights, self.dashboard_url)

    # ---- dashboard ----
    @property
    def dashboard_title(self):
        return "Internship Database"

    @property
    def list_fields(self):
        return [
            {"key": "title", "label": "Title", "type": "title"},
            {"key": "company", "label": "Company", "type": "subtitle"},
            {"key": "location", "label": "Location", "type": "meta"},
            {"key": "url", "label": "Posting", "type": "link"},
            {"key": "relevance_score", "label": "Score", "type": "score"},
            {"key": "discovered_at", "label": "Found", "type": "date"},
            {"key": "age_days", "label": "Posted", "type": "age"},
        ]

    @property
    def searchable_fields(self):
        return ["title", "company", "description"]

    @property
    def status_field(self):
        return "application_status"

    @property
    def status_options(self):
        return ["not_applied", "applied", "interviewing", "rejected", "offer"]

    def on_status_change(self, item, new_status, session):
        if new_status == "applied" and not item.applied:
            item.applied = True
            item.application_date = dt.utcnow()

    # ---- telegram bot ----
    def telegram_commands(self):
        return {
            "/status": ("Show database stats", self.cmd_status),
        }

    def cmd_status(self):
        import requests
        from core.tools.telegram import TelegramTool
        tg = TelegramTool()
        try:
            session = get_db_session()
            total = session.query(InternshipListing).count()
            applied = session.query(InternshipListing).filter_by(application_status="applied").count()
            session.close()
            msg = (
                "<b>System Status</b>\n\n<b>Database:</b>\n"
                "  Total internships: {}\n  Applied: {}\n\n<i>{}</i>".format(
                    total, applied, dt.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        except Exception as e:
            msg = "Error getting status: {}".format(e)
        tg.execute(msg, parse_mode="HTML")
