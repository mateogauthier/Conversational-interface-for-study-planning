"""Configuration for Agent API."""

import os
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent API settings."""

    # API Configuration
    api_title: str = "Agent Tools API"
    api_version: str = "1.0.0"
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8002, description="API port")
    debug: bool = Field(default=True, description="Debug mode")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:8000,http://localhost:3000",
        description="Allowed CORS origins (comma-separated)"
    )

    # Main API URL (for HTTP communication)
    main_api_url: str = Field(
        default="http://fastapi-app:8000",
        description="Main API base URL for HTTP requests"
    )

    # Security - Internal Service Key
    internal_service_key: str = Field(
        default="dev-internal-service-key-change-in-production",
        description="Shared secret for service-to-service authentication"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Settings = None


def get_settings() -> Settings:
    """Get settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
