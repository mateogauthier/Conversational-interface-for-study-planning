"""Base classes and interfaces for agent providers."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ToolSafety(str, Enum):
    """Safety classification for tools."""
    SAFE = "safe"  # Auto-execute (read-only operations)
    REQUIRES_CONFIRM = "requires_confirm"  # User confirmation needed (write operations)
    ADMIN_ONLY = "admin_only"  # Only admins can execute


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for tool execution")
    reasoning: Optional[str] = Field(None, description="Agent's reasoning for calling this tool")
    result: Optional[Any] = Field(None, description="Result after execution")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    execution_time_ms: Optional[int] = Field(None, description="Time taken to execute in milliseconds")


class AgentStep(BaseModel):
    """Represents a single step in agent execution."""
    step_number: int = Field(..., description="Sequential step number")
    step_type: str = Field(..., description="Type of step: 'thought', 'tool_call', 'result', 'error'")
    content: str = Field(..., description="Step content or description")
    tool_call: Optional[ToolCall] = Field(None, description="Tool call details if step_type is 'tool_call'")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When this step occurred")


class PendingConfirmation(BaseModel):
    """Represents a pending tool execution requiring user confirmation."""
    confirmation_id: str = Field(..., description="Unique ID for this confirmation request")
    tool_call: ToolCall = Field(..., description="The tool call awaiting confirmation")
    warning_message: str = Field(..., description="Warning message to display to user")
    conversation_id: str = Field(..., description="Conversation this confirmation belongs to")
    expires_at: Optional[datetime] = Field(None, description="When this confirmation expires")


class AgentResponse(BaseModel):
    """Response from agent execution."""
    answer: str = Field(..., description="Final answer or current status message")
    agent_steps: List[AgentStep] = Field(default_factory=list, description="Execution steps taken by agent")
    tools_executed: List[str] = Field(default_factory=list, description="List of tool names executed")
    pending_confirmations: List[PendingConfirmation] = Field(
        default_factory=list,
        description="Tool executions awaiting user confirmation"
    )
    requires_confirmation: bool = Field(default=False, description="Whether user confirmation is needed")
    is_complete: bool = Field(default=True, description="Whether agent has finished processing")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    message_id: Optional[str] = Field(None, description="Message ID if saved")

    # RAG-specific fields (for compatibility)
    sources: List[str] = Field(default_factory=list, description="Source files used")
    n_chunks_found: int = Field(default=0, description="Number of RAG chunks found")
    relevant_chunks: List[Any] = Field(default_factory=list, description="RAG chunks")
    model_used: Optional[str] = Field(None, description="LLM model used")

    # Routing metadata
    routing_strategy: Optional[str] = Field(None, description="Routing strategy used")
    routing_confidence: Optional[float] = Field(None, description="Routing confidence score")


class Tool(BaseModel):
    """Tool definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="What this tool does")
    parameters_schema: Dict[str, Any] = Field(..., description="JSON schema for parameters")
    safety: ToolSafety = Field(..., description="Safety classification")
    required_role: Optional[str] = Field(None, description="Required user role (admin/student/None)")
    example_usage: Optional[str] = Field(None, description="Example of how to use this tool")


class AgentProvider(ABC):
    """Abstract base class for agent providers.

    Implementations:
    - LocalAgentProvider: Uses existing services directly (current implementation)
    - APIAgentProvider: Calls external agent API (future implementation)
    """

    @abstractmethod
    async def execute_query(
        self,
        query: str,
        user: Any,  # UserInDB type
        conversation_id: Optional[str] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Execute a query using the agent.

        Args:
            query: User's query text
            user: Authenticated user object
            conversation_id: Optional conversation ID to continue
            auto_approve_tools: Whether to auto-approve tool executions
            **kwargs: Additional provider-specific parameters

        Returns:
            AgentResponse with answer, steps, and pending confirmations
        """
        pass

    @abstractmethod
    async def confirm_action(
        self,
        confirmation_id: str,
        approved: bool,
        user: Any,  # UserInDB type
    ) -> AgentResponse:
        """Confirm or deny a pending tool execution.

        Args:
            confirmation_id: ID of the pending confirmation
            approved: Whether user approved the action
            user: Authenticated user object

        Returns:
            AgentResponse with updated execution status
        """
        pass

    @abstractmethod
    async def get_available_tools(
        self,
        user: Any,  # UserInDB type
    ) -> List[Tool]:
        """Get list of tools available to the user.

        Args:
            user: Authenticated user object

        Returns:
            List of Tool definitions user can access
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the agent provider is available.

        Returns:
            True if provider is ready, False otherwise
        """
        pass
