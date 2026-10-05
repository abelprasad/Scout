# Generic mission runner: discover -> dedupe/save -> score -> notify.
# Zero domain logic: every domain decision is delegated to the mission plugin.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base import BaseTool
from core.tools.email import EmailTool
from core.tools.telegram import TelegramTool
from datetime import datetime


class MissionRunner:
    def __init__(self, mission=None):
        if mission is None:
            from core.mission import load_mission
            mission = load_mission()
        self.mission = mission
        self.email = EmailTool()
        self.telegram = TelegramTool()

    def execute(self, job_id=None):
        mission = self.mission
        job_id = job_id or "mission-run"
        session = None
        try:
            print("[MissionRunner] Starting mission '{}'...".format(mission.name))

            # 1. Discovery
            raw_items = []
            for tool in mission.discovery_tools():
                print("[MissionRunner] Discovery: {}".format(tool.name))
                try:
                    res = tool.execute()
                except Exception as e:
                    print("[MissionRunner] Discovery tool {} raised: {}".format(tool.name, e))
                    continue
                if res.get("success"):
                    raw_items.extend(mission.normalize_items(tool.name, res.get("data", {})))
                else:
                    print("[MissionRunner] Discovery tool {} failed: {}".format(tool.name, res.get("error")))
            print("[MissionRunner] Discovered {} raw items".format(len(raw_items)))

            # 2. Dedupe + save
            session = mission.get_session()
            saved = mission.save_new_items(session, raw_items, job_id)
            print("[MissionRunner] Saved {} new ({} duplicates)".format(
                saved["saved_count"], saved["duplicate_count"]))

            # 3. Score
            score_res = mission.scorer().execute()
            scored = score_res.get("data", {}).get("scored_count", 0) if score_res.get("success") else 0
            print("[MissionRunner] Scored {} items".format(scored))

            # 4. Notify
            highlights = mission.recent_highlights(session, hours=2, limit=10)
            stats = {
                "total_discovered": len(raw_items),
                "new_saved": saved["saved_count"],
                "duplicates_filtered": saved["duplicate_count"],
                "scored_count": scored,
                "mission": mission.display_name,
                "run_at": datetime.now(),
            }
            subject, html = mission.format_report_html(stats, highlights)
            email_res = self.email.execute(subject=subject, body=html, html=True)
            tg_msg = mission.format_telegram_message(stats, highlights)
            tg_res = self.telegram.execute(tg_msg, parse_mode="HTML")
            session.close()
            session = None

            stats["email_sent"] = bool(email_res.get("success"))
            stats["telegram_sent"] = bool(tg_res.get("success"))
            stats["run_at"] = stats["run_at"].isoformat()
            return {"success": True, "data": stats}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass


class RunMissionTool(BaseTool):
    name = "run_mission"
    description = "Run the active mission's full workflow: discover, save, score, notify."

    def __init__(self, mission=None):
        self._mission = mission

    def execute(self, job_id=None):
        return MissionRunner(self._mission).execute(job_id=job_id)
