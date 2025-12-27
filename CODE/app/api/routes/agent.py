"""Agent API routes with authentication."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    get_current_user,
    get_app_settings
)
from app.db.models import UserInDB
from app.core.config import Settings
from app.models.requests import AgentQueryRequest, AgentConfirmRequest
from app.models.responses import (
    AgentQueryResponse,
    AgentToolsListResponse,
    AgentStepResponse,
    AgentToolCallResponse,
    PendingConfirmationResponse
)
from app.agents.base import AgentProvider, AgentResponse
from app.core.exceptions import NotFoundHTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])

# Global agent provider instance (initialized in main.py startup)
_agent_provider: AgentProvider = None


def set_agent_provider(provider: AgentProvider):
    """Set the global agent provider instance."""
    global _agent_provider
    _agent_provider = provider


def get_agent_provider() -> AgentProvider:
    """Get the global agent provider instance."""
    if _agent_provider is None:
        raise HTTPException(
            status_code=503,
            detail="Agent provider not initialized"
        )
    return _agent_provider


@router.post("/query", response_model=AgentQueryResponse)
async def agent_query(
    request: AgentQueryRequest,
    current_user: UserInDB = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings)
):
    """
    Execute a query using the agent with tool execution capabilities.

    The agent will:
    1. Analyze the query to determine if tools are needed
    2. Execute safe tools automatically (file listing, search, stats)
    3. Request confirmation for write operations (delete file, etc.)
    4. Generate a final answer using tool results

    - Students: Can access their files + public files
    - Admins: Can access public files only
    """
    try:
        # Check if agent tools are enabled
        if not settings.enable_agent_tools or not request.enable_agent:
            # Fall back to standard RAG (could delegate to rag.py endpoint)
            raise HTTPException(
                status_code=400,
                detail="Agent tools are disabled. Use /rag/query endpoint instead."
            )

        # Get agent provider
        agent_provider = get_agent_provider()

        # Check availability
        if not await agent_provider.is_available():
            raise HTTPException(
                status_code=503,
                detail="Agent service temporarily unavailable"
            )

        logger.info(f"Agent query from user {current_user.auth0_id}: {request.prompt}")

        # Execute agent query
        agent_response: AgentResponse = await agent_provider.execute_query(
            query=request.prompt,
            user=current_user,
            conversation_id=request.conversation_id,
            auto_approve_tools=request.auto_approve_tools,
            # Pass through RAG parameters
            n_results=request.n_results,
            model=request.model,
            language=request.language,
            instructions=request.instructions,
            enable_artifacts=request.enable_artifacts,
            # Pass through question/answer parameters
            question_id=request.question_id,
            answer_to_question=request.answer_to_question,
            original_query=request.prompt
        )

        # Convert to API response model
        return _map_agent_response(agent_response, request.prompt)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent query error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent query failed: {str(e)}"
        )


@router.post("/confirm", response_model=AgentQueryResponse)
async def confirm_action(
    request: AgentConfirmRequest,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Confirm or deny a pending agent action.

    Use this endpoint to respond to pending confirmations from agent tool executions.
    """
    try:
        agent_provider = get_agent_provider()

        logger.info(
            f"Confirmation {request.confirmation_id}: "
            f"approved={request.approved} by {current_user.auth0_id}"
        )

        # Process confirmation
        agent_response: AgentResponse = await agent_provider.confirm_action(
            confirmation_id=request.confirmation_id,
            approved=request.approved,
            user=current_user
        )

        # Convert to API response
        return _map_agent_response(agent_response, "confirmation")

    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Confirmation processing failed: {str(e)}"
        )


@router.get("/tools", response_model=AgentToolsListResponse)
async def get_available_tools(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Get list of tools available to the current user.

    Returns tools the user can execute based on their role and permissions.
    """
    try:
        agent_provider = get_agent_provider()

        tools = await agent_provider.get_available_tools(current_user)

        return AgentToolsListResponse(
            message="Available tools retrieved successfully",
            tools=[tool.model_dump() for tool in tools],
            tool_count=len(tools)
        )

    except Exception as e:
        logger.error(f"Get tools error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tools: {str(e)}"
        )


@router.get("/health")
async def health_check(
    current_user: UserInDB = Depends(get_current_user)
):
    """Check if agent service is available."""
    try:
        agent_provider = get_agent_provider()
        is_available = await agent_provider.is_available()

        if is_available:
            return {
                "status": "healthy",
                "message": "Agent service is available"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Agent service is not available"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Agent service health check failed"
        )


# Helper functions

def _map_agent_response(
    agent_response: AgentResponse,
    original_query: str
) -> AgentQueryResponse:
    """Map AgentResponse to AgentQueryResponse API model."""
    return AgentQueryResponse(
        message="Agent query completed successfully" if agent_response.is_complete else "Awaiting confirmation",
        query=original_query,
        answer=agent_response.answer,
        context="",  # Agent may not use RAG context
        context_used="",  # Agent may not use RAG context
        n_chunks_found=agent_response.n_chunks_found,
        sources=agent_response.sources,
        relevant_chunks=agent_response.relevant_chunks,
        model_used=agent_response.model_used,
        conversation_id=agent_response.conversation_id or "",
        message_id=agent_response.message_id or "",
        artifacts=[],  # TODO: Map artifacts when available
        routing_strategy=agent_response.routing_strategy,
        routing_confidence=agent_response.routing_confidence,
        chromadb_queried=agent_response.n_chunks_found > 0,
        # Agent-specific fields
        agent_steps=[
            AgentStepResponse(
                step_number=step.step_number,
                step_type=step.step_type,
                content=step.content,
                tool_call=AgentToolCallResponse(
                    tool_name=step.tool_call.tool_name,
                    parameters=step.tool_call.parameters,
                    result=step.tool_call.result,
                    error=step.tool_call.error,
                    execution_time_ms=step.tool_call.execution_time_ms
                ) if step.tool_call else None,
                timestamp=step.timestamp
            )
            for step in agent_response.agent_steps
        ],
        tools_executed=agent_response.tools_executed,
        pending_confirmations=[
            PendingConfirmationResponse(
                confirmation_id=conf.confirmation_id,
                tool_name=conf.tool_call.tool_name,
                parameters=conf.tool_call.parameters,
                warning_message=conf.warning_message,
                conversation_id=conf.conversation_id
            )
            for conf in agent_response.pending_confirmations
        ],
        requires_confirmation=agent_response.requires_confirmation,
        is_complete=agent_response.is_complete
    )
