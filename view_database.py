from database import get_db_session, InternshipListing, AgentJob

def view_internships():
    session = get_db_session()
    
    # Get all internships
    internships = session.query(InternshipListing).order_by(InternshipListing.discovered_at.desc()).all()
    
    print(f"=== Found {len(internships)} internships in database ===\n")
    
    for i, internship in enumerate(internships, 1):
        print(f"{i}. {internship.title}")
        print(f"   Company: {internship.company}")
        print(f"   URL: {internship.url}")
        print(f"   Location: {internship.location}")
        print(f"   Discovered: {internship.discovered_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Applied: {'Yes' if internship.applied else 'No'}")
        print("-" * 70)
    
    session.close()

if __name__ == "__main__":
    view_internships()
