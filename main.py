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
import uuid
from datetime import datetime

app = FastAPI(title="AI Agent API")

# In-memory job storage
jobs = {}

class JobRequest(BaseModel):
    goal: str

def run_agent_background(job_id: str, goal: str):
    """Run the agent in the background"""
    jobs[job_id]['status'] = 'running'
    jobs[job_id]['started_at'] = datetime.now().isoformat()
    
    try:
        # Initialize tools
        tools = [
            WebSearchTool(),
            FileSystemTool(),
            EmailTool(),
            BrowserTool(),
            DatabaseTool(),
            DatabaseQueryTool(),
            ATSMonitorTool(),
            ATSChangeDetectorTool(),
            InstantAlertTool()
        ]
	
        
        # Create and run agent
        agent = Agent(tools)
        result = agent.run(goal)
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['result'] = result
        jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['completed_at'] = datetime.now().isoformat()

@app.post("/jobs")
def create_job(request: JobRequest, background_tasks: BackgroundTasks):
    """Submit a new goal for the agent"""
    job_id = str(uuid.uuid4())[:8]
    
    jobs[job_id] = {
        'goal': request.goal,
        'status': 'queued',
        'created_at': datetime.now().isoformat()
    }
    
    # Start agent in background
    background_tasks.add_task(run_agent_background, job_id, request.goal)
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": "Agent started"
    }

@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Get status of a job"""
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    return jobs[job_id]

@app.get("/jobs")
def list_jobs():
    """List all jobs"""
    return {"jobs": jobs}

@app.get("/")
def root():
    """API info"""
    return {
        "name": "AI Agent API",
        "version": "0.1.0",
        "endpoints": {
            "POST /jobs": "Create a new job",
            "GET /jobs/{job_id}": "Get job status",
            "GET /jobs": "List all jobs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
