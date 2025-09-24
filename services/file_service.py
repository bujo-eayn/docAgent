# services/file_service.py
import os
import time
from config import config


class FileService:
    def __init__(self):
        self.images_dir = config.IMAGES_DIR

    def save_uploaded_file(self, file_contents: bytes, original_filename: str) -> str:
        """Save uploaded file and return the saved filename"""
        timestamp = int(time.time() * 1000)
        filename = f"{timestamp}_{original_filename}"
        path = os.path.join(self.images_dir, filename)

        with open(path, "wb") as f:
            f.write(file_contents)

        return filename
