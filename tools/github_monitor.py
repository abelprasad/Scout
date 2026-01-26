from .base import BaseTool
import requests
import json
from datetime import datetime
import hashlib
import re

class GitHubInternshipMonitor(BaseTool):
    name = "monitor_github_internships"
    description = "Monitor GitHub internship repos for new postings. Args: {'repos': ['SimplifyJobs', 'Pitt-CSC']}"
    
    def __init__(self):
        self.repos = {
            'SimplifyJobs': {
                'url': 'https://api.github.com/repos/SimplifyJobs/Summer2026-Internships/commits',
                'raw_url': 'https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md'
            },
            'Pitt-CSC': {
                'url': 'https://api.github.com/repos/pittcsc/Summer2026-Internships/commits', 
                'raw_url': 'https://raw.githubusercontent.com/pittcsc/Summer2026-Internships/dev/README.md'
            }
        }
    
    def execute(self, repos=None, check_recent_commits=True):
        """Monitor GitHub internship repos for updates"""
        try:
            print(f"[GitHubMonitor] Starting GitHub internship monitoring...")
            
            if repos:
                selected_repos = {k: v for k, v in self.repos.items() if k in repos}
            else:
                selected_repos = self.repos
            
            results = []
            
            for repo_name, repo_info in selected_repos.items():
                try:
                    print(f"[GitHubMonitor] Checking {repo_name}...")
                    
                    if check_recent_commits:
                        # Check recent commits for activity
                        commits_data = self._check_commits(repo_info['url'])
                        
                        # Get current content for internship extraction
                        content_data = self._extract_internships(repo_info['raw_url'])
                        
                        results.append({
                            'repo': repo_name,
                            'recent_commits': commits_data['commit_count'],
                            'latest_commit_time': commits_data['latest_time'],
                            'latest_commit_message': commits_data['latest_message'],
                            'internships_found': content_data['internship_count'],
                            'sample_internships': content_data['sample_internships'][:5],  # First 5
                            'last_checked': datetime.utcnow().isoformat()
                        })
                        
                        print(f"[GitHubMonitor] {repo_name}: {commits_data['commit_count']} recent commits, {content_data['internship_count']} internships")
                    
                except Exception as e:
                    print(f"[GitHubMonitor] Error checking {repo_name}: {str(e)}")
                    continue
            
            return {
                "success": True,
                "data": {
                    "repos_checked": len(results),
                    "repo_data": results,
                    "total_internships": sum(r.get('internships_found', 0) for r in results)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_commits(self, commits_url):
        """Check recent commits on the repo"""
        try:
            response = requests.get(commits_url, timeout=15)
            if response.status_code == 200:
                commits = response.json()
                recent_commits = commits[:10]  # Last 10 commits
                
                return {
                    'commit_count': len(recent_commits),
                    'latest_time': recent_commits[0]['commit']['author']['date'] if recent_commits else None,
                    'latest_message': recent_commits[0]['commit']['message'] if recent_commits else None
                }
            else:
                return {'commit_count': 0, 'latest_time': None, 'latest_message': None}
                
        except Exception as e:
            print(f"[GitHubMonitor] Error checking commits: {str(e)}")
            return {'commit_count': 0, 'latest_time': None, 'latest_message': None}
    
    def _extract_internships(self, raw_url):
        """Extract internship listings from README HTML tables"""
        try:
            response = requests.get(raw_url, timeout=15)
            if response.status_code == 200:
                content = response.text
                internships = []
                
                # Parse HTML tables for internship data
                # Pattern matches: <td><strong><a>Company</a></strong></td><td>Role</td><td>Location</td>
                table_pattern = r'<td><strong><a[^>]*>([^<]+)</a></strong></td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>'
                matches = re.findall(table_pattern, content, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    company = match[0].strip()
                    position = match[1].strip()
                    location = match[2].strip()
                    
                    # Filter for internships (the position should contain intern-related keywords)
                    if any(keyword in position.lower() for keyword in ['intern', 'co-op', 'coop', 'summer', 'spring', 'fall']):
                        internships.append({
                            'company': company,
                            'position': position,
                            'location': location,
                            'source': 'GitHub'
                        })
                
                # Alternative pattern for different table formats
                if len(internships) == 0:
                    # Try simpler pattern
                    simple_pattern = r'<td>.*?([A-Za-z][^<]{2,30})</td>\s*<td>([^<]*[Ii]ntern[^<]*)</td>\s*<td>([^<]+)</td>'
                    matches = re.findall(simple_pattern, content, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        company = match[0].strip()
                        position = match[1].strip()
                        location = match[2].strip()
                        
                        internships.append({
                            'company': company,
                            'position': position,
                            'location': location,
                            'source': 'GitHub'
                        })
                
                return {
                    'internship_count': len(internships),
                    'sample_internships': internships[:50]  # First 50 for preview
                }
            else:
                return {'internship_count': 0, 'sample_internships': []}
                
        except Exception as e:
            print(f"[GitHubMonitor] Error extracting internships: {str(e)}")
            return {'internship_count': 0, 'sample_internships': []}


class GitHubChangeDetector(BaseTool):
    name = "detect_github_changes"
    description = "Detect new commits or internship additions to GitHub repos"
    
    def execute(self, repos=None):
        """Detect new activity on GitHub internship repos"""
        try:
            from database import get_db_session, InternshipListing
            
            # Get current GitHub data
            github_monitor = GitHubInternshipMonitor()
            results = github_monitor.execute(repos)
            
            if not results["success"]:
                return results
            
            new_internships = []
            repo_updates = []
            
            for repo_data in results["data"]["repo_data"]:
                # Check if we have new internships to add to database
                for internship in repo_data.get("sample_internships", []):
                    # Create a synthetic URL since GitHub repos don't have direct apply links
                    synthetic_url = f"https://github.com/internship/{internship['company'].lower().replace(' ', '-')}-{internship['position'].lower().replace(' ', '-')}"
                    
                    # Check if this combination exists in database
                    session = get_db_session()
                    existing = session.query(InternshipListing).filter_by(
                        company=internship['company'],
                        title=internship['position']
                    ).first()
                    
                    if not existing:
                        new_internships.append({
                            'title': internship['position'],
                            'company': internship['company'],
                            'location': internship['location'],
                            'url': synthetic_url,
                            'source': 'GitHub-' + repo_data['repo'],
                            'discovered_at': datetime.utcnow().isoformat()
                        })
                        print(f"[GitHubChangeDetector] 🚨 NEW: {internship['position']} at {internship['company']}")
                    
                    session.close()
                
                repo_updates.append({
                    'repo': repo_data['repo'],
                    'commits': repo_data['recent_commits'],
                    'latest_commit': repo_data['latest_commit_message']
                })
            
            return {
                "success": True,
                "data": {
                    "new_internships": len(new_internships),
                    "new_postings": new_internships,
                    "repo_updates": repo_updates,
                    "alert_needed": len(new_internships) > 0
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
