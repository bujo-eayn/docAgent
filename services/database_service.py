# services/database_service.py
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from models import Image, Interaction, SessionLocal
import numpy as np


class DatabaseService:
    def __init__(self):
        pass

    def get_session(self):
        """Get a new database session"""
        return SessionLocal()

    def create_image_record(self, filename: str) -> int:
        """Create initial image record and return image_id"""
        db = self.get_session()
        try:
            image = Image(
                filename=filename,
                caption=None,
                embedding=None,
                created_at=datetime.utcnow()
            )
            db.add(image)
            db.commit()
            db.refresh(image)
            return image.id
        finally:
            db.close()

    def create_interaction_record(self, image_id: int, user_prompt: str):
        """Create interaction record"""
        db = self.get_session()
        try:
            interaction = Interaction(
                image_id=image_id,
                user_prompt=user_prompt,
                model_response=None,
                created_at=datetime.utcnow()
            )
            db.add(interaction)
            db.commit()
        finally:
            db.close()

    def update_image_with_response(self, image_id: int, caption: str, embedding_array: np.ndarray):
        """Update image record with caption and embedding vector"""
        db = self.get_session()
        try:
            image = db.query(Image).filter(Image.id == image_id).first()
            if image:
                image.caption = caption
                if embedding_array is not None:
                    # Convert numpy array to list for pgvector
                    image.embedding = embedding_array.tolist()
                db.commit()
        finally:
            db.close()

    def update_interaction_response(self, image_id: int, model_response: str):
        """Update interaction record with model response"""
        db = self.get_session()
        try:
            interaction = db.query(Interaction).filter(
                Interaction.image_id == image_id
            ).order_by(Interaction.created_at.desc()).first()

            if interaction:
                interaction.model_response = model_response
                db.commit()
        finally:
            db.close()

    def get_all_images(self):
        """Get all image records"""
        db = self.get_session()
        try:
            images = db.query(Image).all()
            return [
                {
                    "id": img.id,
                    "filename": img.filename,
                    "caption": img.caption,
                    "created_at": img.created_at.isoformat()
                }
                for img in images
            ]
        finally:
            db.close()

    def get_image_by_id(self, image_id: int):
        """Get single image record by ID"""
        db = self.get_session()
        try:
            image = db.query(Image).filter(Image.id == image_id).first()
            if not image:
                return None
            return {
                "id": image.id,
                "filename": image.filename,
                "caption": image.caption,
                "created_at": image.created_at.isoformat()
            }
        finally:
            db.close()

    def search_similar_images(self, query_embedding: np.ndarray, top_k: int = 2):
        """
        Search for similar images using pgvector cosine similarity
        Returns list of dicts: {"id": image_id, "caption": caption, "distance": distance}
        """
        db = self.get_session()
        try:
            # Convert numpy array to list for pgvector
            query_list = query_embedding.tolist()

            # Use pgvector's cosine distance operator <=>
            # Lower distance = more similar
            query = text("""
                SELECT id, caption, embedding <=> :query_embedding AS distance
                FROM images
                WHERE embedding IS NOT NULL
                ORDER BY distance
                LIMIT :limit
            """)

            result = db.execute(
                query,
                {"query_embedding": str(query_list), "limit": top_k}
            )

            similar_images = []
            for row in result:
                similar_images.append({
                    "id": row.id,
                    "caption": row.caption,
                    "distance": float(row.distance)
                })

            return similar_images
        finally:
            db.close()
