# models.py - Redesign for Chat-Based Workflow
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey, Boolean, create_engine, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from pgvector.sqlalchemy import Vector
from config import config

Base = declarative_base()


class Chat(Base):
    """Represents a conversation session"""
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Auto-generated from first image
    title = Column(String(255), nullable=True)
    # Original uploaded document
    document_filename = Column(String(255), nullable=False)
    document_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    contexts = relationship(
        "ChatContext", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan")


class ChatContext(Base):
    """Stores extracted information chunks from the document with embeddings"""
    __tablename__ = "chat_contexts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey(
        "chats.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)  # Extracted text chunk
    # Embedding for semantic search
    embedding = Column(Vector(1024), nullable=True)
    chunk_index = Column(Integer, nullable=False)  # Order of extraction
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    chat = relationship("Chat", back_populates="contexts")

    # Create IVFFlat index for fast similarity search
    __table_args__ = (
        Index(
            'chat_contexts_embedding_idx',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )


class Message(Base):
    """Stores conversation messages (user questions and AI responses)"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey(
        "chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    # Context retrieved for this message
    context_used = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    chat = relationship("Chat", back_populates="messages")


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
