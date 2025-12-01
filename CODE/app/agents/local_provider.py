"""Local agent provider using existing services directly."""

import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.agents.base import (
    AgentProvider,
    AgentResponse,
    AgentStep,
    ToolCall,
    PendingConfirmation,
    Tool,
    ToolSafety
)
from app.tools.executor import ToolExecutor
from app.tools.registry import get_user_tools, get_tool_descriptions_for_llm, get_tool
from app.db.models import UserInDB

logger = logging.getLogger(__name__)


class LocalAgentProvider(AgentProvider):
    """Local agent implementation using existing services.

    This provider executes agent queries using:
    - LLMService for reasoning and tool selection
    - ToolExecutor for executing tools
    - ConversationService for managing conversation state
    - Existing RAG pipeline for document retrieval
    """

    def __init__(
        self,
        llm_service,
        rag_service,
        conversation_service,
        file_service,
        user_service,
        max_iterations: int = 5,
        auto_approve_reads: bool = True,
    ):
        """Initialize local agent provider.

        Args:
            llm_service: LLMService instance
            rag_service: RAGService instance
            conversation_service: ConversationService instance
            file_service: FileService instance
            user_service: UserService instance
            max_iterations: Maximum agent iterations
            auto_approve_reads: Whether to auto-approve read-only tools
        """
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.conversation_service = conversation_service
        self.file_service = file_service
        self.user_service = user_service
        self.max_iterations = max_iterations
        self.auto_approve_reads = auto_approve_reads

        # Initialize tool executor
        self.tool_executor = ToolExecutor(
            file_service=file_service,
            rag_service=rag_service,
            conversation_service=conversation_service,
            user_service=user_service,
        )

        # Store pending confirmations in memory
        # In production, this should be in Redis or database
        self.pending_confirmations: Dict[str, PendingConfirmation] = {}

    async def execute_query(
        self,
        query: str,
        user: UserInDB,
        conversation_id: Optional[str] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Execute a query using the local agent.

        Args:
            query: User's query text
            user: Authenticated user object
            conversation_id: Optional conversation ID to continue
            auto_approve_tools: Whether to auto-approve all tool executions
            **kwargs: Additional parameters (n_results, language, model, etc.)

        Returns:
            AgentResponse with answer, steps, and pending confirmations
        """
        logger.info(f"Local agent executing query for user {user.auth0_id}: {query}")

        # Initialize execution state
        agent_steps: List[AgentStep] = []
        tools_executed: List[str] = []
        step_counter = 0

        # Create or load conversation
        if not conversation_id:
            conversation_id = await self.conversation_service.create_conversation(
                user_id=str(user.id),
                auth0_id=user.auth0_id,
                first_message=query
            )

        # Save user message
        await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=query
        )

        # Get conversation history
        conversation_history = await self.conversation_service.get_conversation_history(
            conversation_id=conversation_id
        )

        # Analyze query to determine if tools are needed
        needs_tools, tool_plan = await self._analyze_query_for_tools(
            query=query,
            user=user,
            conversation_history=conversation_history
        )

        if not needs_tools:
            # Use standard RAG pipeline
            logger.info("No tools needed, using standard RAG")
            return await self._execute_standard_rag(
                query=query,
                user=user,
                conversation_id=conversation_id,
                conversation_history=conversation_history,
                **kwargs
            )

        # Agent execution loop with tools
        step_counter += 1
        agent_steps.append(AgentStep(
            step_number=step_counter,
            step_type="thought",
            content=f"Planning: {tool_plan}"
        ))

        # Parse tool calls from plan
        tool_calls = await self._extract_tool_calls(tool_plan, user)

        # Execute tools
        for tool_call_plan in tool_calls:
            tool_name = tool_call_plan["name"]
            parameters = tool_call_plan["parameters"]

            # Check if tool requires confirmation
            tool_def = get_tool(tool_name)
            if tool_def and tool_def.safety == ToolSafety.REQUIRES_CONFIRM:
                # Check if should auto-approve
                if not (auto_approve_tools or self.auto_approve_reads):
                    # Create pending confirmation
                    confirmation = await self._create_pending_confirmation(
                        tool_name=tool_name,
                        parameters=parameters,
                        user=user,
                        conversation_id=conversation_id
                    )

                    step_counter += 1
                    agent_steps.append(AgentStep(
                        step_number=step_counter,
                        step_type="confirmation_required",
                        content=f"Waiting for confirmation to execute: {tool_name}"
                    ))

                    return AgentResponse(
                        answer=f"I need your confirmation to {tool_def.description.lower()}. Please review and approve.",
                        agent_steps=agent_steps,
                        tools_executed=tools_executed,
                        pending_confirmations=[confirmation],
                        requires_confirmation=True,
                        is_complete=False,
                        conversation_id=conversation_id
                    )

            # Execute tool
            step_counter += 1
            agent_steps.append(AgentStep(
                step_number=step_counter,
                step_type="tool_call",
                content=f"Executing {tool_name}",
                tool_call=ToolCall(
                    tool_name=tool_name,
                    parameters=parameters
                )
            ))

            tool_result = await self.tool_executor.execute(
                tool_name=tool_name,
                parameters=parameters,
                user=user
            )

            tools_executed.append(tool_name)

            step_counter += 1
            if tool_result.error:
                agent_steps.append(AgentStep(
                    step_number=step_counter,
                    step_type="error",
                    content=f"Tool execution failed: {tool_result.error}",
                    tool_call=tool_result
                ))
            else:
                agent_steps.append(AgentStep(
                    step_number=step_counter,
                    step_type="result",
                    content=f"Tool completed successfully",
                    tool_call=tool_result
                ))

        # Generate final answer using LLM with tool results
        final_answer = await self._generate_final_answer(
            query=query,
            agent_steps=agent_steps,
            conversation_history=conversation_history,
            **kwargs
        )

        # Save assistant message
        message_id = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_answer,
            metadata={
                "tools_executed": tools_executed,
                "agent_steps_count": len(agent_steps)
            }
        )

        return AgentResponse(
            answer=final_answer,
            agent_steps=agent_steps,
            tools_executed=tools_executed,
            pending_confirmations=[],
            requires_confirmation=False,
            is_complete=True,
            conversation_id=conversation_id,
            message_id=message_id
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
        logger.info(f"Confirmation {confirmation_id}: approved={approved} by user {user.auth0_id}")

        confirmation = self.pending_confirmations.get(confirmation_id)
        if not confirmation:
            return AgentResponse(
                answer="Confirmation not found or has expired.",
                is_complete=True
            )

        # Remove from pending
        del self.pending_confirmations[confirmation_id]

        if not approved:
            return AgentResponse(
                answer="Action cancelled by user.",
                is_complete=True,
                conversation_id=confirmation.conversation_id
            )

        # Execute the tool
        tool_call = confirmation.tool_call
        agent_steps = [
            AgentStep(
                step_number=1,
                step_type="confirmation_approved",
                content=f"User approved: {tool_call.tool_name}"
            )
        ]

        tool_result = await self.tool_executor.execute(
            tool_name=tool_call.tool_name,
            parameters=tool_call.parameters,
            user=user
        )

        agent_steps.append(AgentStep(
            step_number=2,
            step_type="result",
            content=f"Tool completed: {tool_call.tool_name}",
            tool_call=tool_result
        ))

        if tool_result.error:
            answer = f"Action failed: {tool_result.error}"
        else:
            answer = f"Action completed successfully. {self._format_tool_result(tool_result)}"

        # Save message
        message_id = await self.conversation_service.add_message(
            conversation_id=confirmation.conversation_id,
            role="assistant",
            content=answer,
            metadata={"tool_executed": tool_call.tool_name}
        )

        return AgentResponse(
            answer=answer,
            agent_steps=agent_steps,
            tools_executed=[tool_call.tool_name],
            is_complete=True,
            conversation_id=confirmation.conversation_id,
            message_id=message_id
        )

    async def get_available_tools(self, user: UserInDB) -> List[Tool]:
        """Get list of tools available to the user."""
        return get_user_tools(user)

    async def is_available(self) -> bool:
        """Check if the local agent provider is available."""
        # Check if LLM service is available
        return await self.llm_service.is_available()

    # Helper methods

    async def _analyze_query_for_tools(
        self,
        query: str,
        user: UserInDB,
        conversation_history: List[Dict[str, str]]
    ) -> tuple[bool, str]:
        """Analyze if query requires tools and generate plan.

        Returns:
            (needs_tools: bool, plan: str)
        """
        # Get available tools
        tool_descriptions = get_tool_descriptions_for_llm(user)

        # Create analysis prompt
        prompt = f"""Analyze this user query and determine if it requires using tools to answer.

{tool_descriptions}

User query: "{query}"

If tools are needed, respond with:
NEEDS_TOOLS: Yes
PLAN: [list the tools to use and why]

If no tools are needed (can be answered with general knowledge or document search only):
NEEDS_TOOLS: No
PLAN: Answer directly"""

        response = await self.llm_service.generate_response(prompt=prompt)
        response_text = response.get("response", "")

        needs_tools = "NEEDS_TOOLS: Yes" in response_text or "NEEDS_TOOLS:Yes" in response_text

        # Extract plan
        plan = response_text
        if "PLAN:" in response_text:
            plan = response_text.split("PLAN:", 1)[1].strip()

        return needs_tools, plan

    async def _extract_tool_calls(
        self,
        plan: str,
        user: UserInDB
    ) -> List[Dict[str, Any]]:
        """Extract tool calls from plan.

        Simple implementation: looks for tool names in plan text.
        In production, use Instructor for structured output.
        """
        tool_calls = []
        available_tools = get_user_tools(user)

        # Simple pattern matching
        for tool in available_tools:
            if tool.name in plan.lower():
                # Extract parameters (simplified)
                parameters = {}

                if tool.name == "search_documents" and "search" in plan.lower():
                    # Try to extract search query
                    parameters["query"] = plan.split("search", 1)[1].split("\n")[0].strip()
                    parameters["n_results"] = 5

                tool_calls.append({
                    "name": tool.name,
                    "parameters": parameters
                })

        return tool_calls

    async def _execute_standard_rag(
        self,
        query: str,
        user: UserInDB,
        conversation_id: str,
        conversation_history: List[Dict[str, str]],
        **kwargs
    ) -> AgentResponse:
        """Execute standard RAG pipeline without tools."""
        n_results = kwargs.get("n_results", 5)

        # Search documents
        search_results = await self.rag_service.search_documents_async(
            query=query,
            user=user,
            n_results=n_results
        )

        # Generate answer
        llm_response = await self.llm_service.generate_with_context(
            prompt=query,
            context=search_results.get("context", ""),
            conversation_history=conversation_history,
            model=kwargs.get("model"),
            language=kwargs.get("language"),
            instructions=kwargs.get("instructions")
        )

        # Save message
        sources = list(set([chunk.metadata.get('file_name', 'Unknown')
                           for chunk in search_results.get("relevant_chunks", [])]))

        message_id = await self.conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=llm_response["response"],
            model_used=llm_response.get("model_used"),
            source_files=sources
        )

        return AgentResponse(
            answer=llm_response["response"],
            agent_steps=[],
            tools_executed=[],
            conversation_id=conversation_id,
            message_id=message_id,
            sources=sources,
            n_chunks_found=search_results.get("n_chunks_found", 0),
            relevant_chunks=search_results.get("relevant_chunks", []),
            model_used=llm_response.get("model_used")
        )

    async def _generate_final_answer(
        self,
        query: str,
        agent_steps: List[AgentStep],
        conversation_history: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """Generate final answer using LLM with tool results."""
        # Build context from tool results
        context_parts = []
        for step in agent_steps:
            if step.step_type == "result" and step.tool_call and step.tool_call.result:
                context_parts.append(f"Tool: {step.tool_call.tool_name}")
                context_parts.append(f"Result: {step.tool_call.result}")

        context = "\n\n".join(context_parts)

        # Generate answer
        response = await self.llm_service.generate_with_context(
            prompt=query,
            context=context,
            conversation_history=conversation_history,
            model=kwargs.get("model"),
            language=kwargs.get("language"),
            instructions=kwargs.get("instructions")
        )

        return response["response"]

    async def _create_pending_confirmation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        user: UserInDB,
        conversation_id: str
    ) -> PendingConfirmation:
        """Create a pending confirmation for tool execution."""
        confirmation_id = str(uuid.uuid4())

        tool_def = get_tool(tool_name)
        warning_message = f"Do you want to {tool_def.description.lower()}?"

        if tool_name == "delete_file":
            filename = parameters.get("filename", "unknown")
            warning_message = f"Delete file '{filename}'? This action cannot be undone."
        elif tool_name == "delete_conversation":
            warning_message = "Delete this conversation and all its messages? This action cannot be undone."

        confirmation = PendingConfirmation(
            confirmation_id=confirmation_id,
            tool_call=ToolCall(
                tool_name=tool_name,
                parameters=parameters
            ),
            warning_message=warning_message,
            conversation_id=conversation_id,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )

        self.pending_confirmations[confirmation_id] = confirmation
        return confirmation

    def _format_tool_result(self, tool_call: ToolCall) -> str:
        """Format tool result for display."""
        if not tool_call.result:
            return ""

        result = tool_call.result
        if isinstance(result, dict):
            if "message" in result:
                return result["message"]
            if "file_count" in result:
                return f"Found {result['file_count']} files."
            if "conversation_count" in result:
                return f"Found {result['conversation_count']} conversations."

        return str(result)
