import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database.database import get_db_session, InternshipListing, save_internship
from shared.tools.base import BaseTool
from datetime import datetime

class DatabaseTool(BaseTool):
    name = "save_to_database"
    description = "Save internships to database. Args: {'internships': [list_of_internship_objects], 'agent_job_id': 'job_id'}"
    
    def execute(self, internships, agent_job_id=None):
        """Save internships to database"""
        try:
            if not internships:
                return {
                    "success": True,
                    "data": {
                        "saved_count": 0,
                        "duplicate_count": 0,
                        "total_processed": 0
                    }
                }
            
            session = get_db_session()
            saved_count = 0
            duplicate_count = 0
            
            for internship_data in internships:
                # Handle both dict objects and string placeholders
                if isinstance(internship_data, str):
                    print(f"[Database] Skipping string placeholder: {internship_data}")
                    continue
                
                if not isinstance(internship_data, dict):
                    print(f"[Database] Skipping invalid format: {type(internship_data)}")
                    continue
                
                # Extract data from internship object
                title = internship_data.get('title', internship_data.get('position', ''))
                company = internship_data.get('company', '')
                url = internship_data.get('url', '')
                location = internship_data.get('location', '')
                description = internship_data.get('description', '')
                source = internship_data.get('source', 'GitHub')
                
                # Skip if missing essential data
                if not title or not company:
                    print(f"[Database] Skipping incomplete internship: {internship_data}")
                    continue
                
                # Check for duplicates by URL or title+company combination
                existing = session.query(InternshipListing).filter(
                    (InternshipListing.url == url) |
                    ((InternshipListing.title == title) & (InternshipListing.company == company))
                ).first()
                
                if existing:
                    duplicate_count += 1
                    print(f"[Database] Duplicate found: {title} at {company}")
                    continue
                
                # Create new internship record
                new_internship = InternshipListing(
                    agent_job_id=agent_job_id or "multi_agent",
                    title=title,
                    company=company,
                    url=url,
                    location=location,
                    description=description[:500] if description else "",
                    requirements="",
                    deadline="",
                    application_status="not_applied",
                    applied=False,
                    discovered_at=datetime.utcnow()
                )
                
                session.add(new_internship)
                saved_count += 1
                print(f"[Database] Saved: {title} at {company}")
            
            session.commit()
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
            print(f"[Database] Error saving internships: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


class DatabaseQueryTool(BaseTool):
    name = "query_database"
    description = "Query database for internships. Args: {'action': 'recent'|'search'|'unapplied', 'limit': 10, 'query': 'search_term'}"
    
    def execute(self, action="recent", limit=10, query=None):
        """Query internships from database"""
        try:
            session = get_db_session()
            
            if action == "recent":
                internships = session.query(InternshipListing).order_by(
                    InternshipListing.discovered_at.desc()
                ).limit(limit).all()
            
            elif action == "search" and query:
                internships = session.query(InternshipListing).filter(
                    (InternshipListing.title.contains(query)) |
                    (InternshipListing.company.contains(query)) |
                    (InternshipListing.description.contains(query))
                ).limit(limit).all()
            
            elif action == "unapplied":
                internships = session.query(InternshipListing).filter_by(
                    applied=False
                ).limit(limit).all()
            
            else:
                internships = session.query(InternshipListing).limit(limit).all()
            
            result = []
            for internship in internships:
                result.append({
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
                    "internships": result,
                    "count": len(result)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
