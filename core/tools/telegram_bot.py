# Generic Telegram command bot.
#
# Core commands (/health, /check, /backup, /help) work for any mission.
# Missions contribute extra commands via MissionPlugin.telegram_commands(),
# which maps "/cmd" -> (description, handler_fn).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import requests
import time
import shutil
from datetime import datetime


class TelegramCommandBot(object):
    def __init__(self, mission=None):
        if mission is None:
            from core.mission import load_mission
            mission = load_mission()
        self.mission = mission
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = (
            "https://api.telegram.org/bot{}".format(self.bot_token)
            if self.bot_token else None
        )
        self.last_update_id = 0
        self.running = False
        self.commands = {
            "/health": (self.cmd_health, "Check if services are running"),
            "/check": (self.cmd_check, "Run the active mission workflow now"),
            "/backup": (self.cmd_backup, "Backup the mission database"),
            "/help": (self.cmd_help, "Show this message"),
            "/start": (self.cmd_help, "Show this message"),
        }
        for cmd, spec in self.mission.telegram_commands().items():
            self.commands[cmd] = spec

    # ---------- transport ----------
    def send_message(self, text, parse_mode="HTML"):
        if not self.base_url or not self.chat_id:
            return False
        try:
            r = requests.post(
                "{}/sendMessage".format(self.base_url),
                json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
                timeout=10,
            )
            return r.status_code == 200
        except Exception as e:
            print("[TelegramBot] Send error: {}".format(e))
            return False

    def get_updates(self):
        if not self.base_url:
            return []
        try:
            r = requests.get(
                "{}/getUpdates".format(self.base_url),
                params={"offset": self.last_update_id + 1, "timeout": 30},
                timeout=35,
            )
            if r.status_code == 200 and r.json().get("ok"):
                return r.json().get("result", [])
        except Exception as e:
            print("[TelegramBot] Update error: {}".format(e))
        return []

    def process_update(self, update):
        self.last_update_id = update["update_id"]
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        if str(chat_id) != str(self.chat_id):
            print("[TelegramBot] Ignoring message from unauthorized chat: {}".format(chat_id))
            return
        command = text.split()[0].lower() if text else ""
        if command in self.commands:
            print("[TelegramBot] Executing command: {}".format(command))
            handler = self.commands[command][0]
            handler()
        elif text.startswith("/"):
            self.send_message("Unknown command: {}\n\nUse /help to see available commands.".format(command))

    # ---------- core commands ----------
    def cmd_help(self):
        lines = ["<b>Scout Control Panel</b> ({})".format(self.mission.display_name), "", "<b>Commands:</b>"]
        for cmd, (handler, desc) in sorted(self.commands.items()):
            if cmd == "/start":
                continue
            lines.append("{} - {}".format(cmd, desc))
        self.send_message("\n".join(lines))

    def cmd_health(self):
        self.send_message("Checking services...")
        checks = []
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=5)
            checks.append(("Ollama", r.status_code == 200))
        except Exception:
            checks.append(("Ollama", False))
        try:
            r = requests.get("http://localhost:8000/", timeout=5)
            checks.append(("Scout API", r.status_code == 200))
        except Exception:
            checks.append(("Scout API", False))
        try:
            r = requests.get("http://localhost:8001/", timeout=5)
            checks.append(("Dashboard", r.status_code == 200))
        except Exception:
            checks.append(("Dashboard", False))
        emoji = "\u2705" if all(s for _, s in checks) else "\u26a0\ufe0f"
        msg = "{} <b>Health Check</b>\n\n".format(emoji)
        for name, status in checks:
            msg += "{} {}\n".format("\u2705" if status else "\u274c", name)
        msg += "\n<i>{}</i>".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.send_message(msg)

    def cmd_check(self):
        self.send_message("\U0001f50d Starting {} workflow...\n\nThis may take a few minutes.".format(
            self.mission.display_name))
        try:
            r = requests.post("http://localhost:8000/run-workflow", timeout=600)
            if r.status_code == 200:
                result = r.json()
                if result.get("success"):
                    data = result.get("result", {}).get("data", {})
                    msg = ("\u2705 <b>Workflow Complete!</b>\n\n"
                           "Discovered: {}\nNew saved: {}\nDuplicates: {}\n\n<i>{}</i>".format(
                               data.get("total_discovered", "N/A"),
                               data.get("new_saved", "N/A"),
                               data.get("duplicates_filtered", "N/A"),
                               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                else:
                    msg = "\u26a0\ufe0f Workflow finished with issues:\n{}".format(result.get("error", "Unknown error"))
            else:
                msg = "\u274c API returned status {}".format(r.status_code)
        except requests.Timeout:
            msg = "\u23f1 Workflow is taking longer than expected. Check logs for status."
        except Exception as e:
            msg = "\u274c Error: {}".format(e)
        self.send_message(msg)

    def cmd_backup(self):
        self.send_message("\U0001f4be Creating backup...")
        try:
            from core.database import _project_dir
            project_dir = _project_dir()
            db_path = os.path.join(project_dir, self.mission.db_filename)
            backup_dir = os.path.join(project_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, "{}_{}.db".format(self.mission.name, timestamp))
            shutil.copy2(db_path, backup_path)
            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            msg = ("\u2705 <b>Backup Complete</b>\n\nFile: <code>{}</code>\n"
                   "Size: {:.2f} MB\n\n<i>{}</i>".format(
                       os.path.basename(backup_path), size_mb,
                       datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        except Exception as e:
            msg = "\u274c Backup failed: {}".format(e)
        self.send_message(msg)

    # ---------- main loop ----------
    def run(self):
        if not self.bot_token or not self.chat_id:
            print("[TelegramBot] ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
            return
        self.running = True
        print("[TelegramBot] Starting bot... Listening for commands.")
        self.send_message("\U0001f916 <b>Scout Bot Online</b> ({})\n\nUse /help to see commands.".format(
            self.mission.display_name))
        while self.running:
            try:
                for update in self.get_updates():
                    self.process_update(update)
            except KeyboardInterrupt:
                print("[TelegramBot] Shutting down...")
                self.running = False
            except Exception as e:
                print("[TelegramBot] Error in main loop: {}".format(e))
                time.sleep(5)

    def stop(self):
        self.running = False


# Backwards-compatible alias
TelegramBot = TelegramCommandBot


def main():
    from dotenv import load_dotenv
    from core.database import _project_dir
    load_dotenv(os.path.join(_project_dir(), ".env"))
    bot = TelegramCommandBot()
    bot.run()


if __name__ == "__main__":
    main()
