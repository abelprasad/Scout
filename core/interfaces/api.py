# Generic FastAPI service: natural-language job queue + mission workflow trigger.
# Zero domain logic: tools and workflow come from the active mission plugin.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

from core.database import _project_dir
load_dotenv(os.path.join(_project_dir(), ".env"))

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
from datetime import datetime

from core.agent import Agent
from core.mission import load_mission
from core.orchestrator import MissionRunner, RunMissionTool
from core.tools.websearch import WebSearchTool
from core.tools.filesystem import FileSystemTool
from core.tools.email import EmailTool
from core.tools.browser import BrowserTool
from core.tools.telegram import TelegramTool
from core.tools.storage import SaveItemsTool, QueryItemsTool


class JobRequest(BaseModel):
    goal: str


class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str


def create_app(mission=None):
    mission = mission or load_mission()
    app = FastAPI(
        title="Scout - {}".format(mission.display_name),
        description="Mission-agnostic agent system. Active mission: {}".format(mission.name),
    )

    jobs = {}

    def build_tools():
        return (
            [
                WebSearchTool(),
                FileSystemTool(),
                EmailTool(),
                BrowserTool(),
                TelegramTool(),
                SaveItemsTool(mission),
                QueryItemsTool(mission),
                RunMissionTool(mission),
            ]
            + mission.discovery_tools()
            + mission.agent_tools()
        )

    def run_agent(job_id: str, goal: str):
        try:
            jobs[job_id]["status"] = "running"
            jobs[job_id]["started_at"] = datetime.utcnow()
            agent = Agent(tools=build_tools())
            result = agent.run(goal, job_id)
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["completed_at"] = datetime.utcnow()
            jobs[job_id]["result"] = result
        except Exception as e:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = str(e)
            jobs[job_id]["completed_at"] = datetime.utcnow()

    @app.post("/jobs", response_model=JobResponse)
    async def create_job(job: JobRequest, background_tasks: BackgroundTasks):
        job_id = str(uuid.uuid4())[:8]
        jobs[job_id] = {
            "id": job_id,
            "goal": job.goal,
            "status": "queued",
            "created_at": datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }
        background_tasks.add_task(run_agent, job_id, job.goal)
        return JobResponse(job_id=job_id, status="queued", message="Agent started")

    @app.get("/jobs/{job_id}")
    async def get_job(job_id: str):
        if job_id not in jobs:
            return {"error": "Job not found"}
        job = jobs[job_id].copy()
        for field in ["created_at", "started_at", "completed_at"]:
            if job[field]:
                job[field] = job[field].isoformat()
        return job

    @app.get("/")
    async def root():
        return {
            "message": "Scout - {}".format(mission.display_name),
            "mission": mission.name,
            "description": mission.description,
            "tools": [t.name for t in build_tools()],
        }

    @app.post("/run-workflow")
    async def run_workflow():
        # Direct mission workflow execution, bypasses the LLM agent layer.
        # Used by cron and the telegram /check command.
        try:
            result = MissionRunner(mission).execute()
            return {"success": True, "message": "Workflow completed", "result": result}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    return app
