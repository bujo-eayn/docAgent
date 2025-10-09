# config.py
import os


class Config:
    OLLAMA_URL = os.environ.get(
        "OLLAMA_URL", "http://host.docker.internal:11434")
    MODEL_NAME = os.environ.get("MODEL_NAME", "gemma3")
    BASE_DIR = os.environ.get("DATA_DIR", "./data")

    # PostgreSQL configuration
    POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "docAgent")
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")


    @property
    def DATABASE_URL(self):
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def IMAGES_DIR(self):
        return os.path.join(self.BASE_DIR, "images")

    def ensure_directories(self):
        os.makedirs(self.IMAGES_DIR, exist_ok=True)
        os.makedirs(self.BASE_DIR, exist_ok=True)


config = Config()
