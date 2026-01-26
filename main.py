from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from agent import Agent
from tools.websearch import WebSearchTool
from tools.filesystem import FileSystemTool
from tools.email import EmailTool
from tools.browser import BrowserTool
from tools.database import DatabaseTool, DatabaseQueryTool
from tools.ats_monitor import ATSMonitorTool, ATSChangeDetectorTool
from tools.instant_alert import InstantAlertTool
from tools.github_monitor import GitHubInternshipMonitor, GitHubChangeDetector
import uuid
from datetime import datetime

app = FastAPI(title="AI Agent API", description="Autonomous AI agent for internship discovery")

# Job storage (in-memory for now)
jobs = {}

class JobRequest(BaseModel):
    goal: str

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

def run_agent(job_id: str, goal: str):
    """Run agent in background"""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["started_at"] = datetime.utcnow()
        
        # Create agent with all tools
        tools = [
            WebSearchTool(),
            FileSystemTool(),
            EmailTool(),
            BrowserTool(),
            DatabaseTool(),
            DatabaseQueryTool(),
            ATSMonitorTool(),
            ATSChangeDetectorTool(),
            InstantAlertTool(),
            GitHubInternshipMonitor(),
            GitHubChangeDetector()
        ]
        
        agent = Agent(tools=tools)
        
        # Run agent
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
    """Submit a new job to the agent"""
    job_id = str(uuid.uuid4())[:8]
    
    # Initialize job record
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
    
    # Start agent in background
    background_tasks.add_task(run_agent, job_id, job.goal)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Agent started"
    )

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status and results"""
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    job = jobs[job_id].copy()
    
    # Convert datetime objects to strings for JSON serialization
    for field in ["created_at", "started_at", "completed_at"]:
        if job[field]:
            job[field] = job[field].isoformat()
    
    return job

@app.get("/jobs")
async def list_jobs():
    """List all jobs"""
    job_list = []
    for job in jobs.values():
        job_copy = job.copy()
        # Convert datetime objects to strings
        for field in ["created_at", "started_at", "completed_at"]:
            if job_copy[field]:
                job_copy[field] = job_copy[field].isoformat()
        job_list.append(job_copy)
    
    return {"jobs": job_list, "count": len(job_list)}

@app.get("/")
async def root():
    """API info"""
    return {
        "message": "AI Agent API",
        "version": "2.0",
        "capabilities": [
            "Web Search",
            "Browser Automation", 
            "Email Notifications",
            "Database Storage",
            "ATS Monitoring",
            "GitHub Repo Monitoring",
            "Instant Alerts"
        ],
        "endpoints": {
            "POST /jobs": "Submit new agent goal",
            "GET /jobs/{job_id}": "Get job status",
            "GET /jobs": "List all jobs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
