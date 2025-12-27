"""API-based agent provider for external agent service integration.

This is a stub implementation that will be completed when the external
agent API is ready. It provides the same interface as LocalAgentProvider
but delegates execution to an external service.
"""

import logging
import httpx
from typing import List, Optional, Dict, Any

from app.agents.base import (
    AgentProvider,
    AgentResponse,
    AgentStep,
    ToolCall,
    PendingConfirmation,
    Tool
)
from app.db.models import UserInDB

logger = logging.getLogger(__name__)


class APIAgentProvider(AgentProvider):
    """API-based agent provider (stub for future implementation).

    This provider will communicate with an external agent API service.
    When the API is ready, implement the HTTP calls to the external service.

    Configuration (add to .env):
        AGENT_API_URL=https://api.example.com/agent
        AGENT_API_KEY=your_api_key_here
        AGENT_API_TIMEOUT=30
    """

    def __init__(
        self,
        api_url: str,
        api_key: str,
        timeout: int = 30,
        fallback_provider: Optional[AgentProvider] = None
    ):
        """Initialize API agent provider.

        Args:
            api_url: Base URL of the external agent API
            api_key: API key for authentication
            timeout: Request timeout in seconds
            fallback_provider: Optional fallback provider (e.g., LocalAgentProvider)
        """
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.fallback_provider = fallback_provider

        # HTTP client for API calls
        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=timeout
        )

    async def execute_query(
        self,
        query: str,
        user: UserInDB,
        conversation_id: Optional[str] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Execute a query using the external agent API.

        Args:
            query: User's query text
            user: Authenticated user object
            conversation_id: Optional conversation ID to continue
            auto_approve_tools: Whether to auto-approve all tool executions
            **kwargs: Additional parameters

        Returns:
            AgentResponse from the external API
        """
        logger.info(f"API agent executing query for user {user.auth0_id}: {query}")

        try:
            # TODO: Implement actual API call when external service is ready
            #
            # Example implementation:
            # response = await self.client.post(
            #     "/query",
            #     json={
            #         "query": query,
            #         "user_id": user.auth0_id,
            #         "conversation_id": conversation_id,
            #         "auto_approve_tools": auto_approve_tools,
            #         **kwargs
            #     }
            # )
            #
            # if response.status_code == 200:
            #     data = response.json()
            #     return self._map_api_response(data)
            # else:
            #     raise Exception(f"API error: {response.status_code}")

            # STUB: For now, return a placeholder or use fallback
            logger.warning("API agent provider is not yet implemented, using fallback")

            if self.fallback_provider:
                return await self.fallback_provider.execute_query(
                    query=query,
                    user=user,
                    conversation_id=conversation_id,
                    auto_approve_tools=auto_approve_tools,
                    **kwargs
                )
            else:
                return AgentResponse(
                    answer="External agent API not yet configured. Please use local agent provider.",
                    agent_steps=[],
                    tools_executed=[],
                    is_complete=True
                )

        except Exception as e:
            logger.error(f"API agent error: {e}")

            # Fallback to local provider if available
            if self.fallback_provider:
                logger.info("Falling back to local agent provider")
                return await self.fallback_provider.execute_query(
                    query=query,
                    user=user,
                    conversation_id=conversation_id,
                    auto_approve_tools=auto_approve_tools,
                    **kwargs
                )

            # Otherwise return error
            return AgentResponse(
                answer=f"Agent service temporarily unavailable: {str(e)}",
                agent_steps=[],
                tools_executed=[],
                is_complete=True
            )

    async def confirm_action(
        self,
        confirmation_id: str,
        approved: bool,
        user: UserInDB,
    ) -> AgentResponse:
        """Confirm or deny a pending tool execution.

        Args:
            confirmation_id: ID of the pending confirmation
            approved: Whether user approved the action
            user: Authenticated user object

        Returns:
            AgentResponse with updated execution status
        """
        logger.info(f"API agent confirmation: {confirmation_id}, approved={approved}")

        try:
            # TODO: Implement actual API call
            #
            # response = await self.client.post(
            #     "/confirm",
            #     json={
            #         "confirmation_id": confirmation_id,
            #         "approved": approved,
            #         "user_id": user.auth0_id
            #     }
            # )
            #
            # if response.status_code == 200:
            #     data = response.json()
            #     return self._map_api_response(data)

            # STUB: Use fallback
            if self.fallback_provider:
                return await self.fallback_provider.confirm_action(
                    confirmation_id=confirmation_id,
                    approved=approved,
                    user=user
                )

            return AgentResponse(
                answer="External agent API not yet configured.",
                is_complete=True
            )

        except Exception as e:
            logger.error(f"API confirmation error: {e}")

            if self.fallback_provider:
                return await self.fallback_provider.confirm_action(
                    confirmation_id=confirmation_id,
                    approved=approved,
                    user=user
                )

            return AgentResponse(
                answer=f"Confirmation failed: {str(e)}",
                is_complete=True
            )

    async def get_available_tools(self, user: UserInDB) -> List[Tool]:
        """Get list of tools available to the user.

        Args:
            user: Authenticated user object

        Returns:
            List of Tool definitions
        """
        try:
            # TODO: Implement actual API call
            #
            # response = await self.client.get(
            #     "/tools",
            #     params={"user_id": user.auth0_id}
            # )
            #
            # if response.status_code == 200:
            #     tools_data = response.json()
            #     return [Tool(**tool) for tool in tools_data]

            # STUB: Use fallback
            if self.fallback_provider:
                return await self.fallback_provider.get_available_tools(user)

            return []

        except Exception as e:
            logger.error(f"API get tools error: {e}")

            if self.fallback_provider:
                return await self.fallback_provider.get_available_tools(user)

            return []

    async def is_available(self) -> bool:
        """Check if the API agent provider is available.

        Returns:
            True if API is responding, False otherwise
        """
        try:
            # TODO: Implement health check
            #
            # response = await self.client.get("/health")
            # return response.status_code == 200

            # STUB: Check if fallback is available
            if self.fallback_provider:
                return await self.fallback_provider.is_available()

            return False

        except Exception as e:
            logger.error(f"API health check failed: {e}")

            # Check fallback availability
            if self.fallback_provider:
                return await self.fallback_provider.is_available()

            return False

    async def close(self):
        """Close HTTP client connections."""
        await self.client.aclose()

    # Helper methods for when API is implemented

    def _map_api_response(self, data: Dict[str, Any]) -> AgentResponse:
        """Map external API response to internal AgentResponse format.

        This method will need to be implemented based on the actual
        external API response schema.

        Args:
            data: Response data from external API

        Returns:
            Mapped AgentResponse object
        """
        # TODO: Implement mapping based on actual API schema
        #
        # Example:
        # return AgentResponse(
        #     answer=data.get("answer", ""),
        #     agent_steps=[
        #         AgentStep(**step) for step in data.get("steps", [])
        #     ],
        #     tools_executed=data.get("tools_executed", []),
        #     pending_confirmations=[
        #         PendingConfirmation(**conf) for conf in data.get("pending_confirmations", [])
        #     ],
        #     ...
        # )

        return AgentResponse(
            answer=data.get("answer", ""),
            agent_steps=[],
            tools_executed=[],
            is_complete=True
        )


# Factory function for creating agent provider based on configuration
def create_agent_provider(
    provider_type: str,
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> AgentProvider:
    """Create agent provider based on configuration.

    Args:
        provider_type: "react", "instructor", or "api"
        api_url: Agent API URL (for tool execution) or External API URL (for API provider)
        api_key: External API key (for API provider only)
        **kwargs: Additional configuration

    Returns:
        AgentProvider instance

    Provider types:
        - "react": ReAct-based LangGraph agent (simple, fast)
        - "instructor": Instructor-enhanced ReAct with structured reasoning (advanced)
        - "api": External agent API (stub implementation)

    Note:
        Legacy providers ("local", "langgraph") have been removed.
    """
    from app.agents.react_langgraph_provider import ReActLangGraphProvider
    from app.agents.instructor_react_provider import InstructorReActProvider
    from app.tools.http_executor import HTTPToolExecutor

    if provider_type == "react":
        # ReAct agent uses HTTPToolExecutor for agent API calls
        tool_executor = HTTPToolExecutor(agent_api_url=api_url)
        return ReActLangGraphProvider(
            tool_executor=tool_executor,
            **kwargs
        )

    elif provider_type == "instructor":
        # Instructor-enhanced ReAct agent with structured iterative reasoning
        tool_executor = HTTPToolExecutor(agent_api_url=api_url)
        return InstructorReActProvider(
            tool_executor=tool_executor,
            **kwargs
        )

    elif provider_type == "api":
        # External agent API (stub implementation)
        # No fallback to local since legacy providers removed
        return APIAgentProvider(
            api_url=api_url or "http://localhost:8080",
            api_key=api_key or "not_configured",
            fallback_provider=None,
            **kwargs
        )

    # Legacy provider types - show helpful error message
    elif provider_type in ["local", "langgraph"]:
        raise ValueError(
            f"Legacy agent provider '{provider_type}' has been removed. "
            f"Use 'react' for the ReAct-based LangGraph agent instead."
        )

    else:
        raise ValueError(f"Unknown agent provider type: {provider_type}. Use 'react', 'instructor', or 'api'")
