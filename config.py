"""Application configuration using Pydantic Settings.

This module provides type-safe configuration management with environment variable
support and validation. All configuration values can be overridden via environment
variables or a .env file.
"""

import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from constants import (
    CHAT_MODEL_NAME,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_TOP_K_CONTEXTS,
    EMBEDDING_MODEL_NAME,
    OLLAMA_CHAT_TIMEOUT,
    OLLAMA_EMBED_TIMEOUT,
    OLLAMA_EXTRACTION_TIMEOUT,
)


class Settings(BaseSettings):
    """Application settings with environment variable support.

    All settings can be configured via environment variables.
    Default values are provided for development/Docker environments.
    """

    # Ollama Configuration
    ollama_url: str = Field(
        default="http://host.docker.internal:11434",
        description="URL of the Ollama service",
    )
    model_name: str = Field(
        default=CHAT_MODEL_NAME, description="Name of the chat model to use"
    )
    embedding_model_name: str = Field(
        default=EMBEDDING_MODEL_NAME, description="Name of the embedding model to use"
    )

    # Directory Configuration
    base_dir: str = Field(
        default="./data",
        alias="DATA_DIR",
        description="Base directory for data storage",
    )

    # PostgreSQL Configuration
    postgres_user: str = Field(default="postgres", description="PostgreSQL username")
    postgres_password: str = Field(
        default="postgres", description="PostgreSQL password"
    )
    postgres_db: str = Field(default="docAgent", description="PostgreSQL database name")
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: str = Field(default="5432", description="PostgreSQL port")

    # Document Processing Configuration
    chunk_size: int = Field(
        default=DEFAULT_CHUNK_SIZE, description="Size of text chunks for embedding"
    )
    chunk_overlap: int = Field(
        default=DEFAULT_CHUNK_OVERLAP, description="Overlap between consecutive chunks"
    )
    top_k_contexts: int = Field(
        default=DEFAULT_TOP_K_CONTEXTS,
        description="Number of relevant contexts to retrieve",
    )

    # Timeout Configuration
    embed_timeout: int = Field(
        default=OLLAMA_EMBED_TIMEOUT,
        description="Timeout for embedding requests (seconds)",
    )
    chat_timeout: int = Field(
        default=OLLAMA_CHAT_TIMEOUT, description="Timeout for chat requests (seconds)"
    )
    extraction_timeout: int = Field(
        default=OLLAMA_EXTRACTION_TIMEOUT,
        description="Timeout for document extraction (seconds)",
    )

    @field_validator("chunk_size")
    @classmethod
    def validate_chunk_size(cls, v: int) -> int:
        """Validate chunk size is reasonable."""
        if v < 100 or v > 5000:
            raise ValueError("chunk_size must be between 100 and 5000")
        return v

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int) -> int:
        """Validate chunk overlap is reasonable."""
        if v < 0 or v > 500:
            raise ValueError("chunk_overlap must be between 0 and 500")
        return v

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL database URL."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def images_dir(self) -> str:
        """Get path to images directory."""
        return os.path.join(self.base_dir, "images")

    def ensure_directories(self) -> None:
        """Create required directories if they don't exist."""
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.base_dir, exist_ok=True)

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow both snake_case and uppercase environment variables
        populate_by_name = True


# Create global settings instance
settings = Settings()

# Keep backward compatibility with old code
config = settings
