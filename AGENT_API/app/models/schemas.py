"""Request and response models for Agent API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================
# Request Models
# ============================================

class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    user_id: str = Field(..., description="User ID (from main API)")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role (student/admin)")


class SearchDocumentsRequest(BaseModel):
    """Request to search documents."""
    query: str = Field(..., description="Search query")
    n_results: int = Field(default=5, ge=1, le=20, description="Number of results")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class ListFilesRequest(BaseModel):
    """Request to list files."""
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class GetFileInfoRequest(BaseModel):
    """Request to get file information."""
    filename: str = Field(..., description="Filename")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class ListConversationsRequest(BaseModel):
    """Request to list conversations."""
    limit: int = Field(default=10, ge=1, le=100, description="Max conversations to return")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")


class GetUserStatsRequest(BaseModel):
    """Request to get user statistics."""
    user_id: str = Field(..., description="User ID")


class DeleteFileRequest(BaseModel):
    """Request to delete a file."""
    filename: str = Field(..., description="Filename to delete")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class WebSearchRequest(BaseModel):
    """Request to perform web search."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=5, ge=1, le=10, description="Maximum number of results")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class ReadFileContentRequest(BaseModel):
    """Request to read full file content."""
    filename: str = Field(..., description="Filename to read")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


# ============================================
# Response Models
# ============================================

class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(default="", description="Response message")


class ToolExecutionResponse(BaseResponse):
    """Response from tool execution."""
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")


class SearchDocumentsResponse(BaseResponse):
    """Response from document search."""
    query: str = Field(..., description="Search query")
    n_chunks_found: int = Field(..., description="Number of chunks found")
    chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Relevant chunks")
    sources: List[str] = Field(default_factory=list, description="Source files")


class ListFilesResponse(BaseResponse):
    """Response from listing files."""
    file_count: int = Field(..., description="Number of files")
    files: List[Dict[str, Any]] = Field(default_factory=list, description="File metadata")


class GetFileInfoResponse(BaseResponse):
    """Response with file information."""
    filename: str = Field(..., description="Filename")
    size_bytes: int = Field(..., description="File size in bytes")
    uploaded_at: str = Field(..., description="Upload timestamp")
    is_public: bool = Field(..., description="Whether file is public")
    chunk_count: int = Field(default=0, description="Number of chunks in ChromaDB")
    total_uses: int = Field(default=0, description="Total times used")
    total_views: int = Field(default=0, description="Total views")


class ListConversationsResponse(BaseResponse):
    """Response from listing conversations."""
    conversation_count: int = Field(..., description="Number of conversations")
    conversations: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation list")


class GetUserStatsResponse(BaseResponse):
    """Response with user statistics."""
    upload_count: int = Field(default=0, description="Number of files uploaded")
    query_count: int = Field(default=0, description="Number of queries made")
    storage_bytes: int = Field(default=0, description="Storage used in bytes")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")


class DeleteFileResponse(BaseResponse):
    """Response from file deletion."""
    filename: str = Field(..., description="Deleted filename")


class WebSearchResponse(BaseResponse):
    """Response from web search."""
    query: str = Field(..., description="Search query")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Search results")
    result_count: int = Field(..., description="Number of results found")


class ReadFileContentResponse(BaseResponse):
    """Response with file content."""
    filename: str = Field(..., description="Filename")
    content: str = Field(..., description="Full text content of file")
    file_size: int = Field(..., description="File size in bytes")
    chunk_count: int = Field(default=0, description="Number of chunks in ChromaDB")


class ToolListResponse(BaseResponse):
    """Response with list of available tools."""
    tools: List[Dict[str, Any]] = Field(default_factory=list, description="Available tools")
    tool_count: int = Field(..., description="Number of tools")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status")
    message: str = Field(..., description="Health message")
    version: str = Field(..., description="API version")
