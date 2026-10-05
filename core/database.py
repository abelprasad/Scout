# Generic storage layer: declarative base, AgentJob, session management.
# Domain models live in missions/<name>/models.py and register on Base here.
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os


Base = declarative_base()


class AgentJob(Base):
    __tablename__ = "agent_jobs"

    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True)
    goal = Column(Text)
    status = Column(String)  # queued, running, completed, failed
    result_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


def _project_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_session_factories = {}


def session_for(db_filename: str):
    # Return a new session bound to the given sqlite file (cached engine).
    # create_all is idempotent: existing tables are left untouched.
    if db_filename not in _session_factories:
        db_path = os.path.join(_project_dir(), db_filename)
        engine = create_engine(
            "sqlite:///{}".format(db_path),
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        _session_factories[db_filename] = sessionmaker(bind=engine)
    return _session_factories[db_filename]()
