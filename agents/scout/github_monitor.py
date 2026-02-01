import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.tools.base import BaseTool
from shared.database.database import get_db_session, InternshipListing
import requests
import json
from datetime import datetime
import hashlib
import re

class GitHubInternshipMonitor(BaseTool):
    name = "monitor_github_internships"
    description = "Monitor GitHub internship repos for new postings. Args: {'repos': ['SimplifyJobs', 'Pitt-CSC', 'SpeedyApply']}"

    def __init__(self):
        self.repos = {
            'SimplifyJobs': {
                'url': 'https://api.github.com/repos/SimplifyJobs/Summer2026-Internships/commits',
                'raw_url': 'https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md'
            },
            'Pitt-CSC': {
                'url': 'https://api.github.com/repos/pittcsc/Summer2026-Internships/commits',
                'raw_url': 'https://raw.githubusercontent.com/pittcsc/Summer2026-Internships/dev/README.md'
            },
            'SpeedyApply': {
                'url': 'https://api.github.com/repos/speedyapply/2026-SWE-College-Jobs/commits',
                'raw_url': 'https://raw.githubusercontent.com/speedyapply/2026-SWE-College-Jobs/main/README.md'
            }
        }

    def execute(self, repos=None, check_recent_commits=True, limit=500):
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

                        # Get current content for internship extraction (WITH LIMIT)
                        content_data = self._extract_internships(repo_info['raw_url'], limit=limit)

                        results.append({
                            'repo': repo_name,
                            'recent_commits': commits_data['commit_count'],
                            'latest_commit_time': commits_data['latest_time'],
                            'latest_commit_message': commits_data['latest_message'],
                            'internships_found': content_data['internship_count'],
                            'sample_internships': content_data['sample_internships'],  # All internships
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

    def _extract_internships(self, raw_url, limit=500):
        """Extract internship listings from README"""
        try:
            print(f"[GitHubMonitor] Fetching README content...")
            response = requests.get(raw_url, timeout=20)

            if response.status_code != 200:
                print(f"[GitHubMonitor] Failed to fetch README: {response.status_code}")
                return {'internship_count': 0, 'sample_internships': []}

            content = response.text
            internships = []

            print(f"[GitHubMonitor] Parsing internships (limit: {limit})...")

            # Pattern 1: SimplifyJobs HTML table format with age
            # <td><strong><a href="...">Company</a></strong></td>
            # <td>Position</td>
            # <td>Location</td>
            # <td>...<a href="apply_url">...</td>
            # <td>Xd</td> (age in days)
            pattern1 = r'<tr>\s*<td><strong><a[^>]*>([^<]+)</a></strong></td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*<td[^>]*>.*?<a href="([^"]+)"[^>]*><img[^>]*alt="Apply"[^>]*>.*?</td>\s*<td>(\d+)d</td>'
            matches1 = re.findall(pattern1, content, re.DOTALL)

            for match in matches1[:limit]:
                company = match[0].strip()
                position = match[1].strip()
                location = match[2].strip()
                url = match[3].strip()
                age_days = match[4].strip() if len(match) > 4 else "0"

                # Skip if URL is not a real application link
                if 'simplify.jobs' in url and '/c/' in url:
                    continue  # Skip company profile links

                internships.append({
                    'company': company,
                    'position': position,
                    'location': location,
                    'url': url,
                    'age_days': age_days,
                    'source': 'GitHub'
                })

                if len(internships) >= limit:
                    break

            print(f"[GitHubMonitor] Pattern 1 found {len(internships)} internships")

            # Pattern 2: SpeedyApply markdown format
            # | Company | Position | Location | Link |
            if len(internships) < 10:
                pattern2 = r'\|\s*\[([^\]]+)\]\([^)]+\)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*\[Apply\]\(([^)]+)\)'
                matches2 = re.findall(pattern2, content)

                for match in matches2[:limit]:
                    company = match[0].strip()
                    position = match[1].strip()
                    location = match[2].strip()
                    url = match[3].strip()

                    internships.append({
                        'company': company,
                        'position': position,
                        'location': location,
                        'url': url,
                        'source': 'GitHub'
                    })

                    if len(internships) >= limit:
                        break

                print(f"[GitHubMonitor] Pattern 2 found {len(internships)} total")

            print(f"[GitHubMonitor] ✅ Found {len(internships)} internships")

            return {
                'internship_count': len(internships),
                'sample_internships': internships
            }
            
        except Exception as e:
            print(f"[GitHubMonitor] Error extracting internships: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'internship_count': 0, 'sample_internships': []}


class GitHubChangeDetector(BaseTool):
    name = "detect_github_changes"
    description = "Detect new commits or internship additions to GitHub repos"

    def execute(self, repos=None):
        """Detect new activity on GitHub internship repos"""
        try:
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
                            'url': internship['url'],  # Now contains real URL
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
