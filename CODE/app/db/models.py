"""Pydantic models for MongoDB documents."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, ConfigDict
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom type for MongoDB ObjectId to work with Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, info):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserStatistics(BaseModel):
    """User statistics embedded model."""

    total_uploads: int = 0
    total_queries: int = 0
    total_storage_bytes: int = 0
    last_activity: Optional[datetime] = None

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class UserInDB(BaseModel):
    """User document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    auth0_id: str = Field(..., description="Auth0 user ID (sub claim)")
    email: str
    name: Optional[str] = None
    role: str = Field(..., description="User role: admin or student")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    statistics: UserStatistics = Field(default_factory=UserStatistics)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Flexible field for future extensions")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class FileMetadataInDB(BaseModel):
    """File metadata document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    user_id: str = Field(..., description="MongoDB user ID (ObjectId as string)")
    auth0_id: str = Field(..., description="Auth0 user ID for quick lookups")
    is_public: bool = Field(..., description="True if file is public (admin), False if private (student)")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(..., description="File extension")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(default=False, description="Whether file has been processed by RAG")
    chunk_count: int = Field(default=0, description="Number of chunks generated")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class ConversationInDB(BaseModel):
    """Conversation document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="MongoDB user ID (ObjectId as string)")
    auth0_id: str = Field(..., description="Auth0 user ID for quick lookups")
    title: str = Field(..., description="Auto-generated from first message")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = Field(default=0, description="Total number of messages in conversation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata (model, language, etc.)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )


class MessageInDB(BaseModel):
    """Message document model for MongoDB."""

    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    conversation_id: str = Field(..., description="Conversation ID (ObjectId as string)")
    role: Literal["user", "assistant"] = Field(..., description="Message sender role")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    model_used: Optional[str] = Field(None, description="LLM model used for assistant messages")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Optional metadata (sources, token count, etc.)")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
    )
