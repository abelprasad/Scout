from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import sys
import os

# Add paths for new structure
sys.path.append('/home/abel/ai-agent')
sys.path.append('/home/abel/ai-agent/shared')
sys.path.append('/home/abel/ai-agent/agents')

from agent import Agent
from shared.tools.websearch import WebSearchTool
from shared.tools.filesystem import FileSystemTool
from shared.tools.email import EmailTool
from shared.tools.browser import BrowserTool
from shared.tools.database import DatabaseTool, DatabaseQueryTool
from agents.scout.github_monitor import GitHubInternshipMonitor, GitHubChangeDetector
from agents.scout.ats_monitor import ATSMonitorTool, ATSChangeDetectorTool
from agents.scout.instant_alert import InstantAlertTool
from agents.orchestrator.orchestrator_agent import OrchestratorAgent
import uuid
from datetime import datetime

app = FastAPI(title="Multi-Agent AI System", description="Nuclear internship detection with specialized agents")

# Job storage
jobs = {}

class JobRequest(BaseModel):
    goal: str

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

def run_agent(job_id: str, goal: str):
    """Run multi-agent system in background"""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["started_at"] = datetime.utcnow()
        
        # Create agent with all specialized tools
        tools = [
            WebSearchTool(),
            FileSystemTool(),
            EmailTool(),
            BrowserTool(),
            DatabaseTool(),
            DatabaseQueryTool(),
            GitHubInternshipMonitor(),
            GitHubChangeDetector(),
            ATSMonitorTool(),
            ATSChangeDetectorTool(),
            InstantAlertTool(),
            OrchestratorAgent()  # The orchestrator manages workflow
        ]
        
        agent = Agent(tools=tools)
        
        # Run multi-agent system
        result = agent.run(goal, job_id)
        
        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["completed_at"] = datetime.utcnow()
        jobs[job_id]["result"] = result
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.utcnow()

@app.post("/jobs", response_model=JobResponse)
async def create_job(job: JobRequest, background_tasks: BackgroundTasks):
    """Submit job to multi-agent system"""
    job_id = str(uuid.uuid4())[:8]
    
    jobs[job_id] = {
        "id": job_id,
        "goal": job.goal,
        "status": "queued",
        "created_at": datetime.utcnow(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None
    }
    
    background_tasks.add_task(run_agent, job_id, job.goal)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Multi-agent system started"
    )

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status and results"""
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    job = jobs[job_id].copy()
    
    for field in ["created_at", "started_at", "completed_at"]:
        if job[field]:
            job[field] = job[field].isoformat()
    
    return job

@app.get("/")
async def root():
    """Multi-agent system info"""
    return {
        "message": "Nuclear Internship Detection - Multi-Agent System",
        "version": "3.0",
        "architecture": "Multi-Agent Orchestrated Workflow",
        "agents": {
            "orchestrator": "Workflow coordination and database management",
            "scout": "GitHub/ATS internship discovery", 
            "analyzer": "Resume matching (coming soon)",
            "quality": "Professional review (coming soon)",
            "applicant": "Auto-application (coming soon)"
        },
        "capabilities": [
            "2,697+ internship discovery",
            "Real-time change detection",
            "Database management",
            "Professional web dashboard",
            "Instant notifications",
            "Multi-agent coordination"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
