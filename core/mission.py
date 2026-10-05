# Mission plugin interface and loader.
#
# A mission is a self-contained domain pack: it defines what to discover,
# how to store it, how to score it, and how to present it. The core engine
# drives the workflow but never contains domain logic.
import importlib
import os
from abc import ABC, abstractmethod


class MissionPlugin(ABC):
    # ---- identity ----
    name: str = ""
    display_name: str = ""
    description: str = ""

    # ---- storage ----
    @property
    @abstractmethod
    def model(self):
        # SQLAlchemy declarative model class for discovered items.
        raise NotImplementedError

    @property
    def db_filename(self) -> str:
        return "scout.db"

    def get_session(self):
        from core.database import session_for
        return session_for(self.db_filename)

    # ---- discovery ----
    @abstractmethod
    def discovery_tools(self) -> list:
        # Return BaseTool instances that discover new items.
        raise NotImplementedError

    @abstractmethod
    def normalize_items(self, tool_name: str, result_data: dict) -> list:
        # Map a discovery tool's raw result dict into canonical item dicts.
        raise NotImplementedError

    # ---- persistence (mission owns its schema) ----
    @abstractmethod
    def save_new_items(self, session, items: list, job_id: str) -> dict:
        # Dedupe + persist. Returns {"saved_count": int, "duplicate_count": int}.
        raise NotImplementedError

    # ---- scoring ----
    @abstractmethod
    def scorer(self):
        # Return scorer object with execute(item_ids=None, update_db=True) -> dict.
        raise NotImplementedError

    # ---- reporting ----
    @abstractmethod
    def recent_highlights(self, session, hours: int = 2, limit: int = 10) -> list:
        # Top-scoring recent items for notifications.
        raise NotImplementedError

    @abstractmethod
    def format_report_html(self, stats: dict, highlights: list) -> tuple:
        # Return (subject, html_body) for the run report email.
        raise NotImplementedError

    @abstractmethod
    def format_telegram_message(self, stats: dict, highlights: list) -> str:
        # Return HTML-formatted telegram alert text.
        raise NotImplementedError

    # ---- dashboard ----
    @property
    @abstractmethod
    def dashboard_title(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def list_fields(self) -> list:
        # [{"key": str, "label": str, "type": str}]
        # type in: title, subtitle, meta, link, score, date, age, status
        raise NotImplementedError

    @property
    def searchable_fields(self) -> list:
        return []

    @property
    def status_field(self):
        # Model attribute name holding workflow status, or None.
        return None

    @property
    def status_options(self) -> list:
        return []

    @property
    def score_field(self) -> str:
        return "relevance_score"

    @property
    def discovered_field(self) -> str:
        return "discovered_at"

    def on_status_change(self, item, new_status, session):
        # Hook run after the status field is updated. Default: no-op.
        return

    # ---- extra agent tools ----
    def agent_tools(self) -> list:
        # Mission-specific tools exposed to the LLM agent (e.g. scorer).
        return []

    # ---- telegram bot commands ----
    def telegram_commands(self) -> dict:
        # {"/cmd": (description, handler_fn)} merged into the core bot.
        return {}


def active_mission_name() -> str:
    return os.getenv("ACTIVE_MISSION", "internships")


def load_mission(name: str = None) -> MissionPlugin:
    name = name or active_mission_name()
    module = importlib.import_module("missions.{}.mission".format(name))
    cls = getattr(module, "Mission")
    mission = cls()
    if not isinstance(mission, MissionPlugin):
        raise TypeError(
            "missions.{}.mission.Mission must subclass MissionPlugin".format(name)
        )
    return mission
