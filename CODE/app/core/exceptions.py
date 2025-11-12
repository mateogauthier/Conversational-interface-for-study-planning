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


class AuthenticationException(StudyPlanningException):
    """Exception raised when authentication fails."""
    pass


class AuthorizationException(StudyPlanningException):
    """Exception raised when authorization fails (insufficient permissions)."""
    pass


class TokenExpiredException(AuthenticationException):
    """Exception raised when JWT token has expired."""
    pass


class UserNotFoundException(StudyPlanningException):
    """Exception raised when user is not found."""
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


class UnauthorizedHTTPException(HTTPException):
    """Unauthorized HTTP exception (401)."""

    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=401,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenHTTPException(HTTPException):
    """Forbidden HTTP exception (403)."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            detail=detail
        )


class TokenExpiredHTTPException(HTTPException):
    """Token expired HTTP exception (401)."""

    def __init__(self):
        super().__init__(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
