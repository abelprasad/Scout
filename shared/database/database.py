from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class AgentJob(Base):
    __tablename__ = "agent_jobs"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True)  # The UUID from FastAPI
    goal = Column(Text)
    status = Column(String)  # queued, running, completed, failed
    result_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class InternshipListing(Base):
    __tablename__ = "internship_listings"
    
    id = Column(Integer, primary_key=True)
    agent_job_id = Column(String)  # Links back to the job that found it
    title = Column(String)
    company = Column(String)
    url = Column(String, unique=True)  # Prevent duplicate URLs
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
    application_status = Column(String, default="not_applied")  # not_applied, applied, interview, rejected, offer
    notes = Column(Text)
    
    # Quality scoring
    relevance_score = Column(Float, default=0.0)
    interest_level = Column(Integer, default=0)  # 1-5 scale

def get_database_url():
    """Get database file path"""
    db_path = os.path.expanduser("~/ai-agent/internships.db")
    return f"sqlite:///{db_path}"

def init_database():
    """Initialize database and return engine and session factory"""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    return engine, SessionLocal

def get_db_session():
    """Get a database session"""
    _, SessionLocal = init_database()
    return SessionLocal()

# Utility functions
def save_internship(session, listing_data, agent_job_id):
    """Save an internship listing to database"""
    # Check if URL already exists
    existing = session.query(InternshipListing).filter_by(url=listing_data['url']).first()
    if existing:
        print(f"[Database] Internship already exists: {listing_data['title']}")
        return existing
    
    # Create new listing
    internship = InternshipListing(
        agent_job_id=agent_job_id,
        title=listing_data.get('title', 'Unknown Position'),
        company=listing_data.get('company', 'Unknown Company'),
        url=listing_data['url'],
        location=listing_data.get('location', ''),
        description=listing_data.get('description', ''),
        requirements=listing_data.get('requirements', ''),
        deadline=listing_data.get('deadline', ''),
    )
    
    session.add(internship)
    session.commit()
    print(f"[Database] Saved new internship: {internship.title} at {internship.company}")
    return internship

def get_recent_internships(limit=20):
    """Get recently discovered internships"""
    session = get_db_session()
    internships = session.query(InternshipListing)\
                        .order_by(InternshipListing.discovered_at.desc())\
                        .limit(limit).all()
    session.close()
    return internships

def mark_as_applied(internship_id, notes=""):
    """Mark an internship as applied to"""
    session = get_db_session()
    internship = session.query(InternshipListing).get(internship_id)
    if internship:
        internship.applied = True
        internship.application_date = datetime.utcnow()
        internship.application_status = "applied"
        internship.notes = notes
        session.commit()
        print(f"[Database] Marked as applied: {internship.title}")
    session.close()
