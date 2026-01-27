from database import get_db_session, InternshipListing

def fix_remaining_urls():
    """Fix any remaining synthetic GitHub URLs"""
    session = get_db_session()
    
    # Get all internships with synthetic URLs
    internships = session.query(InternshipListing).filter(
        InternshipListing.url.like('%github.com/internship%')
    ).all()
    
    print(f"Found {len(internships)} entries with synthetic URLs")
    
    for internship in internships:
        # Create Google search URL as fallback
        search_query = f"{internship.company} {internship.title} internship application"
        google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        
        internship.url = google_url
        print(f"✅ Updated {internship.company} - {internship.title}")
    
    session.commit()
    session.close()
    print("🎉 All URLs fixed!")

if __name__ == "__main__":
    fix_remaining_urls()
