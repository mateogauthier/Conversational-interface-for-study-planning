"""Application configuration."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_title: str = "Study Planning Conversational Interface"
    api_description: str = "A RAG-powered API for study planning with document upload and intelligent querying"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama2", env="OLLAMA_MODEL")
    ollama_timeout: int = 90  # Balanced timeout for RAG queries
    
    # File Storage Configuration
    upload_dir: str = "data/uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: list[str] = [".pdf", ".txt", ".md", ".doc", ".docx", ".xls", ".xlsx"]
    
    # RAG Configuration
    chromadb_path: str = "data/chroma_db"
    collection_name: str = "study_documents"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunks_for_context: int = 5
    
    # LLM Response Configuration
    default_language: str = Field(default="auto", env="DEFAULT_LANGUAGE")  # "auto", "spanish", "english"
    response_instructions: str = Field(default="", env="RESPONSE_INSTRUCTIONS")
    max_context_length: int = Field(default=1500, env="MAX_CONTEXT_LENGTH")
    
    # CORS Configuration
    cors_origins: list[str] = ["*"]
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]
    
    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.chromadb_path).mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
