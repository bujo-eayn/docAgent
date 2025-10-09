# models.py
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from config import config

Base = declarative_base()


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    caption = Column(Text, nullable=True)
    embedding = Column(Vector(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(Integer, nullable=True)
    user_prompt = Column(Text, nullable=True)
    model_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Database setup
engine = create_engine(config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all tables and enable pgvector extension"""
    from sqlalchemy import text

    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create tables
    Base.metadata.create_all(engine)


def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
