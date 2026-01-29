import os
import requests
from .base import BaseTool


class TelegramTool(BaseTool):
    name = "send_telegram"
    description = "Send a Telegram message. Args: {'message': 'text to send', 'parse_mode': 'HTML' or 'Markdown' (optional)}"

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None

    def execute(self, message, parse_mode=None):
        """Send a message via Telegram bot"""
        try:
            if not self.bot_token or not self.chat_id:
                return {
                    "success": False,
                    "error": "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env"
                }

            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "disable_web_page_preview": False
            }

            if parse_mode:
                payload["parse_mode"] = parse_mode

            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": "Telegram message sent"
                }
            else:
                return {
                    "success": False,
                    "error": f"Telegram API error: {response.text}"
                }

        except requests.Timeout:
            return {
                "success": False,
                "error": "Telegram request timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def send_internship_alert(self, internships, urgent=False):
        """Send formatted internship alert"""
        if not internships:
            return {"success": True, "data": "No internships to alert"}

        emoji = "🚨" if urgent else "📢"
        header = f"{emoji} <b>NEW INTERNSHIPS DETECTED</b> {emoji}\n\n"

        messages = []
        current_msg = header

        for i, job in enumerate(internships, 1):
            company = job.get('company', 'Unknown')
            position = job.get('position', job.get('title', 'Unknown'))
            location = job.get('location', 'Unknown')
            url = job.get('url', '')

            entry = f"<b>{i}. {company}</b>\n"
            entry += f"   📋 {position}\n"
            entry += f"   📍 {location}\n"
            if url:
                entry += f"   🔗 <a href=\"{url}\">Apply</a>\n"
            entry += "\n"

            # Telegram has 4096 char limit - split if needed
            if len(current_msg) + len(entry) > 4000:
                messages.append(current_msg)
                current_msg = entry
            else:
                current_msg += entry

        current_msg += f"⚡ <b>{len(internships)} new postings</b> - Apply fast!"
        messages.append(current_msg)

        # Send all message chunks
        results = []
        for msg in messages:
            result = self.execute(msg, parse_mode="HTML")
            results.append(result)
            if not result["success"]:
                return result

        return {
            "success": True,
            "data": f"Sent {len(messages)} Telegram message(s) with {len(internships)} internships"
        }
