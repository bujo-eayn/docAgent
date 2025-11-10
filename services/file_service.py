# services/file_service.py
"""File service for handling uploaded document files.

This service manages the storage and retrieval of uploaded document files.
"""
import os
import time

from config import config


class FileService:
    """Service for handling file uploads and storage."""

    def __init__(self):
        """Initialize the file service with images directory from config."""
        self.images_dir = config.images_dir

    def save_uploaded_file(self, file_contents: bytes, original_filename: str) -> str:
        """Save uploaded file with timestamp prefix.

        Args:
            file_contents: Raw bytes of the uploaded file
            original_filename: Original name of the uploaded file

        Returns:
            The saved filename with timestamp prefix

        Raises:
            IOError: If file cannot be written to disk
        """
        timestamp = int(time.time() * 1000)
        filename = f"{timestamp}_{original_filename}"
        path = os.path.join(self.images_dir, filename)

        with open(path, "wb") as f:
            f.write(file_contents)

        return filename
