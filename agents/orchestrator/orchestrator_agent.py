import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.tools.base import BaseTool
from agents.scout.github_monitor import GitHubInternshipMonitor, GitHubChangeDetector
from shared.tools.database import DatabaseTool, DatabaseQueryTool
from agents.scout.instant_alert import InstantAlertTool
from shared.tools.email_tool import EmailTool
from agents.analyzer.resume_matcher import ResumeMatcher
from datetime import datetime

class OrchestratorAgent(BaseTool):
    name = "orchestrate_workflow"
    description = "Orchestrates proven multi-agent workflow: GitHub discovery → Database saving → Notifications"
    
    def __init__(self):
        self.github_monitor = GitHubInternshipMonitor()
        self.database_tool = DatabaseTool()
        self.email_tool = EmailTool()
        self.resume_matcher = ResumeMatcher()
    
    def execute(self, workflow_type="full", repos=None, agent_job_id=None):
        """Execute the proven workflow that we know works"""
        try:
            print(f"[Orchestrator] 🚀 Starting proven workflow...")
            
            # Step 1: GitHub Discovery (PROVEN TO WORK)
            print(f"[Orchestrator] Step 1: GitHub Discovery")
            discovery = self.github_monitor.execute(repos=repos, limit=500)  # Uses all repos by default
            
            if not discovery["success"]:
                return {"success": False, "error": f"Discovery failed: {discovery.get('error')}"}
            
            total_found = discovery["data"]["total_internships"]
            print(f"[Orchestrator] ✅ Discovered {total_found} internships")
            
            # Step 2: Extract Sample Internships for Saving
            all_samples = []
            for repo_data in discovery["data"]["repo_data"]:
                all_samples.extend(repo_data["sample_internships"])
            
            if not all_samples:
                return {"success": True, "data": {"message": "No internships to save"}}
            
            # Step 3: Database Saving (PROVEN TO WORK) 
            print(f"[Orchestrator] Step 2: Database Saving ({len(all_samples)} internships)")
            
            # Format internships correctly (matching the working format)
            formatted_internships = []
            for internship in all_samples:
                formatted_internships.append({
                    'company': internship['company'],
                    'position': internship['position'],
                    'location': internship['location'],
                    'url': internship['url'],
                    'source': internship['source'],
                    'age_days': internship.get('age_days')
                })
            
            db_result = self.database_tool.execute(
                internships=formatted_internships,
                agent_job_id=agent_job_id or "orchestrator"
            )
            
            if not db_result["success"]:
                return {"success": False, "error": f"Database save failed: {db_result.get('error')}"}
            
            saved_count = db_result["data"]["saved_count"]
            duplicate_count = db_result["data"]["duplicate_count"]
            print(f"[Orchestrator] ✅ Saved {saved_count} new internships ({duplicate_count} duplicates)")

            # Step 4: Resume Matching - Score internships
            print(f"[Orchestrator] Step 3: Resume Matching")
            match_result = self.resume_matcher.execute()
            scored_count = match_result.get("data", {}).get("scored_count", 0) if match_result["success"] else 0
            print(f"[Orchestrator] ✅ Scored {scored_count} internships based on resume")

            # Step 5: Success Summary Email + Telegram
            print(f"[Orchestrator] Step 4: Success Summary")

            from shared.database.database import get_db_session, InternshipListing
            from datetime import datetime as dt, timedelta
            notif_session = get_db_session()
            recent_cutoff = dt.utcnow() - timedelta(hours=2)
            top_new = notif_session.query(InternshipListing)\
                .filter(InternshipListing.discovered_at >= recent_cutoff)\
                .filter(InternshipListing.relevance_score >= 20)\
                .order_by(InternshipListing.relevance_score.desc())\
                .limit(10).all()
            all_new = notif_session.query(InternshipListing)\
                .filter(InternshipListing.discovered_at >= recent_cutoff)\
                .order_by(InternshipListing.relevance_score.desc())\
                .limit(50).all()
            notif_session.close()

            now_str = dt.now().strftime("%B %d, %Y at %I:%M %p")

            listings_html = ""
            for internship in top_new:
                score_color = "#16a34a" if internship.relevance_score >= 30 else "#ca8a04"
                listings_html += f'''<tr>
<td style="padding:12px;border-bottom:1px solid #27272a;">
<a href="{internship.url or chr(35)}" style="color:#fafafa;font-weight:600;text-decoration:none;">{internship.title}</a><br>
<span style="color:#a1a1aa;font-size:13px;">{internship.company} · {internship.location or "Location N/A"}</span>
</td>
<td style="padding:12px;border-bottom:1px solid #27272a;text-align:right;">
<span style="background:{score_color};color:white;padding:3px 8px;border-radius:4px;font-size:12px;">{internship.relevance_score:.0f}%</span>
</td></tr>'''
            if not listings_html:
                listings_html = "<tr><td colspan=2 style='padding:20px;text-align:center;color:#71717a;'>No high-scoring new listings this run</td></tr>"

            all_rows = ""
            for internship in all_new:
                all_rows += f'''<tr>
<td style="padding:8px 12px;border-bottom:1px solid #1c1c1f;font-size:13px;">
<a href="{internship.url or chr(35)}" style="color:#a1a1aa;text-decoration:none;">{internship.title}</a></td>
<td style="padding:8px 12px;border-bottom:1px solid #1c1c1f;font-size:12px;color:#71717a;">{internship.company}</td>
<td style="padding:8px 12px;border-bottom:1px solid #1c1c1f;font-size:12px;color:#71717a;text-align:right;">{internship.relevance_score:.0f}%</td>
</tr>'''

            all_section = f'''<div style="background:#18181b;border:1px solid #27272a;border-radius:8px;margin-bottom:24px;">
<div style="padding:16px 20px;border-bottom:1px solid #27272a;"><h2 style="color:#fafafa;font-size:14px;margin:0;">All New Listings</h2></div>
<table style="width:100%;border-collapse:collapse;">
<tr style="background:#0f0f10;">
<th style="padding:8px 12px;text-align:left;font-size:11px;color:#71717a;">Title</th>
<th style="padding:8px 12px;text-align:left;font-size:11px;color:#71717a;">Company</th>
<th style="padding:8px 12px;text-align:right;font-size:11px;color:#71717a;">Match</th>
</tr>{all_rows}</table></div>''' if all_rows else ""

            email_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,sans-serif;">
<div style="max-width:600px;margin:0 auto;padding:40px 20px;">
<h1 style="color:#fafafa;font-size:22px;margin:0 0 4px 0;">Scout Report</h1>
<p style="color:#71717a;font-size:13px;margin:0 0 32px 0;">{now_str}</p>
<div style="display:flex;gap:12px;margin-bottom:32px;">
<div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center;">
<div style="font-size:28px;font-weight:700;color:#fafafa;">{saved_count}</div>
<div style="font-size:11px;color:#71717a;text-transform:uppercase;">New Found</div></div>
<div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center;">
<div style="font-size:28px;font-weight:700;color:#fafafa;">{len(top_new)}</div>
<div style="font-size:11px;color:#71717a;text-transform:uppercase;">Strong Matches</div></div>
<div style="flex:1;background:#18181b;border:1px solid #27272a;border-radius:8px;padding:16px;text-align:center;">
<div style="font-size:28px;font-weight:700;color:#fafafa;">{total_found}</div>
<div style="font-size:11px;color:#71717a;text-transform:uppercase;">Scanned</div></div></div>
<div style="background:#18181b;border:1px solid #27272a;border-radius:8px;margin-bottom:24px;">
<div style="padding:16px 20px;border-bottom:1px solid #27272a;"><h2 style="color:#fafafa;font-size:14px;margin:0;">Top Matches</h2></div>
<table style="width:100%;border-collapse:collapse;">{listings_html}</table></div>
{all_section}
<div style="text-align:center;padding:20px;">
<a href="http://100.98.50.85:8001" style="background:#fafafa;color:#0a0a0a;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600;">Open Dashboard</a>
</div></div></body></html>"""

            subject = f"Scout: {saved_count} new internships found" if saved_count > 0 else "Scout: No new listings this run"
            email_result = self.email_tool.execute(subject=subject, body=email_html, html=True)

            try:
                from shared.tools.telegram_bot import TelegramBot
                if saved_count > 0:
                    tg = TelegramBot()
                    high = [i for i in top_new if i.relevance_score >= 30]
                    tg_msg = f"<b>Scout: {saved_count} new internships found</b>\n\n"
                    if high:
                        tg_msg += "<b>Top matches:</b>\n"
                        for i in high[:5]:
                            tg_msg += f"• {i.title} @ {i.company} ({i.relevance_score:.0f}%)\n"
                    tg_msg += "\nhttp://100.98.50.85:8001"
                    tg.send_message(tg_msg)
            except Exception as tg_err:
                print(f"[Orchestrator] Telegram alert error: {tg_err}")

            
            return {
                "success": True,
                "data": {
                    "total_discovered": total_found,
                    "new_saved": saved_count,
                    "duplicates_filtered": duplicate_count,
                    "scored_count": scored_count,
                    "email_sent": email_result["success"],
                    "workflow_complete": True
                }
            }
            
        except Exception as e:
            print(f"[Orchestrator] ❌ Error: {str(e)}")
            return {"success": False, "error": f"Orchestrator error: {str(e)}"}
