"""Custom exception classes for docAgent application.

This module defines application-specific exceptions for better error handling
and debugging. All custom exceptions inherit from DocAgentException base class.
"""


class DocAgentException(Exception):
    """Base exception class for all docAgent exceptions."""

    def __init__(self, message: str, details: dict = None):
        """Initialize exception with message and optional details.

        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error context
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ChatNotFoundException(DocAgentException):
    """Raised when a requested chat session is not found."""

    def __init__(self, chat_id: int):
        """Initialize with chat ID.

        Args:
            chat_id: The ID of the chat that was not found
        """
        message = f"Chat with ID {chat_id} not found"
        super().__init__(message, {"chat_id": chat_id})


class DocumentProcessingException(DocAgentException):
    """Raised when document processing fails."""

    def __init__(self, filename: str, reason: str):
        """Initialize with filename and failure reason.

        Args:
            filename: Name of the document that failed to process
            reason: Description of why processing failed
        """
        message = f"Failed to process document '{filename}': {reason}"
        super().__init__(message, {"filename": filename, "reason": reason})


class OllamaServiceException(DocAgentException):
    """Raised when Ollama service is unavailable or returns errors."""

    def __init__(self, endpoint: str, reason: str):
        """Initialize with endpoint and failure reason.

        Args:
            endpoint: The Ollama endpoint that failed
            reason: Description of the failure
        """
        message = f"Ollama service error at {endpoint}: {reason}"
        super().__init__(message, {"endpoint": endpoint, "reason": reason})


class EmbeddingException(DocAgentException):
    """Raised when embedding generation fails."""

    def __init__(self, text_preview: str, reason: str):
        """Initialize with text preview and failure reason.

        Args:
            text_preview: First 100 characters of text that failed to embed
            reason: Description of the failure
        """
        message = f"Failed to generate embedding: {reason}"
        super().__init__(
            message, {"text_preview": text_preview[:100], "reason": reason}
        )


class DatabaseException(DocAgentException):
    """Raised when database operations fail."""

    def __init__(self, operation: str, reason: str):
        """Initialize with operation type and failure reason.

        Args:
            operation: The database operation that failed (e.g., 'insert', 'query')
            reason: Description of the failure
        """
        message = f"Database operation '{operation}' failed: {reason}"
        super().__init__(message, {"operation": operation, "reason": reason})


class FileUploadException(DocAgentException):
    """Raised when file upload validation or processing fails."""

    def __init__(self, filename: str, reason: str):
        """Initialize with filename and failure reason.

        Args:
            filename: Name of the file that failed to upload
            reason: Description of why upload failed
        """
        message = f"Failed to upload file '{filename}': {reason}"
        super().__init__(message, {"filename": filename, "reason": reason})


class InvalidFileTypeException(FileUploadException):
    """Raised when uploaded file type is not allowed."""

    def __init__(self, filename: str, file_type: str, allowed_types: list):
        """Initialize with file details.

        Args:
            filename: Name of the uploaded file
            file_type: The file extension that was rejected
            allowed_types: List of allowed file extensions
        """
        reason = (
            f"File type '{file_type}' not allowed. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
        super().__init__(filename, reason)
        self.details["file_type"] = file_type
        self.details["allowed_types"] = allowed_types


class ConfigurationException(DocAgentException):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, config_key: str, reason: str):
        """Initialize with configuration key and issue description.

        Args:
            config_key: The configuration parameter that has an issue
            reason: Description of the configuration problem
        """
        message = f"Configuration error for '{config_key}': {reason}"
        super().__init__(message, {"config_key": config_key, "reason": reason})
