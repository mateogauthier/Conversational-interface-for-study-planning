"""Custom exceptions for the application."""

from fastapi import HTTPException
from typing import Any, Dict, Optional


class StudyPlanningException(Exception):
    """Base exception for study planning application."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class FileProcessingException(StudyPlanningException):
    """Exception raised when file processing fails."""
    pass


class RAGException(StudyPlanningException):
    """Exception raised when RAG operations fail."""
    pass


class LLMException(StudyPlanningException):
    """Exception raised when LLM operations fail."""
    pass


class FileValidationException(StudyPlanningException):
    """Exception raised when file validation fails."""
    pass


# HTTP Exceptions
class FileNotFoundHTTPException(HTTPException):
    """File not found HTTP exception."""
    
    def __init__(self, filename: str):
        super().__init__(
            status_code=404,
            detail=f"File '{filename}' not found"
        )


class FileTypeNotSupportedHTTPException(HTTPException):
    """File type not supported HTTP exception."""
    
    def __init__(self, file_type: str, supported_types: list[str]):
        super().__init__(
            status_code=400,
            detail=f"File type '{file_type}' not supported. Supported types: {', '.join(supported_types)}"
        )


class FileTooLargeHTTPException(HTTPException):
    """File too large HTTP exception."""
    
    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            status_code=413,
            detail=f"File size {file_size} bytes exceeds maximum allowed size of {max_size} bytes"
        )


class RAGNotAvailableHTTPException(HTTPException):
    """RAG service not available HTTP exception."""
    
    def __init__(self, reason: str = "RAG service unavailable"):
        super().__init__(
            status_code=503,
            detail=f"RAG service is not available: {reason}"
        )


class LLMNotAvailableHTTPException(HTTPException):
    """LLM service not available HTTP exception."""
    
    def __init__(self, reason: str = "LLM service unavailable"):
        super().__init__(
            status_code=503,
            detail=f"LLM service is not available: {reason}"
        )
