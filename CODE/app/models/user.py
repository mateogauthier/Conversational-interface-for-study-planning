"""User-related Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class UserStatisticsResponse(BaseModel):
    """User statistics for API responses."""

    total_uploads: int = Field(..., description="Total number of files uploaded")
    total_queries: int = Field(..., description="Total number of RAG queries made")
    total_storage_bytes: int = Field(..., description="Total storage used in bytes")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


class UserResponse(BaseModel):
    """User response model for API."""

    id: str = Field(..., description="MongoDB user ID")
    auth0_id: str = Field(..., description="Auth0 user ID")
    email: EmailStr = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    role: str = Field(..., description="User role (admin or student)")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    statistics: UserStatisticsResponse = Field(..., description="User statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "auth0_id": "auth0|123456789",
                "email": "student@example.com",
                "name": "John Doe",
                "role": "student",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-10T12:00:00Z",
                "statistics": {
                    "total_uploads": 5,
                    "total_queries": 23,
                    "total_storage_bytes": 1024000,
                    "last_activity": "2025-01-10T12:00:00Z"
                }
            }
        }


class UserProfileUpdate(BaseModel):
    """Model for updating user profile."""

    name: Optional[str] = Field(None, description="User name", max_length=100)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional user metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Jane Smith",
                "metadata": {
                    "preferred_language": "es",
                    "study_preferences": {
                        "chunk_size": 1000
                    }
                }
            }
        }


class UserListResponse(BaseModel):
    """Response model for listing users (admin only)."""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")

    class Config:
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "auth0_id": "auth0|123456789",
                        "email": "student@example.com",
                        "name": "John Doe",
                        "role": "student",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-10T12:00:00Z",
                        "statistics": {
                            "total_uploads": 5,
                            "total_queries": 23,
                            "total_storage_bytes": 1024000,
                            "last_activity": "2025-01-10T12:00:00Z"
                        }
                    }
                ],
                "total": 1
            }
        }


class FileOwnershipInfo(BaseModel):
    """File ownership information for API responses."""

    filename: str = Field(..., description="File name")
    user_id: str = Field(..., description="Owner's MongoDB user ID")
    user_email: str = Field(..., description="Owner's email")
    is_public: bool = Field(..., description="Whether file is public")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    file_size: int = Field(..., description="File size in bytes")
    chunk_count: int = Field(..., description="Number of chunks generated")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "study_notes.pdf",
                "user_id": "507f1f77bcf86cd799439011",
                "user_email": "student@example.com",
                "is_public": False,
                "uploaded_at": "2025-01-10T10:00:00Z",
                "file_size": 204800,
                "chunk_count": 15
            }
        }
