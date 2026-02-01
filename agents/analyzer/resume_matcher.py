import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.tools.base import BaseTool
from shared.database.database import get_db_session, InternshipListing
import re
import json

class ResumeMatcher(BaseTool):
    name = "match_resume"
    description = "Score internships based on resume/skills match"

    def __init__(self, resume_path=None):
        self.skills = []
        self.keywords = []
        self.resume_path = resume_path or os.path.expanduser("~/ai-agent/resume.txt")
        self._load_resume()

    def _load_resume(self):
        """Load and parse resume to extract skills"""
        # Default tech skills if no resume found
        default_skills = [
            # Languages
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "r",
            # Web
            "react", "angular", "vue", "node", "express", "django", "flask", "fastapi",
            # Data/ML
            "machine learning", "deep learning", "tensorflow", "pytorch", "pandas", "numpy",
            "data science", "data analysis", "sql", "nosql", "mongodb", "postgresql",
            # Cloud/DevOps
            "aws", "azure", "gcp", "docker", "kubernetes", "ci/cd", "jenkins", "terraform",
            # General
            "git", "linux", "agile", "rest api", "microservices", "algorithms", "data structures"
        ]

        try:
            if os.path.exists(self.resume_path):
                with open(self.resume_path, 'r') as f:
                    content = f.read().lower()
                    # Extract skills from resume
                    self.skills = self._extract_skills(content)
                    print(f"[ResumeMatcher] Loaded {len(self.skills)} skills from resume")
            else:
                print(f"[ResumeMatcher] No resume found at {self.resume_path}, using default skills")
                self.skills = default_skills
        except Exception as e:
            print(f"[ResumeMatcher] Error loading resume: {e}, using defaults")
            self.skills = default_skills

        # Common CS internship keywords
        self.keywords = [
            "software engineer", "software developer", "swe", "backend", "frontend",
            "full stack", "fullstack", "data engineer", "data scientist", "ml engineer",
            "machine learning", "ai", "artificial intelligence", "devops", "cloud",
            "mobile", "ios", "android", "web developer", "api", "infrastructure"
        ]

    def _extract_skills(self, content):
        """Extract technical skills from resume content"""
        # Common tech skills to look for
        tech_patterns = [
            r'\b(python|java|javascript|typescript|c\+\+|c#|golang|go|rust|ruby|php|swift|kotlin|scala)\b',
            r'\b(react|angular|vue|svelte|next\.?js|node\.?js|express|django|flask|fastapi|spring|rails)\b',
            r'\b(aws|azure|gcp|google cloud|docker|kubernetes|k8s|terraform|jenkins|ci/cd)\b',
            r'\b(sql|mysql|postgresql|postgres|mongodb|redis|elasticsearch|dynamodb|firebase)\b',
            r'\b(tensorflow|pytorch|keras|scikit-learn|pandas|numpy|matplotlib|opencv)\b',
            r'\b(machine learning|deep learning|nlp|computer vision|data science|ai)\b',
            r'\b(git|github|gitlab|linux|unix|bash|shell|vim|vscode)\b',
            r'\b(rest|graphql|grpc|microservices|api|websocket)\b',
            r'\b(agile|scrum|jira|confluence|kanban)\b',
        ]

        found_skills = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            found_skills.update([m.lower() for m in matches])

        return list(found_skills) if found_skills else None

    def execute(self, internship_ids=None, update_db=True):
        """Score internships based on resume match"""
        try:
            session = get_db_session()

            if internship_ids:
                internships = session.query(InternshipListing).filter(
                    InternshipListing.id.in_(internship_ids)
                ).all()
            else:
                # Score all unscored internships
                internships = session.query(InternshipListing).filter(
                    InternshipListing.relevance_score == 0.0
                ).all()

            print(f"[ResumeMatcher] Scoring {len(internships)} internships...")

            scored_count = 0
            for internship in internships:
                score = self._calculate_score(internship)

                if update_db:
                    internship.relevance_score = score
                    scored_count += 1

            if update_db:
                session.commit()

            session.close()

            return {
                "success": True,
                "data": {
                    "scored_count": scored_count,
                    "skills_used": len(self.skills)
                }
            }

        except Exception as e:
            print(f"[ResumeMatcher] Error: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_score(self, internship):
        """Calculate relevance score for an internship (0-100)"""
        score = 0
        max_score = 100

        # Combine title, company, location, description for matching
        text = f"{internship.title} {internship.company} {internship.description or ''}".lower()

        # Skill matching (60% of score)
        skill_matches = 0
        for skill in self.skills:
            if skill.lower() in text:
                skill_matches += 1

        if self.skills:
            skill_score = min(60, (skill_matches / len(self.skills)) * 100)
        else:
            skill_score = 30  # Default if no skills

        # Keyword matching (25% of score)
        keyword_matches = 0
        for keyword in self.keywords:
            if keyword.lower() in text:
                keyword_matches += 1

        keyword_score = min(25, (keyword_matches / len(self.keywords)) * 50)

        # Company bonus (15% of score) - FAANG and top companies
        top_companies = [
            "google", "meta", "amazon", "apple", "microsoft", "netflix", "nvidia",
            "openai", "anthropic", "stripe", "airbnb", "uber", "lyft", "doordash",
            "coinbase", "robinhood", "palantir", "databricks", "snowflake", "figma",
            "notion", "discord", "twitch", "spotify", "linkedin", "salesforce",
            "adobe", "oracle", "ibm", "intel", "amd", "qualcomm", "tesla", "spacex"
        ]

        company_lower = internship.company.lower() if internship.company else ""
        company_score = 15 if any(tc in company_lower for tc in top_companies) else 5

        # Calculate final score
        score = skill_score + keyword_score + company_score

        return min(max_score, round(score, 1))

    def get_top_matches(self, limit=20):
        """Get top matching internships"""
        session = get_db_session()

        internships = session.query(InternshipListing).filter(
            InternshipListing.relevance_score > 0
        ).order_by(
            InternshipListing.relevance_score.desc()
        ).limit(limit).all()

        results = []
        for i in internships:
            results.append({
                "id": i.id,
                "title": i.title,
                "company": i.company,
                "location": i.location,
                "score": i.relevance_score,
                "url": i.url
            })

        session.close()
        return results


# Standalone test
if __name__ == "__main__":
    matcher = ResumeMatcher()
    print(f"Skills loaded: {matcher.skills[:10]}...")

    result = matcher.execute()
    print(f"Result: {result}")

    top = matcher.get_top_matches(10)
    print("\nTop 10 matches:")
    for t in top:
        print(f"  [{t['score']}] {t['title']} at {t['company']}")
