from .base import BaseTool
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_session, save_internship, get_recent_internships, InternshipListing, AgentJob

class DatabaseTool(BaseTool):
    name = "save_to_database"
    description = "Save internship data to database. Args: {'internships': [list of internship objects], 'agent_job_id': 'job_id'}"
    
    def execute(self, internships, agent_job_id):
        """Save internship listings to database"""
        try:
            session = get_db_session()
            saved_count = 0
            duplicate_count = 0
            
            for internship_data in internships:
                # Check if this URL already exists
                existing = session.query(InternshipListing).filter_by(url=internship_data.get('url')).first()
                if existing:
                    duplicate_count += 1
                    continue
                
                # Save new internship
                saved_internship = save_internship(session, internship_data, agent_job_id)
                if saved_internship:
                    saved_count += 1
            
            session.close()
            
            return {
                "success": True,
                "data": {
                    "saved_count": saved_count,
                    "duplicate_count": duplicate_count,
                    "total_processed": len(internships)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class DatabaseQueryTool(BaseTool):
    name = "query_database"
    description = "Query saved internships. Args: {'action': 'recent'|'search', 'query': 'search terms', 'limit': 10}"
    
    def execute(self, action="recent", query="", limit=10):
        """Query internship database"""
        try:
            session = get_db_session()
            
            if action == "recent":
                internships = session.query(InternshipListing)\
                                   .order_by(InternshipListing.discovered_at.desc())\
                                   .limit(limit).all()
            
            elif action == "search":
                internships = session.query(InternshipListing)\
                                   .filter(InternshipListing.title.contains(query) | 
                                          InternshipListing.company.contains(query) |
                                          InternshipListing.description.contains(query))\
                                   .order_by(InternshipListing.discovered_at.desc())\
                                   .limit(limit).all()
            
            elif action == "unapplied":
                internships = session.query(InternshipListing)\
                                   .filter_by(applied=False)\
                                   .order_by(InternshipListing.discovered_at.desc())\
                                   .limit(limit).all()
            
            # Convert to dict format
            results = []
            for internship in internships:
                results.append({
                    "id": internship.id,
                    "title": internship.title,
                    "company": internship.company,
                    "url": internship.url,
                    "location": internship.location,
                    "deadline": internship.deadline,
                    "discovered_at": internship.discovered_at.strftime("%Y-%m-%d"),
                    "applied": internship.applied
                })
            
            session.close()
            
            return {
                "success": True,
                "data": {
                    "internships": results,
                    "count": len(results)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
