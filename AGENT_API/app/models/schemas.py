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


# ============================================
# University/Academic Tool Request Models
# ============================================

class GetUniversitySubjectsRequest(BaseModel):
    """Request to get all university subjects."""
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class GetDegreeCurriculumRequest(BaseModel):
    """Request to get suggested curriculum for a degree."""
    degree_id: str = Field(..., description="Degree ID (e.g., 'ingenieria-sistemas')")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class GetDegreeSubjectsRequest(BaseModel):
    """Request to get subjects and prerequisites for a degree."""
    degree_id: str = Field(..., description="Degree ID")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class UploadStudentSchoolingRequest(BaseModel):
    """Request to upload/update student schooling records."""
    student_id: str = Field(..., description="Student ID")
    schooling_data: Dict[str, Any] = Field(..., description="Schooling data (subjects, grades, dates)")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class GetStudentDegreeRequest(BaseModel):
    """Request to get student's enrolled degree."""
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class GetStudentDegreeResponse(BaseModel):
    """Response with student's degree ID."""
    success: bool
    message: str
    degree_id: str = Field(..., description="Degree ID the student is enrolled in")


class GetStudentSchoolingRequest(BaseModel):
    """Request to get student's schooling records."""
    student_id: str = Field(..., description="Student ID")
    degree_id: str = Field(..., description="Degree ID")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class GetStudentPlanRequest(BaseModel):
    """Request to get student's career plan."""
    student_id: str = Field(..., description="Student ID")
    degree_id: str = Field(..., description="Degree ID")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


class UpdateStudentPlanRequest(BaseModel):
    """Request to modify student's career plan."""
    student_id: str = Field(..., description="Student ID")
    degree_id: str = Field(..., description="Degree ID")
    plan_data: Dict[str, Any] = Field(..., description="Updated plan data")
    user_id: str = Field(..., description="User ID")
    user_auth0_id: str = Field(..., description="User Auth0 ID")
    user_role: str = Field(..., description="User role")


# ============================================
# University/Academic Tool Response Models
# ============================================

class GetUniversitySubjectsResponse(BaseResponse):
    """Response with all university subjects."""
    subjects: List[Dict[str, Any]] = Field(default_factory=list, description="List of all subjects")
    subject_count: int = Field(..., description="Total number of subjects")


class GetDegreeCurriculumResponse(BaseResponse):
    """Response with degree curriculum."""
    degree_id: str = Field(..., description="Degree ID")
    degree_name: str = Field(..., description="Degree name")
    curriculum: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested curriculum by semester")


class GetDegreeSubjectsResponse(BaseResponse):
    """Response with degree subjects and prerequisites."""
    degree_id: str = Field(..., description="Degree ID")
    degree_name: str = Field(..., description="Degree name")
    subjects: List[Dict[str, Any]] = Field(default_factory=list, description="Subjects with prerequisites")
    subject_count: int = Field(..., description="Number of subjects in degree")


class UploadStudentSchoolingResponse(BaseResponse):
    """Response after uploading student schooling."""
    student_id: str = Field(..., description="Student ID")
    records_updated: int = Field(..., description="Number of records updated")


class GetStudentSchoolingResponse(BaseResponse):
    """Response with student schooling records."""
    student_id: str = Field(..., description="Student ID")
    degree_id: str = Field(..., description="Degree ID")
    schooling_records: List[Dict[str, Any]] = Field(default_factory=list, description="Student's completed subjects")
    in_progress_subjects: List[Dict[str, Any]] = Field(default_factory=list, description="Student's in-progress subjects")
    total_credits: int = Field(default=0, description="Total credits earned")
    gpa: float = Field(default=0.0, description="Grade point average")


class GetStudentPlanResponse(BaseResponse):
    """Response with student's career plan."""
    student_id: str = Field(..., description="Student ID")
    degree_id: str = Field(..., description="Degree ID")
    plan: List[Dict[str, Any]] = Field(default_factory=list, description="Planned subjects by semester")
    total_semesters: int = Field(..., description="Total semesters in plan")


class UpdateStudentPlanResponse(BaseResponse):
    """Response after updating student plan."""
    student_id: str = Field(..., description="Student ID")
    degree_id: str = Field(..., description="Degree ID")
    plan_updated: bool = Field(..., description="Whether plan was successfully updated")
