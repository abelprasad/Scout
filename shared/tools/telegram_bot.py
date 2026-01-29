import os
import requests
import time
import subprocess
from datetime import datetime
from threading import Thread


class TelegramBot:
    """Telegram bot that listens for commands and triggers actions"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else None
        self.last_update_id = 0
        self.running = False

        self.commands = {
            "/health": self.cmd_health,
            "/status": self.cmd_status,
            "/check": self.cmd_check,
            "/backup": self.cmd_backup,
            "/help": self.cmd_help,
            "/start": self.cmd_help,
        }

    def send_message(self, text, parse_mode="HTML"):
        """Send a message to the configured chat"""
        if not self.base_url or not self.chat_id:
            return False

        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[TelegramBot] Send error: {e}")
            return False

    def get_updates(self):
        """Get new messages from Telegram"""
        if not self.base_url:
            return []

        try:
            response = requests.get(
                f"{self.base_url}/getUpdates",
                params={
                    "offset": self.last_update_id + 1,
                    "timeout": 30
                },
                timeout=35
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("result", [])
        except Exception as e:
            print(f"[TelegramBot] Update error: {e}")

        return []

    def process_update(self, update):
        """Process a single update from Telegram"""
        self.last_update_id = update["update_id"]

        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")

        # Only respond to authorized chat
        if str(chat_id) != str(self.chat_id):
            print(f"[TelegramBot] Ignoring message from unauthorized chat: {chat_id}")
            return

        # Extract command
        command = text.split()[0].lower() if text else ""

        if command in self.commands:
            print(f"[TelegramBot] Executing command: {command}")
            self.commands[command]()
        elif text.startswith("/"):
            self.send_message(f"Unknown command: {command}\n\nUse /help to see available commands.")

    # ========== COMMANDS ==========

    def cmd_help(self):
        """Show available commands"""
        help_text = """<b>AI Agent Control Panel</b>

<b>Commands:</b>
/health - Check if services are running
/status - Show system status and stats
/check - Run internship discovery now
/backup - Backup the database
/help - Show this message

<i>Your internship hunter is ready!</i>"""
        self.send_message(help_text)

    def cmd_health(self):
        """Check health of all services"""
        self.send_message("Checking services...")

        checks = []

        # Check Ollama
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            checks.append(("Ollama", r.status_code == 200))
        except:
            checks.append(("Ollama", False))

        # Check API
        try:
            r = requests.get("http://localhost:8000/", timeout=5)
            checks.append(("AI Agent API", r.status_code == 200))
        except:
            checks.append(("AI Agent API", False))

        # Check Dashboard
        try:
            r = requests.get("http://localhost:8001/", timeout=5)
            checks.append(("Dashboard", r.status_code == 200))
        except:
            checks.append(("Dashboard", False))

        # Format response
        all_ok = all(status for _, status in checks)
        emoji = "✅" if all_ok else "⚠️"

        msg = f"{emoji} <b>Health Check</b>\n\n"
        for name, status in checks:
            icon = "✅" if status else "❌"
            msg += f"{icon} {name}\n"

        msg += f"\n<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
        self.send_message(msg)

    def cmd_status(self):
        """Show system status"""
        self.send_message("Gathering status...")

        try:
            # Get API info
            r = requests.get("http://localhost:8000/", timeout=5)
            api_info = r.json() if r.status_code == 200 else {}

            # Count internships in database
            import sqlite3
            db_path = os.path.expanduser("~/ai-agent/internships.db")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM internship_listings")
            total_internships = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM internship_listings WHERE status = 'applied'")
            applied = cursor.fetchone()[0]
            conn.close()

            msg = f"""<b>System Status</b>

<b>Database:</b>
  Total internships: {total_internships}
  Applied: {applied}

<b>Version:</b> {api_info.get('version', 'Unknown')}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"""

        except Exception as e:
            msg = f"❌ Error getting status: {e}"

        self.send_message(msg)

    def cmd_check(self):
        """Trigger internship discovery workflow"""
        self.send_message("🔍 Starting internship discovery...\n\nThis may take a few minutes.")

        try:
            r = requests.post(
                "http://localhost:8000/run-workflow",
                timeout=600  # 10 min timeout
            )

            if r.status_code == 200:
                result = r.json()
                if result.get("success"):
                    data = result.get("result", {}).get("data", {})
                    msg = f"""✅ <b>Discovery Complete!</b>

Found: {data.get('total_discovered', 'N/A')} internships
New saved: {data.get('new_saved', 'N/A')}
Duplicates: {data.get('duplicates_filtered', 'N/A')}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"""
                else:
                    msg = f"⚠️ Workflow finished with issues:\n{result.get('error', 'Unknown error')}"
            else:
                msg = f"❌ API returned status {r.status_code}"

        except requests.Timeout:
            msg = "⏱️ Workflow is taking longer than expected. Check logs for status."
        except Exception as e:
            msg = f"❌ Error: {e}"

        self.send_message(msg)

    def cmd_backup(self):
        """Backup the database"""
        self.send_message("💾 Creating backup...")

        try:
            db_path = os.path.expanduser("~/ai-agent/internships.db")
            backup_dir = os.path.expanduser("~/ai-agent/backups")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{backup_dir}/internships_{timestamp}.db"

            # Copy database
            import shutil
            shutil.copy2(db_path, backup_path)

            # Get file size
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)

            msg = f"""✅ <b>Backup Complete</b>

File: <code>internships_{timestamp}.db</code>
Size: {size_mb:.2f} MB

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"""

        except Exception as e:
            msg = f"❌ Backup failed: {e}"

        self.send_message(msg)

    # ========== MAIN LOOP ==========

    def run(self):
        """Main polling loop"""
        if not self.bot_token or not self.chat_id:
            print("[TelegramBot] ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
            return

        self.running = True
        print(f"[TelegramBot] Starting bot... Listening for commands.")
        self.send_message("🤖 <b>AI Agent Bot Online</b>\n\nUse /help to see commands.")

        while self.running:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.process_update(update)
            except KeyboardInterrupt:
                print("[TelegramBot] Shutting down...")
                self.running = False
            except Exception as e:
                print(f"[TelegramBot] Error in main loop: {e}")
                time.sleep(5)

    def stop(self):
        """Stop the bot"""
        self.running = False


def main():
    """Run the bot standalone"""
    from dotenv import load_dotenv
    load_dotenv(os.path.expanduser("~/ai-agent/.env"))

    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
