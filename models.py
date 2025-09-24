# models.py
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, LargeBinary, MetaData, String, Table, create_engine
from config import config

# Database setup
engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False}
)
metadata = MetaData()

images_tbl = Table(
    "images", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("filename", String, nullable=False),
    Column("caption", String, nullable=True),
    Column("embedding", LargeBinary, nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

interactions_tbl = Table(
    "interactions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("image_id", Integer, nullable=True),
    Column("user_prompt", String, nullable=True),
    Column("model_response", String, nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)


def create_tables():
    metadata.create_all(engine)
