"""Logging configuration for docAgent application.

This module provides a centralized logging configuration that can be used
throughout the application instead of print statements.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "docAgent", level: int = logging.INFO, log_format: Optional[str] = None
) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
        name: Name of the logger (default: "docAgent")
        level: Logging level (default: INFO)
        log_format: Custom log format string (default: timestamp + level + message)

    Returns:
        Configured logger instance

    Example:
        >>> from utils.logger import setup_logger
        >>> logger = setup_logger(__name__)
        >>> logger.info("Document processing started")
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(level)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Create formatter
        if log_format is None:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)

    return logger


# Create a default logger for the application
logger = setup_logger()
