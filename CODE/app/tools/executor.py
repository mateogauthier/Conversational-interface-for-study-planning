"""Tool executor with permission checks and service integration."""

import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime

from app.agents.base import ToolCall, ToolSafety
from app.tools.registry import TOOL_REGISTRY, get_tool
from app.db.models import UserInDB
from app.core.exceptions import ForbiddenHTTPException, NotFoundHTTPException

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    pass


class ToolExecutor:
    """Executes tools with permission checks and service integration."""

    def __init__(
        self,
        file_service=None,
        rag_service=None,
        conversation_service=None,
        user_service=None,
    ):
        """Initialize tool executor with service dependencies.

        Args:
            file_service: FileService instance
            rag_service: RAGService instance
            conversation_service: ConversationService instance
            user_service: UserService instance
        """
        self.file_service = file_service
        self.rag_service = rag_service
        self.conversation_service = conversation_service
        self.user_service = user_service

        # Register executor functions
        self._register_executors()

    def _register_executors(self):
        """Register executor functions for each tool."""
        TOOL_REGISTRY["list_files"]["executor"] = self._execute_list_files
        TOOL_REGISTRY["search_documents"]["executor"] = self._execute_search_documents
        TOOL_REGISTRY["get_file_info"]["executor"] = self._execute_get_file_info
        TOOL_REGISTRY["list_conversations"]["executor"] = self._execute_list_conversations
        TOOL_REGISTRY["get_conversation"]["executor"] = self._execute_get_conversation
        TOOL_REGISTRY["get_user_stats"]["executor"] = self._execute_get_user_stats
        TOOL_REGISTRY["delete_file"]["executor"] = self._execute_delete_file
        TOOL_REGISTRY["delete_conversation"]["executor"] = self._execute_delete_conversation

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user: UserInDB,
    ) -> ToolCall:
        """Execute a tool with permission checks.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            user: Authenticated user

        Returns:
            ToolCall with execution result

        Raises:
            NotFoundException: If tool not found
            ForbiddenException: If user doesn't have permission
            ToolExecutionError: If execution fails
        """
        start_time = time.time()

        # Get tool definition
        tool = get_tool(tool_name)
        if not tool:
            raise NotFoundHTTPException(f"Tool '{tool_name}' not found")

        # Check role permission
        if tool.required_role and user.role != tool.required_role:
            raise ForbiddenHTTPException(
                f"Tool '{tool_name}' requires role '{tool.required_role}'"
            )

        # Get executor function
        executor = TOOL_REGISTRY[tool_name]["executor"]
        if not executor:
            raise ToolExecutionError(f"No executor registered for tool '{tool_name}'")

        # Execute tool
        try:
            result = await executor(parameters, user)
            execution_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Tool executed successfully: {tool_name} by user {user.auth0_id} "
                f"in {execution_time_ms}ms"
            )

            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                result=result,
                execution_time_ms=execution_time_ms
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            logger.error(
                f"Tool execution failed: {tool_name} by user {user.auth0_id} - {error_msg}"
            )

            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                error=error_msg,
                execution_time_ms=execution_time_ms
            )

    # Tool executor functions

    async def _execute_list_files(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """List all files accessible to the user."""
        files = await self.file_service.list_files(user)

        return {
            "file_count": len(files),
            "files": [
                {
                    "filename": f.get("filename"),
                    "size_bytes": f.get("size_bytes"),
                    "uploaded_at": f.get("uploaded_at"),
                    "is_public": f.get("is_public", False),
                    "chunk_count": f.get("chunk_count", 0)
                }
                for f in files
            ]
        }

    async def _execute_search_documents(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """Search documents using semantic search."""
        query = parameters.get("query")
        n_results = parameters.get("n_results", 5)

        if not query:
            raise ToolExecutionError("Parameter 'query' is required")

        # Use RAG service for search
        search_results = await self.rag_service.search_documents_async(
            query=query,
            user=user,
            n_results=n_results
        )

        # Extract relevant information
        chunks = []
        for chunk in search_results.get("relevant_chunks", []):
            chunks.append({
                "content": chunk.page_content[:200] + "..." if len(chunk.page_content) > 200 else chunk.page_content,
                "source": chunk.metadata.get("file_name", "Unknown"),
                "chunk_index": chunk.metadata.get("chunk_index", 0)
            })

        return {
            "query": query,
            "n_chunks_found": search_results.get("n_chunks_found", 0),
            "chunks": chunks,
            "sources": list(set([chunk.metadata.get("file_name", "Unknown")
                               for chunk in search_results.get("relevant_chunks", [])]))
        }

    async def _execute_get_file_info(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """Get information about a specific file."""
        filename = parameters.get("filename")

        if not filename:
            raise ToolExecutionError("Parameter 'filename' is required")

        # Get file metadata
        file_metadata = await self.file_service.get_file_metadata(filename, user)

        if not file_metadata:
            raise NotFoundHTTPException(f"File '{filename}' not found or not accessible")

        return {
            "filename": file_metadata.get("filename"),
            "size_bytes": file_metadata.get("size_bytes"),
            "uploaded_at": file_metadata.get("uploaded_at"),
            "is_public": file_metadata.get("is_public", False),
            "chunk_count": file_metadata.get("chunk_count", 0),
            "total_uses": file_metadata.get("total_uses", 0),
            "total_views": file_metadata.get("total_views", 0)
        }

    async def _execute_list_conversations(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """List user's conversations."""
        limit = parameters.get("limit", 10)

        conversations = await self.conversation_service.get_user_conversations(
            auth0_id=user.auth0_id,
            limit=limit,
            offset=0
        )

        return {
            "conversation_count": len(conversations),
            "conversations": [
                {
                    "conversation_id": str(conv.get("_id")) if conv.get("_id") else conv.get("id"),
                    "title": conv.get("title"),
                    "message_count": conv.get("message_count", 0),
                    "updated_at": conv.get("updated_at")
                }
                for conv in conversations
            ]
        }

    async def _execute_get_conversation(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """Get full conversation with messages."""
        conversation_id = parameters.get("conversation_id")

        if not conversation_id:
            raise ToolExecutionError("Parameter 'conversation_id' is required")

        conversation = await self.conversation_service.get_conversation(
            conversation_id=conversation_id,
            user=user
        )

        if not conversation:
            raise NotFoundException(f"Conversation '{conversation_id}' not found")

        return {
            "conversation_id": conversation_id,
            "title": conversation.get("title"),
            "message_count": len(conversation.get("messages", [])),
            "messages": [
                {
                    "role": msg.get("role"),
                    "content": msg.get("content")[:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content"),
                    "timestamp": msg.get("timestamp")
                }
                for msg in conversation.get("messages", [])
            ]
        }

    async def _execute_get_user_stats(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """Get user's statistics."""
        stats = await self.user_service.get_user_stats(str(user.id))

        return {
            "upload_count": stats.get("upload_count", 0),
            "query_count": stats.get("query_count", 0),
            "storage_bytes": stats.get("storage_bytes", 0),
            "last_activity": stats.get("last_activity")
        }

    async def _execute_delete_file(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """Delete a file (requires confirmation)."""
        filename = parameters.get("filename")

        if not filename:
            raise ToolExecutionError("Parameter 'filename' is required")

        # Delete file
        success = await self.file_service.delete_file(filename, user)

        if not success:
            raise ToolExecutionError(f"Failed to delete file '{filename}'")

        return {
            "success": True,
            "filename": filename,
            "message": f"File '{filename}' deleted successfully"
        }

    async def _execute_delete_conversation(
        self,
        parameters: Dict[str, Any],
        user: UserInDB
    ) -> Dict[str, Any]:
        """Delete a conversation (requires confirmation)."""
        conversation_id = parameters.get("conversation_id")

        if not conversation_id:
            raise ToolExecutionError("Parameter 'conversation_id' is required")

        # Delete conversation
        success = await self.conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user=user
        )

        if not success:
            raise ToolExecutionError(f"Failed to delete conversation '{conversation_id}'")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "message": f"Conversation deleted successfully"
        }
