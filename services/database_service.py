# services/database_service.py
from datetime import datetime
from sqlalchemy import insert, select, update
from models import engine, images_tbl, interactions_tbl


class DatabaseService:
    def __init__(self):
        self.engine = engine

    def create_image_record(self, filename: str):
        """Create initial image record and return image_id"""
        with self.engine.begin() as conn:
            res = conn.execute(
                insert(images_tbl).values(
                    filename=filename,
                    caption=None,
                    embedding=None,
                    created_at=datetime.utcnow(),
                )
            )
            return res.inserted_primary_key[0]

    def create_interaction_record(self, image_id: int, user_prompt: str):
        """Create interaction record"""
        with self.engine.begin() as conn:
            conn.execute(
                insert(interactions_tbl).values(
                    image_id=image_id,
                    user_prompt=user_prompt,
                    model_response=None,
                    created_at=datetime.utcnow(),
                )
            )

    def update_image_with_response(self, image_id: int, caption: str, embedding_bytes: bytes):
        """Update image record with caption and embedding"""
        with self.engine.begin() as conn:
            conn.execute(
                images_tbl.update()
                .where(images_tbl.c.id == image_id)
                .values(caption=caption, embedding=embedding_bytes)
            )

    def update_interaction_response(self, image_id: int, model_response: str):
        """Update interaction record with model response"""
        with self.engine.begin() as conn:
            conn.execute(
                interactions_tbl.update()
                .where(interactions_tbl.c.image_id == image_id)
                .values(model_response=model_response)
            )

    def get_all_images(self):
        """Get all image records"""
        with self.engine.connect() as conn:
            rows = conn.execute(select(images_tbl)).fetchall()
            return [
                {
                    "id": r.id,
                    "filename": r.filename,
                    "caption": r.caption,
                    "created_at": r.created_at.isoformat()
                }
                for r in rows
            ]

    def get_image_by_id(self, image_id: int):
        """Get single image record by ID"""
        with self.engine.connect() as conn:
            r = conn.execute(
                select(images_tbl).where(images_tbl.c.id == image_id)
            ).first()
            if not r:
                return None
            return {
                "id": r.id,
                "filename": r.filename,
                "caption": r.caption,
                "created_at": r.created_at.isoformat()
            }

    def get_embeddings_data(self):
        """Get all records with embeddings for FAISS indexing"""
        with self.engine.connect() as conn:
            return conn.execute(
                select(images_tbl.c.id, images_tbl.c.embedding,
                       images_tbl.c.caption)
            ).fetchall()
