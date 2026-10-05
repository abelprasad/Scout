import os
import requests
from core.base import BaseTool


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
