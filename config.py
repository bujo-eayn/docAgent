# config.py
import os


class Config:
    OLLAMA_URL = os.environ.get(
        "OLLAMA_URL", "http://host.docker.internal:11434")
    MODEL_NAME = os.environ.get("MODEL_NAME", "gemma3")
    BASE_DIR = os.environ.get("DATA_DIR", "./data")

    @property
    def IMAGES_DIR(self):
        return os.path.join(self.BASE_DIR, "images")

    @property
    def DB_PATH(self):
        return os.path.join(self.BASE_DIR, "memory.db")

    def ensure_directories(self):
        os.makedirs(self.IMAGES_DIR, exist_ok=True)
        os.makedirs(self.BASE_DIR, exist_ok=True)


config = Config()
