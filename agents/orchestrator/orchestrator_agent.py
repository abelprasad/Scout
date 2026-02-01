import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.tools.base import BaseTool
from agents.scout.github_monitor import GitHubInternshipMonitor, GitHubChangeDetector
from shared.tools.database import DatabaseTool, DatabaseQueryTool
from agents.scout.instant_alert import InstantAlertTool
from shared.tools.email_tool import EmailTool
from agents.analyzer.resume_matcher import ResumeMatcher
from datetime import datetime

class OrchestratorAgent(BaseTool):
    name = "orchestrate_workflow"
    description = "Orchestrates proven multi-agent workflow: GitHub discovery → Database saving → Notifications"
    
    def __init__(self):
        self.github_monitor = GitHubInternshipMonitor()
        self.database_tool = DatabaseTool()
        self.email_tool = EmailTool()
        self.resume_matcher = ResumeMatcher()
    
    def execute(self, workflow_type="full", repos=None, agent_job_id=None):
        """Execute the proven workflow that we know works"""
        try:
            print(f"[Orchestrator] 🚀 Starting proven workflow...")
            
            # Step 1: GitHub Discovery (PROVEN TO WORK)
            print(f"[Orchestrator] Step 1: GitHub Discovery")
            discovery = self.github_monitor.execute(repos=repos or ["SimplifyJobs", "Pitt-CSC", "SpeedyApply"], limit=500)
            
            if not discovery["success"]:
                return {"success": False, "error": f"Discovery failed: {discovery.get('error')}"}
            
            total_found = discovery["data"]["total_internships"]
            print(f"[Orchestrator] ✅ Discovered {total_found} internships")
            
            # Step 2: Extract Sample Internships for Saving
            all_samples = []
            for repo_data in discovery["data"]["repo_data"]:
                all_samples.extend(repo_data["sample_internships"])
            
            if not all_samples:
                return {"success": True, "data": {"message": "No internships to save"}}
            
            # Step 3: Database Saving (PROVEN TO WORK) 
            print(f"[Orchestrator] Step 2: Database Saving ({len(all_samples)} internships)")
            
            # Format internships correctly (matching the working format)
            formatted_internships = []
            for internship in all_samples:
                formatted_internships.append({
                    'company': internship['company'],
                    'position': internship['position'], 
                    'location': internship['location'],
                    'url': internship['url'],
                    'source': internship['source']
                })
            
            db_result = self.database_tool.execute(
                internships=formatted_internships,
                agent_job_id=agent_job_id or "orchestrator"
            )
            
            if not db_result["success"]:
                return {"success": False, "error": f"Database save failed: {db_result.get('error')}"}
            
            saved_count = db_result["data"]["saved_count"]
            duplicate_count = db_result["data"]["duplicate_count"]
            print(f"[Orchestrator] ✅ Saved {saved_count} new internships ({duplicate_count} duplicates)")

            # Step 4: Resume Matching - Score internships
            print(f"[Orchestrator] Step 3: Resume Matching")
            match_result = self.resume_matcher.execute()
            scored_count = match_result.get("data", {}).get("scored_count", 0) if match_result["success"] else 0
            print(f"[Orchestrator] ✅ Scored {scored_count} internships based on resume")

            # Step 5: Success Summary Email
            print(f"[Orchestrator] Step 4: Success Summary")
            summary = f"""ORCHESTRATED WORKFLOW SUCCESS ✅

🔍 GitHub Discovery: {total_found} internships found
💾 Database Updates: {saved_count} new internships saved
🔄 Duplicates Detected: {duplicate_count} (properly filtered)
📊 Resume Matched: {scored_count} internships scored

Your nuclear internship detection system completed the full workflow successfully!
Check your web dashboard for the new listings sorted by relevance.
"""
            
            email_result = self.email_tool.execute(
                subject="Orchestrated Workflow Complete - Database Updated!",
                body=summary
            )
            
            return {
                "success": True,
                "data": {
                    "total_discovered": total_found,
                    "new_saved": saved_count,
                    "duplicates_filtered": duplicate_count,
                    "scored_count": scored_count,
                    "email_sent": email_result["success"],
                    "workflow_complete": True
                }
            }
            
        except Exception as e:
            print(f"[Orchestrator] ❌ Error: {str(e)}")
            return {"success": False, "error": f"Orchestrator error: {str(e)}"}
