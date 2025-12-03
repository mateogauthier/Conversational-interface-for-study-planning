"""Agent tool execution endpoints."""

import logging
from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import (
    SearchDocumentsRequest, SearchDocumentsResponse,
    ListFilesRequest, ListFilesResponse,
    GetFileInfoRequest, GetFileInfoResponse,
    ListConversationsRequest, ListConversationsResponse,
    GetUserStatsRequest, GetUserStatsResponse,
    DeleteFileRequest, DeleteFileResponse,
    WebSearchRequest, WebSearchResponse,
    ReadFileContentRequest, ReadFileContentResponse,
    ToolListResponse
)
from app.services.tool_services import agent_tool_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/search_documents", response_model=SearchDocumentsResponse)
async def search_documents(request: SearchDocumentsRequest):
    """Search documents using semantic search."""
    try:
        result = await agent_tool_service.search_documents(
            query=request.query,
            n_results=request.n_results,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return SearchDocumentsResponse(
            success=True,
            message="Search completed successfully",
            **result
        )

    except Exception as e:
        logger.error(f"Search documents error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list_files", response_model=ListFilesResponse)
async def list_files(request: ListFilesRequest):
    """List files accessible to the user."""
    try:
        result = await agent_tool_service.list_files(
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return ListFilesResponse(
            success=True,
            message="Files retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"List files error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_file_info", response_model=GetFileInfoResponse)
async def get_file_info(request: GetFileInfoRequest):
    """Get detailed information about a file."""
    try:
        result = await agent_tool_service.get_file_info(
            filename=request.filename,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return GetFileInfoResponse(
            success=True,
            message="File info retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"Get file info error: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/list_conversations", response_model=ListConversationsResponse)
async def list_conversations(request: ListConversationsRequest):
    """List user's conversations."""
    try:
        result = await agent_tool_service.list_conversations(
            limit=request.limit,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id
        )

        return ListConversationsResponse(
            success=True,
            message="Conversations retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"List conversations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_user_stats", response_model=GetUserStatsResponse)
async def get_user_stats(request: GetUserStatsRequest):
    """Get user statistics."""
    try:
        result = await agent_tool_service.get_user_stats(
            user_id=request.user_id
        )

        return GetUserStatsResponse(
            success=True,
            message="User stats retrieved successfully",
            **result
        )

    except Exception as e:
        logger.error(f"Get user stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/delete_file", response_model=DeleteFileResponse)
async def delete_file(request: DeleteFileRequest):
    """Delete a file (requires confirmation in agent flow)."""
    try:
        result = await agent_tool_service.delete_file(
            filename=request.filename,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return DeleteFileResponse(
            success=True,
            message=result["message"],
            filename=result["filename"]
        )

    except Exception as e:
        logger.error(f"Delete file error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web_search", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest):
    """Perform web search using DuckDuckGo."""
    try:
        result = await agent_tool_service.web_search(
            query=request.query,
            max_results=request.max_results,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return WebSearchResponse(
            success=True,
            message="Web search completed successfully",
            **result
        )

    except Exception as e:
        error_msg = str(e)
        # Return 503 for rate limiting, 500 for other errors
        if "rate limiting" in error_msg.lower() or "ratelimit" in error_msg.lower():
            logger.warning(f"Web search rate limited: {e}")
            raise HTTPException(status_code=503, detail=error_msg)
        else:
            logger.error(f"Web search error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=error_msg)


@router.post("/read_file_content", response_model=ReadFileContentResponse)
async def read_file_content(request: ReadFileContentRequest):
    """Read full content of a specific file."""
    try:
        result = await agent_tool_service.read_file_content(
            filename=request.filename,
            user_id=request.user_id,
            user_auth0_id=request.user_auth0_id,
            user_role=request.user_role
        )

        return ReadFileContentResponse(
            success=True,
            message=f"File content retrieved successfully",
            **result
        )

    except ValueError as e:
        logger.error(f"Read file content error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Read file content error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list", response_model=ToolListResponse)
async def list_available_tools():
    """List all available agent tools."""
    tools = [
        {
            "name": "search_documents",
            "description": "Search through documents using semantic search",
            "endpoint": "/tools/search_documents",
            "method": "POST",
            "parameters": ["query", "n_results", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "list_files",
            "description": "List all files accessible to the user",
            "endpoint": "/tools/list_files",
            "method": "POST",
            "parameters": ["user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "get_file_info",
            "description": "Get detailed information about a specific file",
            "endpoint": "/tools/get_file_info",
            "method": "POST",
            "parameters": ["filename", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "list_conversations",
            "description": "List user's conversation history",
            "endpoint": "/tools/list_conversations",
            "method": "POST",
            "parameters": ["limit", "user_id", "user_auth0_id"]
        },
        {
            "name": "get_user_stats",
            "description": "Get user's usage statistics",
            "endpoint": "/tools/get_user_stats",
            "method": "POST",
            "parameters": ["user_id"]
        },
        {
            "name": "delete_file",
            "description": "Delete a file (requires confirmation)",
            "endpoint": "/tools/delete_file",
            "method": "POST",
            "parameters": ["filename", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo",
            "endpoint": "/tools/web_search",
            "method": "POST",
            "parameters": ["query", "max_results", "user_id", "user_auth0_id", "user_role"]
        },
        {
            "name": "read_file_content",
            "description": "Read full text content of a specific file",
            "endpoint": "/tools/read_file_content",
            "method": "POST",
            "parameters": ["filename", "user_id", "user_auth0_id", "user_role"]
        }
    ]

    return ToolListResponse(
        success=True,
        message="Available tools retrieved",
        tools=tools,
        tool_count=len(tools)
    )
