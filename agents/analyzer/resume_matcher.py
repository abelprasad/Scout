import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.tools.base import BaseTool
from shared.database.database import get_db_session, InternshipListing
import re

# ---------------------------------------------------------------------------
# Skill categories derived from Abel's resume (resume.pdf)
# Languages: Python, JS, TS, SQL, HTML/CSS
# Backend:   FastAPI, Node.js, Express.js, REST APIs, Power Automate, SQLAlchemy
# Frontend:  React, Next.js, Tailwind CSS, Power Pages
# AI/ML:     LLM Orchestration, Agentic AI, RAG, NLP, spaCy, VADER, Groq, Ollama
# Databases: PostgreSQL, MongoDB, SQLite, Microsoft Dataverse
# Infra:     AWS, GCP, Docker, Linux, Git, PAC CLI, Playwright
# ---------------------------------------------------------------------------

SKILL_CATEGORIES = {
    "languages": {
        "terms": ["python", "javascript", "typescript", "sql", "html", "css"],
        "pts": 0.4,
        "cap": 1.2,
    },
    "backend": {
        "terms": ["fastapi", "node", "node.js", "express", "express.js", "rest", "sqlalchemy", "power automate"],
        "pts": 0.5,
        "cap": 1.5,
    },
    "frontend": {
        "terms": ["react", "next.js", "nextjs", "tailwind", "power pages"],
        "pts": 0.5,
        "cap": 1.2,
    },
    "ai_ml": {
        "terms": ["llm", "rag", "nlp", "spacy", "ollama", "groq", "agentic", "vector", "embedding",
                  "machine learning", "deep learning", "transformer", "langchain", "openai"],
        "pts": 0.6,
        "cap": 1.8,
    },
    "databases": {
        "terms": ["postgresql", "postgres", "mongodb", "sqlite", "supabase", "dataverse", "redis", "mysql"],
        "pts": 0.4,
        "cap": 1.0,
    },
    "infra": {
        "terms": ["aws", "gcp", "docker", "linux", "git", "playwright", "vercel", "kubernetes", "terraform"],
        "pts": 0.3,
        "cap": 0.8,
    },
}

STRONG_TITLE_KEYWORDS = [
    "software engineer", "software developer", "swe",
    "full stack", "fullstack", "full-stack",
    "backend", "back end", "back-end",
    "frontend", "front end", "front-end",
    "web developer",
]

BONUS_TITLE_KEYWORDS = [
    "ai engineer", "ml engineer", "machine learning engineer",
    "devops", "platform engineer", "site reliability",
]

DEALBREAKERS = [
    "hardware engineer", "embedded", "firmware", "fpga", "vhdl", "verilog",
    "electrical engineer", "mechanical engineer",
    "data analyst", "business analyst",
    "marketing", "sales", "recruiter", "recruiting",
    "accounting", "legal", "counsel",
    "graphic design", "graphic designer",
    "product designer", "ux designer",
]


def _load_resume_text(path):
    """Extract plain text from resume.pdf, fall back gracefully."""
    try:
        import pypdf
        reader = pypdf.PdfReader(path)
        return " ".join(page.extract_text() or "" for page in reader.pages).lower()
    except Exception as e:
        print(f"[ResumeMatcher] PDF load failed ({e}), using hardcoded skill profile")
        return ""


class ResumeMatcher(BaseTool):
    name = "match_resume"
    description = "Score internships 0-10 against Abel's resume (v2: skills + location + recency)"

    def __init__(self, resume_path=None):
        self.resume_path = resume_path or os.path.expanduser("~/ai-agent/resume.pdf")
        self.resume_text = _load_resume_text(self.resume_path)
        if self.resume_text:
            print(f"[ResumeMatcher] Loaded resume ({len(self.resume_text)} chars)")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def execute(self, internship_ids=None, update_db=True):
        """Score internships and optionally persist scores to DB."""
        try:
            session = get_db_session()

            if internship_ids:
                internships = session.query(InternshipListing).filter(
                    InternshipListing.id.in_(internship_ids)
                ).all()
            else:
                internships = session.query(InternshipListing).filter(
                    InternshipListing.relevance_score == 0.0
                ).all()

            print(f"[ResumeMatcher] Scoring {len(internships)} internships...")

            for internship in internships:
                internship.relevance_score = self._calculate_score(internship)

            if update_db:
                session.commit()

            scored_count = len(internships)
            session.close()
            return {"success": True, "data": {"scored_count": scored_count}}

        except Exception as e:
            print(f"[ResumeMatcher] Error: {e}")
            return {"success": False, "error": str(e)}

    def get_top_matches(self, limit=20):
        """Return top listings sorted by score desc, discovered_at desc."""
        session = get_db_session()
        internships = (
            session.query(InternshipListing)
            .filter(InternshipListing.relevance_score > 0)
            .order_by(
                InternshipListing.relevance_score.desc(),
                InternshipListing.discovered_at.desc(),
            )
            .limit(limit)
            .all()
        )
        results = [
            {
                "id": i.id,
                "title": i.title,
                "company": i.company,
                "location": i.location,
                "score": i.relevance_score,
                "age_days": i.age_days,
                "url": i.url,
            }
            for i in internships
        ]
        session.close()
        return results

    # ------------------------------------------------------------------
    # v2 Scoring
    # ------------------------------------------------------------------

    def _calculate_score(self, internship):
        """
        Composite score 0-10:
          resume_score  0-6  (skill category matches + title bonus)
          location_score 0-2
          recency_score  0-2
        Dealbreaker roles → 0.0
        """
        title = (internship.title or "").lower()
        company = (internship.company or "").lower()
        description = (internship.description or "").lower()
        requirements = (internship.requirements or "").lower()
        location = (internship.location or "").lower()
        full_text = " ".join([title, company, description, requirements])

        # Dealbreakers
        for term in DEALBREAKERS:
            if term in title:
                return 0.0

        resume_score = self._resume_score(title, full_text)
        location_score = self._location_score(location)
        recency_score = self._recency_score(internship.age_days)

        total = round(resume_score + location_score + recency_score, 2)
        return min(10.0, total)

    def _resume_score(self, title, full_text):
        # Category skill matches
        skill_total = 0.0
        for category in SKILL_CATEGORIES.values():
            hits = sum(1 for term in category["terms"] if term in full_text)
            skill_total += min(category["cap"], hits * category["pts"])
        skill_total = min(4.5, skill_total)

        # Title bonuses
        title_bonus = 0.0
        if any(kw in title for kw in STRONG_TITLE_KEYWORDS):
            title_bonus = 1.5
        elif any(kw in title for kw in BONUS_TITLE_KEYWORDS):
            title_bonus = 0.8

        return min(6.0, skill_total + title_bonus)

    def _location_score(self, location):
        if not location or location in ("", "n/a", "unknown"):
            return 0.5
        loc = location.lower()
        if any(w in loc for w in ["philadelphia", "philly"]):
            return 2.0
        if any(w in loc for w in [" pa", "pennsylvania", " nj", "new jersey", " de", "delaware",
                                   "new york", " ny", "nyc"]):
            return 1.5
        if any(w in loc for w in ["remote", "hybrid", "anywhere"]):
            return 1.0
        # Detect likely international by presence of a country name outside US
        international_signals = ["canada", "united kingdom", "uk", "india", "germany",
                                  "australia", "france", "netherlands", "ireland", "singapore"]
        if any(w in loc for w in international_signals):
            return 0.0
        # Default: other US location
        return 0.3

    def _recency_score(self, age_days):
        if age_days is None:
            return 0.0
        if age_days == 0:
            return 2.0
        if age_days <= 3:
            return 1.5
        if age_days <= 7:
            return 1.0
        if age_days <= 14:
            return 0.5
        return 0.0


# Standalone test / rescore
if __name__ == "__main__":
    matcher = ResumeMatcher()

    # Rescore everything
    from shared.database.database import get_db_session, InternshipListing
    session = get_db_session()
    all_listings = session.query(InternshipListing).all()
    print(f"Rescoring {len(all_listings)} listings...")
    for listing in all_listings:
        listing.relevance_score = matcher._calculate_score(listing)
    session.commit()
    session.close()
    print("Done. Top 20:")

    top = matcher.get_top_matches(20)
    print(f"\n{'#':<3} {'Score':<6} {'Age':>4}d  {'Company':<28} {'Title':<45} {'Location'}")
    print("-" * 120)
    for idx, t in enumerate(top, 1):
        age = f"{t['age_days']}" if t['age_days'] is not None else "?"
        print(f"{idx:<3} {t['score']:<6} {age:>5}  {(t['company'] or '')[:27]:<28} {(t['title'] or '')[:44]:<45} {t['location'] or ''}")
