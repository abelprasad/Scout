# Internships mission storage.
# InternshipListing keeps its original table name and columns so the
# existing internships.db keeps working with zero migration.
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from datetime import datetime

from core.database import Base, session_for


DB_FILENAME = "internships.db"


class InternshipListing(Base):
    __tablename__ = "internship_listings"

    id = Column(Integer, primary_key=True)
    agent_job_id = Column(String)
    title = Column(String)
    company = Column(String)
    url = Column(String, unique=True)
    location = Column(String)
    description = Column(Text)
    requirements = Column(Text)
    deadline = Column(String)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    # Application tracking
    applied = Column(Boolean, default=False)
    application_date = Column(DateTime, nullable=True)
    application_status = Column(String, default="not_applied")
    notes = Column(Text)

    # Quality scoring
    relevance_score = Column(Float, default=0.0)
    interest_level = Column(Integer, default=0)

    # Posting age (days since posted)
    age_days = Column(Integer, nullable=True)


def get_db_session():
    return session_for(DB_FILENAME)


def save_internship(session, listing_data, agent_job_id):
    existing = session.query(InternshipListing).filter_by(url=listing_data["url"]).first()
    if existing:
        print("[Database] Internship already exists: {}".format(listing_data.get("title")))
        return existing
    internship = InternshipListing(
        agent_job_id=agent_job_id,
        title=listing_data.get("title", "Unknown Position"),
        company=listing_data.get("company", "Unknown Company"),
        url=listing_data["url"],
        location=listing_data.get("location", ""),
        description=listing_data.get("description", ""),
        requirements=listing_data.get("requirements", ""),
        deadline=listing_data.get("deadline", ""),
    )
    session.add(internship)
    session.commit()
    print("[Database] Saved new internship: {} at {}".format(internship.title, internship.company))
    return internship


def get_recent_internships(limit=20):
    session = get_db_session()
    try:
        return session.query(InternshipListing).order_by(
            InternshipListing.discovered_at.desc()).limit(limit).all()
    finally:
        session.close()


def mark_as_applied(internship_id, notes=""):
    session = get_db_session()
    try:
        internship = session.query(InternshipListing).get(internship_id)
        if internship:
            internship.applied = True
            internship.application_date = datetime.utcnow()
            internship.application_status = "applied"
            internship.notes = notes
            session.commit()
            print("[Database] Marked as applied: {}".format(internship.title))
    finally:
        session.close()
