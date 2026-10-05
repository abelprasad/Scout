
import os
from core.base import BaseTool
from core.tools.telegram import TelegramTool
import requests
import json

class InstantAlertTool(BaseTool):
    name = "send_instant_alert"
    description = "Send instant alert for urgent new internships. Args: {'jobs': [job_list], 'urgent': True}"

    def __init__(self):
        self.telegram = TelegramTool()

    def execute(self, jobs, urgent=True):
        """Send instant notification for new internships via Telegram"""
        try:
            if not jobs:
                return {"success": True, "data": "No jobs to alert about"}

            # Create alert message
            alert_message = self._format_alert(jobs, urgent)

            # Console output
            print("=" * 60)
            print("🚨 INSTANT INTERNSHIP ALERT 🚨")
            print("=" * 60)
            print(alert_message)
            print("=" * 60)

            # Save alert to file for tracking
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "output", "instant_alerts.log"), "a") as f:
                f.write(f"\n{alert_message}\n{'='*60}\n")

            # Send via Telegram
            telegram_result = self._send_alert(jobs, urgent=urgent)

            if telegram_result["success"]:
                print(f"[InstantAlert] ✅ Telegram notification sent")
            else:
                print(f"[InstantAlert] ⚠️ Telegram failed: {telegram_result.get('error')}")

            return {
                "success": True,
                "data": f"Alert sent for {len(jobs)} new internships",
                "telegram": telegram_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    

    def _send_alert(self, jobs, urgent=False):
        # Format + chunked send (moved from core TelegramTool).
        emoji = "\U0001f6a8" if urgent else "\U0001f4e2"
        header = "{} <b>NEW INTERNSHIPS DETECTED</b> {}\n\n".format(emoji, emoji)
        messages = []
        current_msg = header
        for i, job in enumerate(jobs, 1):
            company = job.get("company", "Unknown")
            position = job.get("position", job.get("title", "Unknown"))
            location = job.get("location", "Unknown")
            url = job.get("url", "")
            entry = "<b>{}. {}</b>\n".format(i, company)
            entry += "   \U0001f4cb {}\n".format(position)
            entry += "   \U0001f4cd {}\n".format(location)
            if url:
                entry += '   \U0001f517 <a href="{}">Apply</a>\n'.format(url)
            entry += "\n"
            if len(current_msg) + len(entry) > 4000:
                messages.append(current_msg)
                current_msg = entry
            else:
                current_msg += entry
        current_msg += "\u26a1 <b>{} new postings</b> - Apply fast!".format(len(jobs))
        messages.append(current_msg)
        for msg in messages:
            result = self.telegram.execute(msg, parse_mode="HTML")
            if not result["success"]:
                return result
        return {"success": True,
                "data": "Sent {} Telegram message(s) with {} internships".format(len(messages), len(jobs))}

    def _format_alert(self, jobs, urgent):
        """Format alert message"""
        timestamp = json.loads(jobs[0]['discovered_at'])[:19] if jobs else "now"
        
        message = f"⚡ DETECTED AT: {timestamp}\n\n"
        
        for i, job in enumerate(jobs, 1):
            message += f"{i}. {job['title']}\n"
            message += f"   🏢 {job['company'].title()}\n"
            message += f"   📍 {job['location']}\n"
            message += f"   🔗 {job['url']}\n"
            message += f"   🏷️ {job['department']}\n\n"
        
        message += f"⚡ APPLY IMMEDIATELY - DETECTED FROM ATS SOURCE\n"
        message += f"🎯 {len(jobs)} NEW POSTINGS FOUND"
        
        return message
