"""Application configuration."""

import os
from pathlib import Path
from typing import Optional, List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # API Configuration
    api_title: str = "Study Planning Conversational Interface"
    api_description: str = "A RAG-powered API for study planning with document upload and intelligent querying"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Auth0 Configuration
    auth0_domain: Optional[str] = Field(default=None)
    auth0_api_audience: Optional[str] = Field(default=None)
    auth0_algorithms: List[str] = Field(default=["RS256"])
    auth0_issuer: Optional[str] = Field(default=None)

    # MongoDB Configuration
    mongo_uri: str = Field(
        default="mongodb://admin:password@mongodb:27017/?authSource=admin"
    )
    mongo_database_name: str = Field(default="study_planning")
    mongo_max_pool_size: int = Field(default=50)  # Max connections per API instance
    mongo_min_pool_size: int = Field(default=10)  # Min connections to maintain

    # Role Configuration
    admin_role: str = "admin"
    student_role: str = "student"
    allowed_roles: List[str] = ["admin", "student"]

    # Ollama Configuration
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama2")
    ollama_timeout: int = Field(default=180)  # Timeout in seconds for LLM queries (default: 3 minutes)

    # File Storage Configuration
    upload_dir: str = "data/uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: list[str] = [".pdf", ".txt", ".md", ".doc", ".docx", ".xls", ".xlsx"]

    # RAG Configuration
    chromadb_mode: str = Field(default="persistent")  # "persistent" or "client"
    chromadb_path: str = "data/chroma_db"
    chromadb_host: str = Field(default="chromadb-server")  # For client mode
    chromadb_port: int = Field(default=8000)  # For client mode
    collection_name: str = "study_documents"
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunks_for_context: int = 5

    # LLM Response Configuration
    default_language: str = Field(default="auto")  # "auto", "spanish", "english"
    response_instructions: str = Field(default="")
    max_context_length: int = Field(default=1500)

    # Adaptive RAG Routing Configuration
    enable_adaptive_routing: bool = Field(default=True)
    routing_mode: str = Field(default="hybrid")  # "heuristic", "llm", or "hybrid"
    routing_confidence_threshold: float = Field(default=0.7)

    # Agent Configuration
    enable_agent_tools: bool = Field(default=True, description="Enable agentic tool execution")
    agent_provider: str = Field(default="local", description="Agent provider: 'local' or 'api'")
    agent_max_iterations: int = Field(default=5, description="Maximum agent execution iterations")
    agent_auto_approve_reads: bool = Field(default=True, description="Auto-approve read-only tool executions")
    agent_auto_approve_writes: bool = Field(default=False, description="Auto-approve write tool executions")

    # External Agent API Configuration (for future use)
    agent_api_url: Optional[str] = Field(default=None, description="External agent API base URL")
    agent_api_key: Optional[str] = Field(default=None, description="External agent API key")
    agent_api_timeout: int = Field(default=30, description="External agent API timeout in seconds")
    agent_fallback_to_local: bool = Field(default=True, description="Fallback to local provider if API fails")

    # CORS Configuration (accepts JSON array or comma-separated string)
    cors_origins: Union[str, List[str]] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )
    cors_methods: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
    cors_headers: List[str] = ["*"]

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("auth0_algorithms", mode="before")
    @classmethod
    def parse_auth0_algorithms(cls, v):
        """Parse AUTH0_ALGORITHMS from string or list."""
        if isinstance(v, str):
            # Handle JSON-like string format: ["RS256"]
            v = v.strip()
            if v.startswith('[') and v.endswith(']'):
                # Remove brackets and quotes, split by comma
                v = v[1:-1].replace('"', '').replace("'", '').strip()
                if v:
                    return [alg.strip() for alg in v.split(',')]
                return ["RS256"]
            # Handle comma-separated format: RS256,HS256
            return [alg.strip() for alg in v.split(',')]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            # Split by comma and strip whitespace
            origins = [origin.strip() for origin in v.split(',') if origin.strip()]
            return origins if origins else ["http://localhost:3000", "http://localhost:8000"]
        elif isinstance(v, list):
            return v
        # Fallback to default
        return ["http://localhost:3000", "http://localhost:8000"]

    @model_validator(mode="after")
    def create_directories_and_normalize(self):
        """Ensure required directories exist and normalize fields."""
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)
        Path(self.chromadb_path).mkdir(parents=True, exist_ok=True)

        # Ensure cors_origins is always a list
        if isinstance(self.cors_origins, str):
            self.cors_origins = [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

        return self


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings
