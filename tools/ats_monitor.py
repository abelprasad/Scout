from .base import BaseTool
import requests
import hashlib
import json
import time
from datetime import datetime

class ATSMonitorTool(BaseTool):
    name = "monitor_ats"
    description = "Monitor ATS systems (Greenhouse, Lever) for new postings. Args: {'companies': ['company1', 'company2'], 'ats_type': 'greenhouse'}"
    
    def __init__(self):
        # Companies with known ATS endpoints (base URLs without /jobs)
        self.greenhouse_companies = {
            'stripe': 'https://boards.greenhouse.io/stripe',
            'reddit': 'https://boards.greenhouse.io/reddit', 
            'twitch': 'https://boards.greenhouse.io/twitch',
            'robinhood': 'https://boards.greenhouse.io/robinhood',
            'coinbase': 'https://boards.greenhouse.io/coinbase',
            'square': 'https://boards.greenhouse.io/square',
            'dropbox': 'https://boards.greenhouse.io/dropbox',
            'notion': 'https://boards.greenhouse.io/notion'
        }

    def execute(self, companies=None, ats_type="greenhouse", check_internships_only=True):
        """Monitor ATS endpoints for new job postings"""
        try:
            print(f"[ATSMonitor] Starting {ats_type} monitoring...")
            
            # Only proceed if we have greenhouse type
            if ats_type != "greenhouse":
                print(f"[ATSMonitor] Unsupported ATS type: {ats_type}, switching to greenhouse")
                ats_type = "greenhouse"
            
            company_urls = self.greenhouse_companies
            
            # If specific companies requested, filter and normalize case
            if companies:
                # Convert to lowercase for matching
                companies_lower = [c.lower() for c in companies]
                company_urls = {k: v for k, v in company_urls.items() if k in companies_lower}
                print(f"[ATSMonitor] Filtering to companies: {list(company_urls.keys())}")
            
            results = []
            
            for company, base_url in company_urls.items():
                try:
                    print(f"[ATSMonitor] Checking {company}...")
                    
                    # Construct full URL with /jobs?format=json
                    full_url = base_url + '/jobs?format=json'
                    print(f"[ATSMonitor] URL: {full_url}")
                    
                    # Make request with realistic headers
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                        'Accept': 'application/json',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    response = requests.get(full_url, headers=headers, timeout=15)
                    
                    print(f"[ATSMonitor] {company}: HTTP {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            jobs = self._extract_jobs(data, company, check_internships_only)
                            results.extend(jobs)
                            
                            print(f"[ATSMonitor] {company}: Found {len(jobs)} internships")
                        except json.JSONDecodeError as e:
                            print(f"[ATSMonitor] {company}: Invalid JSON response - {str(e)}")
                    else:
                        print(f"[ATSMonitor] {company}: Failed to fetch data - Status {response.status_code}")
                        # Print first 200 chars of response for debugging
                        print(f"[ATSMonitor] Response preview: {response.text[:200]}")
                    
                    # Rate limiting - be respectful
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"[ATSMonitor] Error checking {company}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "jobs_found": len(results),
                    "jobs": results,
                    "companies_checked": list(company_urls.keys())
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_jobs(self, data, company, internships_only=True):
        """Extract job data from Greenhouse response"""
        jobs = []
        
        try:
            job_list = data.get('jobs', [])
            print(f"[ATSMonitor] {company}: Processing {len(job_list)} total jobs")
            
            for job in job_list:
                title = job.get('title', '')
                
                # Filter for internships if requested
                if internships_only and not self._is_internship(title):
                    continue
                
                jobs.append({
                    'title': title,
                    'company': company,
                    'location': job.get('location', {}).get('name', '') if isinstance(job.get('location'), dict) else str(job.get('location', '')),
                    'url': job.get('absolute_url', ''),
                    'department': job.get('departments', [{}])[0].get('name', '') if job.get('departments') else '',
                    'ats_source': 'greenhouse',
                    'ats_id': str(job.get('id', '')),
                    'discovered_at': datetime.utcnow().isoformat(),
                    'description': job.get('content', '')[:500] + "..." if job.get('content') else ''
                })
                    
        except Exception as e:
            print(f"[ATSMonitor] Error extracting jobs: {str(e)}")
        
        return jobs
    
    def _is_internship(self, title):
        """Check if job title indicates an internship"""
        intern_keywords = ['intern', 'internship', 'co-op', 'coop', 'student', 'summer', 'fall', 'spring', 'new grad', 'graduate']
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in intern_keywords)


class ATSChangeDetectorTool(BaseTool):
    name = "detect_ats_changes"
    description = "Detect new ATS postings since last check. Args: {'companies': ['stripe', 'figma']}"
    
    def execute(self, companies=None):
        """Detect changes in job postings"""
        try:
            from database import get_db_session, InternshipListing
            
            # Get current ATS data
            ats_monitor = ATSMonitorTool()
            results = ats_monitor.execute(companies, "greenhouse")
            
            if not results["success"]:
                return results
            
            all_jobs = results["data"]["jobs"]
            
            # Check against database for truly new postings
            session = get_db_session()
            new_jobs = []
            
            for job in all_jobs:
                # Check if we've seen this job before by URL
                existing = session.query(InternshipListing).filter_by(url=job['url']).first()
                
                if not existing:
                    new_jobs.append(job)
                    print(f"[ATSChangeDetector] 🚨 NEW: {job['title']} at {job['company']}")
            
            session.close()
            
            return {
                "success": True,
                "data": {
                    "total_jobs_found": len(all_jobs),
                    "new_jobs": len(new_jobs),
                    "new_postings": new_jobs,
                    "alert_needed": len(new_jobs) > 0
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
