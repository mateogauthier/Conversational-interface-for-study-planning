"""API dependencies and dependency injection."""

from fastapi import Depends
from app.services.file_service import FileService, file_service
from app.services.llm_service import LLMService, llm_service  
from app.services.rag_service import RAGService, rag_service
from app.core.config import Settings, get_settings


def get_file_service() -> FileService:
    """Get file service dependency."""
    return file_service


def get_llm_service() -> LLMService:
    """Get LLM service dependency."""
    return llm_service


def get_rag_service() -> RAGService:
    """Get RAG service dependency."""
    return rag_service


def get_app_settings() -> Settings:
    """Get application settings dependency."""
    return get_settings()
