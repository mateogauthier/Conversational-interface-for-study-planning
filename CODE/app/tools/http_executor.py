"""HTTP-based tool executor that calls the Agent API."""

import logging
import time
import httpx
from typing import Any, Dict

from app.agents.base import ToolCall
from app.db.models import UserInDB
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HTTPToolExecutor:
    """Executes tools by calling the Agent API via HTTP."""

    def __init__(self, agent_api_url: str = None):
        """Initialize HTTP tool executor.

        Args:
            agent_api_url: Base URL for Agent API (default: http://agent-api:8002)
        """
        self.agent_api_url = agent_api_url or "http://agent-api:8002"
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"HTTPToolExecutor initialized with Agent API: {self.agent_api_url}")

    async def execute(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user: UserInDB,
    ) -> ToolCall:
        """Execute a tool via Agent API.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            user: Authenticated user

        Returns:
            ToolCall with execution result
        """
        start_time = time.time()

        # Map tool names to Agent API endpoints
        endpoint_map = {
            "search_documents": "/tools/search_documents",
            "list_files": "/tools/list_files",
            "get_file_info": "/tools/get_file_info",
            "list_conversations": "/tools/list_conversations",
            "get_conversation": "/tools/get_conversation",
            "get_user_stats": "/tools/get_user_stats",
            "delete_file": "/tools/delete_file",
            "delete_conversation": "/tools/delete_conversation",
            "web_search": "/tools/web_search",
            "read_file_content": "/tools/read_file_content",
            # University/Academic endpoints
            "get_university_subjects": "/tools/get_university_subjects",
            "get_degree_curriculum": "/tools/get_degree_curriculum",
            "get_degree_subjects": "/tools/get_degree_subjects",
            "upload_student_schooling": "/tools/upload_student_schooling",
            "get_student_schooling": "/tools/get_student_schooling",
            "get_student_plan": "/tools/get_student_plan",
            "update_student_plan": "/tools/update_student_plan",
        }

        endpoint = endpoint_map.get(tool_name)
        if not endpoint:
            error_msg = f"Unknown tool: {tool_name}"
            logger.error(error_msg)
            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                error=error_msg,
                execution_time_ms=0
            )

        # Prepare request payload
        payload = {
            **parameters,
            "user_id": str(user.id),
            "user_auth0_id": user.auth0_id,
            "user_role": user.role
        }

        try:
            # Call Agent API
            url = f"{self.agent_api_url}{endpoint}"
            logger.info(f"Calling Agent API: POST {url}")

            response = await self.client.post(url, json=payload)
            execution_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                result = response.json()
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
            else:
                error_msg = f"Agent API error: {response.status_code} - {response.text}"
                logger.error(f"Tool execution failed: {tool_name} - {error_msg}")

                return ToolCall(
                    tool_name=tool_name,
                    parameters=parameters,
                    error=error_msg,
                    execution_time_ms=execution_time_ms
                )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Failed to call Agent API: {str(e)}"
            logger.error(f"Tool execution failed: {tool_name} - {error_msg}")

            return ToolCall(
                tool_name=tool_name,
                parameters=parameters,
                error=error_msg,
                execution_time_ms=execution_time_ms
            )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
