"""Response models for API endpoints."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime


class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = Field(True, description="Whether the operation was successful")
    message: Optional[str] = Field(None, description="Optional message")


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = Field(False, description="Operation failed")
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class HealthResponse(BaseResponse):
    """Health check response."""
    status: str = Field("healthy", description="Service status")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class LLMResponse(BaseResponse):
    """LLM query response."""
    response: str = Field(..., description="LLM generated response")
    model_used: Optional[str] = Field(None, description="Model that generated the response")


class FileFeedbackStatsResponse(BaseModel):
    """File feedback statistics response model."""
    total_uses: int = Field(..., description="Total times file was used")
    total_likes: int = Field(..., description="Total likes received")
    total_dislikes: int = Field(..., description="Total dislikes received")
    last_used: Optional[str] = Field(None, description="Last time file was used (ISO format)")


class FileInfo(BaseModel):
    """File information model."""
    filename: str = Field(..., description="Name of the file")
    file_path: str = Field(..., description="Path to the file")
    file_type: str = Field(..., description="Type/description of the file")
    size_bytes: int = Field(..., description="File size in bytes")
    size_mb: float = Field(..., description="File size in megabytes")
    created_at: float = Field(..., description="Creation timestamp")
    modified_at: float = Field(..., description="Last modification timestamp")
    is_supported: bool = Field(..., description="Whether the file type is supported for processing")
    feedback_stats: Optional[FileFeedbackStatsResponse] = Field(None, description="Feedback statistics for this file")


class FileUploadResponse(BaseResponse):
    """File upload response."""
    filename: str = Field(..., description="Name of the uploaded file")
    file_path: str = Field(..., description="Path where the file was saved")
    processed_for_rag: bool = Field(..., description="Whether the file was successfully processed for RAG")
    file_info: Optional[FileInfo] = Field(None, description="File metadata")


class FileListResponse(BaseResponse):
    """File listing response."""
    files: List[FileInfo] = Field(..., description="List of uploaded files")
    total_files: int = Field(..., description="Total number of files")


class RelevantChunk(BaseModel):
    """Model for relevant document chunks."""
    content: str = Field(..., description="Content of the chunk")
    metadata: Dict[str, Any] = Field(..., description="Chunk metadata")
    distance: float = Field(..., description="Similarity distance (lower is more similar)")


class RAGResponse(BaseResponse):
    """RAG query response."""
    query: str = Field(..., description="Original query")
    context: str = Field(..., description="Retrieved context from documents")
    n_chunks_found: int = Field(..., description="Number of relevant chunks found")
    relevant_chunks: List[RelevantChunk] = Field(..., description="List of relevant document chunks")


class RAGLLMResponse(BaseResponse):
    """RAG query with LLM completion response."""
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="LLM generated answer based on context")
    context_used: str = Field(..., description="Context from documents that was used")
    n_chunks_found: int = Field(..., description="Number of relevant chunks found")
    sources: List[str] = Field(..., description="Source files that contributed to the answer")
    relevant_chunks: List[RelevantChunk] = Field(..., description="List of relevant document chunks")
    model_used: Optional[str] = Field(None, description="LLM model used for generation")
    conversation_id: str = Field(..., description="Conversation ID for this exchange")
    message_id: str = Field(..., description="Message ID for this assistant response")


class RAGStatsResponse(BaseResponse):
    """RAG system statistics response."""
    collection_name: str = Field(..., description="Name of the document collection")
    document_count: int = Field(..., description="Number of documents in the collection")
    embedding_model: str = Field(..., description="Embedding model being used")
    total_chunks: Optional[int] = Field(None, description="Total number of document chunks")


class APIInfoResponse(BaseResponse):
    """API information response."""
    title: str = Field(..., description="API title")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    endpoints: Dict[str, Any] = Field(..., description="Available endpoints and their descriptions")


class ConversationInfo(BaseModel):
    """Conversation information model."""
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_serialization_defaults_required=True
    )

    id: str = Field(..., description="Conversation ID", alias="_id")
    title: str = Field(..., description="Conversation title")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    message_count: int = Field(..., description="Number of messages in conversation")


class MessageInfo(BaseModel):
    """Message information model."""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(..., description="Message ID", alias="_id")
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    model_used: Optional[str] = Field(None, description="LLM model used (for assistant messages)")
    source_files: List[str] = Field(default_factory=list, description="Source files used for this response")
    feedback: Optional[str] = Field(None, description="User feedback (like or dislike)")


class ConversationListResponse(BaseResponse):
    """List of conversations response."""
    conversations: List[ConversationInfo] = Field(..., description="List of user's conversations")
    total: int = Field(..., description="Total number of conversations")


class ConversationDetailResponse(BaseResponse):
    """Detailed conversation with messages response."""
    conversation: ConversationInfo = Field(..., description="Conversation information")
    messages: List[MessageInfo] = Field(..., description="List of messages in conversation")
