# services/chat_service.py - Chat Management Service
"""Chat service for managing chat sessions and messages.

This service handles all database operations related to:
- Chat sessions (create, retrieve, list, delete)
- Chat contexts (add chunks, search with pgvector)
- Messages (add, retrieve conversation history)
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from constants import IVFFLAT_INDEX_LISTS, IVFFLAT_INDEX_NAME
from models import Chat, ChatContext, Message, SessionLocal
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ChatService:
    """Service for managing chat sessions, contexts, and messages."""

    def __init__(self):
        """Initialize chat service."""
        pass

    def get_session(self):
        """Get a new database session"""
        return SessionLocal()

    def create_chat(
        self, document_filename: str, document_path: str, title: Optional[str] = None
    ) -> int:
        """Create a new chat session"""
        db = self.get_session()
        try:
            # Generate title from filename if not provided
            if not title:
                title = f"Chat: {document_filename[:50]}"

            chat = Chat(
                title=title,
                document_filename=document_filename,
                document_path=document_path,
                created_at=datetime.now(timezone.utc),
                is_active=True,
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return chat.id
        finally:
            db.close()

    def get_chat(self, chat_id: int) -> Optional[Dict]:
        """Get chat by ID"""
        db = self.get_session()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if not chat:
                return None
            return {
                "id": chat.id,
                "title": chat.title,
                "document_filename": chat.document_filename,
                "created_at": chat.created_at.isoformat(),
                "updated_at": chat.updated_at.isoformat(),
                "message_count": len(chat.messages),
            }
        finally:
            db.close()

    def get_all_chats(self) -> List[Dict]:
        """Get all chats ordered by most recent"""
        db = self.get_session()
        try:
            chats = (
                db.query(Chat)
                .filter(Chat.is_active == True)
                .order_by(desc(Chat.updated_at))
                .all()
            )
            return [
                {
                    "id": chat.id,
                    "title": chat.title,
                    "document_filename": chat.document_filename,
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat(),
                    "message_count": len(chat.messages),
                }
                for chat in chats
            ]
        finally:
            db.close()

    def delete_chat(self, chat_id: int) -> bool:
        """Soft delete a chat"""
        db = self.get_session()
        try:
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.is_active = False
                db.commit()
                return True
            return False
        finally:
            db.close()

    def add_context_chunk(
        self, chat_id: int, content: str, embedding: np.ndarray, chunk_index: int
    ):
        """Add a context chunk to a chat"""
        db = self.get_session()
        try:
            context = ChatContext(
                chat_id=chat_id,
                content=content,
                embedding=embedding.tolist() if embedding is not None else None,
                chunk_index=chunk_index,
                created_at=datetime.now(timezone.utc),
            )
            db.add(context)
            db.commit()
        finally:
            db.close()

    def search_context(
        self, chat_id: int, query_embedding: np.ndarray, top_k: int = 3
    ) -> List[Dict]:
        """Search for relevant context within a specific chat using pgvector"""
        db = self.get_session()
        try:
            query_list = query_embedding.tolist()

            # Use pgvector's cosine distance with IVFFlat index
            query = text(
                """
                SELECT id, content, embedding <=> :query_embedding AS distance
                FROM chat_contexts
                WHERE chat_id = :chat_id AND embedding IS NOT NULL
                ORDER BY distance
                LIMIT :limit
            """
            )

            result = db.execute(
                query,
                {
                    "query_embedding": str(query_list),
                    "chat_id": chat_id,
                    "limit": top_k,
                },
            )

            contexts = []
            for row in result:
                contexts.append(
                    {
                        "id": row.id,
                        "content": row.content,
                        "distance": float(row.distance),
                        "similarity": 1 - float(row.distance),
                    }
                )

            return contexts
        finally:
            db.close()

    def add_message(
        self, chat_id: int, role: str, content: str, context_used: Optional[str] = None
    ):
        """Add a message to the chat"""
        db = self.get_session()
        try:
            message = Message(
                chat_id=chat_id,
                role=role,
                content=content,
                context_used=context_used,
                created_at=datetime.now(timezone.utc),
            )
            db.add(message)

            # Update chat's updated_at timestamp
            chat = db.query(Chat).filter(Chat.id == chat_id).first()
            if chat:
                chat.updated_at = datetime.now(timezone.utc)

            db.commit()
        finally:
            db.close()

    def get_chat_messages(self, chat_id: int) -> List[Dict]:
        """Get all messages in a chat"""
        db = self.get_session()
        try:
            messages = (
                db.query(Message)
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at)
                .all()
            )

            return [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "context_used": msg.context_used,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        finally:
            db.close()

    def create_ivfflat_index(self):
        """Create IVFFlat index for faster similarity search (run after adding many contexts)"""
        db = self.get_session()
        try:
            # Check if index already exists
            query = text(
                """
                SELECT 1 FROM pg_indexes 
                WHERE indexname = 'chat_contexts_embedding_idx'
            """
            )
            result = db.execute(query).fetchone()

            if not result:
                # Create index
                create_index = text(
                    """
                    CREATE INDEX chat_contexts_embedding_idx 
                    ON chat_contexts 
                    USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100)
                """
                )
                db.execute(create_index)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error creating IVFFlat index: {e}", exc_info=True)
            return False
        finally:
            db.close()
