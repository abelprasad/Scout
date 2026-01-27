import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.tools.base import BaseTool
import requests
import json

class InstantAlertTool(BaseTool):
    name = "send_instant_alert"
    description = "Send instant alert for urgent new internships. Args: {'jobs': [job_list], 'urgent': True}"
    
    def execute(self, jobs, urgent=True):
        """Send instant notification for new internships"""
        try:
            if not jobs:
                return {"success": True, "data": "No jobs to alert about"}
            
            # Create alert message
            alert_message = self._format_alert(jobs, urgent)
            
            # For now, we'll use print/email until Telegram is set up
            print("=" * 60)
            print("🚨 INSTANT INTERNSHIP ALERT 🚨")
            print("=" * 60)
            print(alert_message)
            print("=" * 60)
            
            # Save alert to file for tracking
            with open("output/instant_alerts.log", "a") as f:
                f.write(f"\n{alert_message}\n{'='*60}\n")
            
            return {
                "success": True,
                "data": f"Alert sent for {len(jobs)} new internships"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_alert(self, jobs, urgent):
        """Format alert message"""
        timestamp = json.loads(jobs[0]['discovered_at'])[:19] if jobs else "now"
        
        message = f"⚡ DETECTED AT: {timestamp}\n\n"
        
        for i, job in enumerate(jobs, 1):
            message += f"{i}. {job['title']}\n"
            message += f"   🏢 {job['company'].title()}\n"
            message += f"   📍 {job['location']}\n"
            message += f"   🔗 {job['url']}\n"
            message += f"   🏷️ {job['department']}\n\n"
        
        message += f"⚡ APPLY IMMEDIATELY - DETECTED FROM ATS SOURCE\n"
        message += f"🎯 {len(jobs)} NEW POSTINGS FOUND"
        
        return message
