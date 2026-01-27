from database import get_db_session, InternshipListing
import requests
import re

def update_urls():
    """Update database with real application URLs"""
    session = get_db_session()
    
    # Get GitHub content
    url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
    response = requests.get(url)
    content = response.text
    
    # Extract real URLs from content
    pattern = r'<td><strong><a[^>]*>([^<]+)</a></strong></td>\s*<td>([^<]+)</td>.*?href="([^"]+)"'
    matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    print(f"Found {len(matches)} companies with URLs")
    
    for company, position, real_url in matches:
        # Find matching database record
        internship = session.query(InternshipListing).filter_by(
            company=company.strip(),
            title=position.strip()
        ).first()
        
        if internship and 'github.com/internship' in internship.url:
            internship.url = real_url.strip()
            print(f"✅ Updated {company}: {real_url[:50]}...")
    
    session.commit()
    session.close()
    print("🎉 URL update complete!")

if __name__ == "__main__":
    update_urls()
