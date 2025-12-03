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
from app.tools.http_executor import HTTPToolExecutor
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

        # Initialize HTTP tool executor (calls Agent API)
        self.tool_executor = HTTPToolExecutor(
            agent_api_url="http://agent-api:8002"
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

        # Multi-iteration agent execution loop (ReAct pattern)
        iteration = 0
        max_iterations = self.max_iterations
        should_continue = True
        executed_tool_signatures = set()  # Track executed tool+params to prevent loops

        while should_continue and iteration < max_iterations:
            iteration += 1

            # Add iteration marker
            step_counter += 1
            agent_steps.append(AgentStep(
                step_number=step_counter,
                step_type="thought",
                content=f"Iteration {iteration}/{max_iterations}: {tool_plan if iteration == 1 else 'Re-evaluating based on results...'}"
            ))

            # Parse tool calls from plan (pass original query and kwargs for user preferences)
            tool_calls = await self._extract_tool_calls(tool_plan, user, original_query=query, **kwargs)

            # If no tools in this iteration, break
            if not tool_calls:
                step_counter += 1
                agent_steps.append(AgentStep(
                    step_number=step_counter,
                    step_type="thought",
                    content="No additional tools needed. Ready to generate answer."
                ))
                break

            # Execute tools for this iteration
            for tool_call_plan in tool_calls:
                tool_name = tool_call_plan["name"]
                parameters = tool_call_plan["parameters"]

                # Create signature for loop detection
                import json
                param_signature = json.dumps(parameters, sort_keys=True)
                tool_signature = f"{tool_name}:{param_signature}"

                # Check if we've already executed this exact tool call
                if tool_signature in executed_tool_signatures:
                    step_counter += 1
                    agent_steps.append(AgentStep(
                        step_number=step_counter,
                        step_type="thought",
                        content=f"Skipping {tool_name} - already executed with same parameters. Breaking loop."
                    ))
                    logger.warning(f"Loop detected: {tool_name} with params {parameters} already executed")
                    continue

                # Mark this tool call as executed
                executed_tool_signatures.add(tool_signature)

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

            # After executing tools, check if we need another iteration
            if iteration < max_iterations:
                step_counter += 1
                agent_steps.append(AgentStep(
                    step_number=step_counter,
                    step_type="thought",
                    content=f"Evaluating if more information is needed..."
                ))

                # Ask LLM if it needs more tools or is ready to answer
                decision = await self._should_continue_iteration(
                    query=query,
                    agent_steps=agent_steps,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    user=user,
                    **kwargs
                )

                if decision["should_continue"]:
                    tool_plan = decision["next_plan"]
                    step_counter += 1
                    agent_steps.append(AgentStep(
                        step_number=step_counter,
                        step_type="thought",
                        content=f"Need more information: {decision['reason']}"
                    ))
                else:
                    step_counter += 1
                    agent_steps.append(AgentStep(
                        step_number=step_counter,
                        step_type="thought",
                        content=f"Sufficient information gathered: {decision['reason']}"
                    ))
                    should_continue = False
            else:
                # Max iterations reached
                step_counter += 1
                agent_steps.append(AgentStep(
                    step_number=step_counter,
                    step_type="thought",
                    content=f"Maximum iterations ({max_iterations}) reached. Generating answer with available information."
                ))
                should_continue = False

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
                "agent_steps_count": len(agent_steps),
                "iterations_completed": iteration
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
            message_id=message_id,
            iterations_completed=iteration,
            max_iterations=max_iterations
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
        user: UserInDB,
        original_query: str = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Extract tool calls from plan.

        Simple implementation: looks for tool names in plan text.
        In production, use Instructor for structured output.

        Args:
            plan: LLM-generated plan text
            user: User making the request
            original_query: Original user query (preserves language and intent)
            **kwargs: Additional parameters including n_results from user preferences
        """
        tool_calls = []
        available_tools = get_user_tools(user)

        # Simple pattern matching
        for tool in available_tools:
            if tool.name in plan.lower():
                # Extract parameters (simplified)
                parameters = {}

                if tool.name == "search_documents":
                    # If we have the original query, use it directly to preserve language
                    if original_query:
                        parameters["query"] = original_query
                    else:
                        # Fallback: Extract search query from plan
                        # Look for quoted text or keywords after common phrases
                        import re
                        # Try to find quoted text first
                        quoted = re.search(r'["\']([^"\']+)["\']', plan)
                        if quoted:
                            parameters["query"] = quoted.group(1)
                        elif "search for" in plan.lower():
                            parameters["query"] = plan.lower().split("search for", 1)[1].split("\n")[0].strip().strip('"\'')
                        elif "search documents about" in plan.lower():
                            parameters["query"] = plan.lower().split("search documents about", 1)[1].split("\n")[0].strip().strip('"\'')
                        else:
                            # Fallback: extract main keywords from query
                            # Remove tool names and common words
                            clean_plan = plan.lower()
                            for word in ["search_documents", "search", "documents", "find", "look for"]:
                                clean_plan = clean_plan.replace(word, "")
                            parameters["query"] = clean_plan.strip().split("\n")[0][:100]
                    # Use user's preferred chunk count, default to 5
                    parameters["n_results"] = kwargs.get("n_results", 5)

                elif tool.name == "web_search":
                    # Extract web search query - similar to search_documents
                    # Use original query to preserve language
                    if original_query:
                        parameters["query"] = original_query
                    else:
                        # Fallback: Extract search query from plan
                        import re
                        # Try to find quoted text first
                        quoted = re.search(r'["\']([^"\']+)["\']', plan)
                        if quoted:
                            parameters["query"] = quoted.group(1)
                        elif "search for" in plan.lower():
                            parameters["query"] = plan.lower().split("search for", 1)[1].split("\n")[0].strip().strip('"\'')
                        elif "web_search" in plan.lower() and "query=" in plan.lower():
                            # Extract from function call format: web_search(query="...")
                            query_match = re.search(r'query=["\'"]([^"\']+)["\']', plan)
                            if query_match:
                                parameters["query"] = query_match.group(1)
                        else:
                            # Fallback: Use cleaned plan
                            clean_plan = plan.lower()
                            for word in ["web_search", "search", "web", "find", "look for"]:
                                clean_plan = clean_plan.replace(word, "")
                            parameters["query"] = clean_plan.strip().split("\n")[0][:100]
                    # Default max_results to 5
                    parameters["max_results"] = kwargs.get("max_results", 5)

                elif tool.name == "get_file_info":
                    # Extract filename parameter
                    import re
                    # Try to find quoted filename
                    filename_match = re.search(r'filename=["\'"]([^"\']+)["\']', plan)
                    if filename_match:
                        parameters["filename"] = filename_match.group(1)
                    else:
                        # Try to find any quoted text that might be the filename
                        quoted = re.search(r'["\']([^"\']+\.(?:pdf|docx|txt|xlsx|md))["\']', plan, re.IGNORECASE)
                        if quoted:
                            parameters["filename"] = quoted.group(1)

                elif tool.name == "list_conversations":
                    # Extract limit parameter if present
                    import re
                    limit_match = re.search(r'limit=(\d+)', plan)
                    if limit_match:
                        parameters["limit"] = int(limit_match.group(1))
                    else:
                        parameters["limit"] = kwargs.get("limit", 10)

                elif tool.name == "delete_file":
                    # Extract filename parameter
                    import re
                    filename_match = re.search(r'filename=["\'"]([^"\']+)["\']', plan)
                    if filename_match:
                        parameters["filename"] = filename_match.group(1)
                    else:
                        # Try to find any quoted text that might be the filename
                        quoted = re.search(r'["\']([^"\']+\.(?:pdf|docx|txt|xlsx|md))["\']', plan, re.IGNORECASE)
                        if quoted:
                            parameters["filename"] = quoted.group(1)

                elif tool.name == "read_file_content":
                    # Extract filename parameter (same logic as get_file_info)
                    import re
                    filename_match = re.search(r'filename=["\'"]([^"\']+)["\']', plan)
                    if filename_match:
                        parameters["filename"] = filename_match.group(1)
                    else:
                        # Try to find any quoted text that might be the filename
                        quoted = re.search(r'["\']([^"\']+\.(?:pdf|docx|txt|xlsx|md))["\']', plan, re.IGNORECASE)
                        if quoted:
                            parameters["filename"] = quoted.group(1)

                # Only add tool call if we have required parameters
                if tool.name == "search_documents" and "query" in parameters:
                    tool_calls.append({
                        "name": tool.name,
                        "parameters": parameters
                    })
                elif tool.name == "web_search" and "query" in parameters:
                    tool_calls.append({
                        "name": tool.name,
                        "parameters": parameters
                    })
                elif tool.name in ["list_files", "get_user_stats", "list_conversations"]:
                    # These tools don't require query parameter
                    tool_calls.append({
                        "name": tool.name,
                        "parameters": parameters
                    })
                elif tool.name in ["get_file_info", "delete_file", "read_file_content"] and "filename" in parameters:
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

    async def _should_continue_iteration(
        self,
        query: str,
        agent_steps: List[AgentStep],
        iteration: int,
        max_iterations: int,
        user: UserInDB,
        **kwargs
    ) -> Dict[str, Any]:
        """Determine if agent needs another iteration.

        Args:
            query: Original user query
            agent_steps: Steps executed so far
            iteration: Current iteration number
            max_iterations: Maximum allowed iterations
            user: Authenticated user

        Returns:
            Dict with:
                - should_continue: bool
                - reason: str explanation
                - next_plan: str (if should_continue is True)
        """
        # Build summary of what we know so far
        tool_results_summary = []
        for step in agent_steps:
            if step.step_type == "result" and step.tool_call and step.tool_call.result:
                tool_name = step.tool_call.tool_name
                result = step.tool_call.result

                # Create concise summary of result
                if tool_name == "search_documents":
                    n_chunks = result.get("n_chunks_found", 0) if isinstance(result, dict) else 0
                    # Extract source filenames from chunks
                    sources = set()
                    if isinstance(result, dict) and "chunks" in result:
                        for chunk in result.get("chunks", []):
                            if "source" in chunk:
                                sources.add(chunk["source"])
                    sources_str = f" from files: {', '.join(sources)}" if sources else ""
                    tool_results_summary.append(f"- search_documents: Found {n_chunks} document chunks{sources_str}")
                elif tool_name == "list_files":
                    files = result.get("files", []) if isinstance(result, dict) else []
                    tool_results_summary.append(f"- list_files: Found {len(files)} files")
                elif tool_name == "read_file_content":
                    filename = result.get("filename", "unknown") if isinstance(result, dict) else "unknown"
                    content_len = len(result.get("content", "")) if isinstance(result, dict) else 0
                    if content_len > 0:
                        tool_results_summary.append(f"- read_file_content: Successfully read COMPLETE file '{filename}' ({content_len} characters). You now have ALL the data from this file.")
                    else:
                        tool_results_summary.append(f"- read_file_content: Failed to read {filename}")
                elif tool_name == "web_search":
                    result_count = result.get("result_count", 0) if isinstance(result, dict) else 0
                    tool_results_summary.append(f"- web_search: Found {result_count} web results")
                else:
                    tool_results_summary.append(f"- {tool_name}: Completed")

        summary = "\n".join(tool_results_summary) if tool_results_summary else "No tool results yet"

        # Get available tools for user
        available_tools = get_user_tools(user)
        tools_list = ", ".join([t.name for t in available_tools])

        # Ask LLM if it can answer the question or needs more tools
        decision_prompt = f"""You are evaluating whether you have enough information to answer the user's question.

User's Question: {query}

Tools Executed So Far (Iteration {iteration}/{max_iterations}):
{summary}

Available Tools: {tools_list}

**CRITICAL: CHECK IF YOU ALREADY HAVE COMPLETE FILE CONTENT!**

FIRST, scan the tool results above for "Successfully read COMPLETE file". If you see this message, it means read_file_content was ALREADY executed and YOU HAVE ALL THE DATA. You MUST respond with should_continue=false immediately!

**WHEN TO STOP (should_continue = false):**
- ✓ If you see "Successfully read COMPLETE file" anywhere in tool results → STOP NOW!
- ✓ If read_file_content appears in the tool results with content > 0 characters → STOP NOW!
- ✓ You have sufficient information to answer the user's question → STOP!
- ✓ You've reached iteration 3, 4 or 5 → STOP NOW!

**WHEN TO CONTINUE (should_continue = true):**
- ✗ If search_documents found chunks but you need complete file content
- ✗ If user asks for specific YEAR but search chunks show DIFFERENT year
- ✗ If only partial information available from search chunks

**HOW TO REQUEST read_file_content:**
Look at the tool results for search_documents. Extract the filename from the "source" field in the chunks. Then request: read_file_content(filename='EXACT_FILENAME_FROM_SOURCE')

**ANTI-LOOP PROTECTION:**
- NEVER request a tool that was already executed
- If you see the same tool name twice in results, DO NOT request it again

Respond in this EXACT JSON format:

Example 1 - If you need to read a file (extract filename from search results):
{{
  "should_continue": true,
  "reason": "Need complete file, search chunks show wrong year",
  "next_tools": "read_file_content(filename='FILENAME_FROM_SOURCE_FIELD')"
}}

Example 2 - If you already have complete file OR enough information:
{{
  "should_continue": false,
  "reason": "Already have complete file content"
}}

**IMPORTANT**:
- In "next_tools", use the EXACT filename from the "source" field in search results
- Do NOT hardcode any filename - extract it dynamically from the tool results above
- If read_file_content was already executed, you MUST set should_continue=false

RESPOND ONLY WITH VALID JSON, NO OTHER TEXT."""

        try:
            # Get LLM decision
            response = await self.llm_service.generate_with_context(
                prompt=decision_prompt,
                context="",
                conversation_history=[],
                model=kwargs.get("model"),
                language="english"  # Force English for structured output
            )

            # Parse JSON response
            import json
            import re

            # Extract JSON from response (might have markdown formatting)
            json_match = re.search(r'\{[^}]+\}', response["response"], re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(0))
            else:
                # Fallback: stop after first iteration to avoid infinite loops
                logger.warning(f"Could not parse LLM decision, defaulting to stop")
                return {
                    "should_continue": False,
                    "reason": "Could not determine if more information needed",
                    "next_plan": ""
                }

            should_continue = decision.get("should_continue", False)
            reason = decision.get("reason", "No reason provided")
            next_tools = decision.get("next_tools", "")

            if should_continue and next_tools:
                # Generate new tool plan
                next_plan = f"Based on current results, execute these tools: {next_tools}"
                return {
                    "should_continue": True,
                    "reason": reason,
                    "next_plan": next_plan
                }
            else:
                return {
                    "should_continue": False,
                    "reason": reason,
                    "next_plan": ""
                }

        except Exception as e:
            logger.error(f"Error in _should_continue_iteration: {e}")
            # Fallback: stop to avoid infinite loops
            return {
                "should_continue": False,
                "reason": f"Error evaluating continuation: {str(e)}",
                "next_plan": ""
            }

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
        has_web_search = False
        web_search_empty = False
        has_doc_search = False
        doc_search_empty = False
        has_read_file_content = False

        for step in agent_steps:
            if step.step_type == "result" and step.tool_call and step.tool_call.result:
                tool_name = step.tool_call.tool_name
                result = step.tool_call.result

                context_parts.append(f"Tool: {tool_name}")
                context_parts.append(f"Result: {result}")

                # Check if web search returned empty results
                if tool_name == "web_search":
                    has_web_search = True
                    result_count = result.get("result_count", 0) if isinstance(result, dict) else 0
                    if result_count == 0:
                        web_search_empty = True

                # Check if document search returned empty results
                if tool_name == "search_documents":
                    has_doc_search = True
                    n_chunks = result.get("n_chunks_found", 0) if isinstance(result, dict) else 0
                    if n_chunks == 0:
                        doc_search_empty = True

                # Check if read_file_content was used successfully
                if tool_name == "read_file_content":
                    content_len = len(result.get("content", "")) if isinstance(result, dict) else 0
                    if content_len > 0:
                        has_read_file_content = True

        context = "\n\n".join(context_parts)

        # Add explicit anti-hallucination instructions when searches return empty or insufficient data
        additional_instructions = ""
        if has_web_search and web_search_empty:
            additional_instructions += "\n\n**CRITICAL**: The web search returned ZERO results. You do NOT have any information to answer this question. You MUST tell the user that you could not find the information online. DO NOT make up addresses, locations, phone numbers, or any other specific details. Be honest that the search was unsuccessful."

        if has_doc_search and doc_search_empty:
            additional_instructions += "\n\n**CRITICAL**: The document search returned ZERO relevant chunks. You do NOT have any information in the documents to answer this question. DO NOT make up information. Tell the user that you could not find relevant information in the uploaded documents."

        if not context_parts:
            additional_instructions += "\n\n**CRITICAL**: No tool results were obtained. You do NOT have information to answer this question. DO NOT make up specific details like addresses, names, or facts."

        # Add instructions based on which tools were used
        if has_read_file_content:
            # If read_file_content was used, we have COMPLETE file content
            additional_instructions += "\n\n**CRITICAL INSTRUCTION - COMPLETE FILE CONTENT AVAILABLE**: The read_file_content tool was used successfully, which means you have access to the COMPLETE content of the file(s), not just search chunks. You must carefully analyze ALL the text content provided in the 'read_file_content' results above.\n\n**THOROUGH SEARCH REQUIRED**: If the user asks for information from a specific year (e.g., 2024), you MUST search through the ENTIRE file content for ALL occurrences of that year. Look for date patterns like 'DD/MM/2024' or '2024' in the text. Do NOT just look at the first few lines - scan the complete document.\n\n**DATE FORMAT**: Dates are typically in DD/MM/YYYY format (e.g., '03/07/2024' means July 3rd, 2024). Extract ALL entries matching the requested year.\n\n**ANTI-HALLUCINATION**: Only report information that is explicitly present in the file content. If you cannot find data for the requested year after thoroughly searching, honestly tell the user you didn't find any entries for that specific year, and optionally mention which years you DID find data for."
        elif has_doc_search:
            # If only search_documents was used (partial chunks)
            additional_instructions += "\n\n**CRITICAL INSTRUCTION**: You MUST base your answer ONLY on the exact text content provided in the document chunks above. DO NOT invent, extrapolate, or assume information that is not explicitly stated in the chunks. If the chunks do not contain complete information to answer the question (e.g., user asks for all grades but chunks only show 2 courses), you MUST tell the user that you only found partial information and list ONLY what you actually found. NEVER create fictional data, grades, names, or any other details. If you're unsure or the information is incomplete, say so explicitly.\n\n**DATE/YEAR VERIFICATION**: If the user asks for information from a specific year or date range, you MUST verify that the data you found matches that year/date. If the chunks show data from a DIFFERENT year than what the user asked for, you MUST tell the user that you found data from year X but they asked for year Y. For example, if the user asks for '2023 grades' and the chunks show dates like '08/07/2025', those are from 2025, NOT 2023 - you must tell the user you didn't find 2023 data."

        # Combine with user's custom instructions if any
        final_instructions = kwargs.get("instructions", "")
        if additional_instructions:
            final_instructions = (final_instructions + additional_instructions) if final_instructions else additional_instructions.strip()

        # Generate answer
        response = await self.llm_service.generate_with_context(
            prompt=query,
            context=context if context else "No information available from tools.",
            conversation_history=conversation_history,
            model=kwargs.get("model"),
            language=kwargs.get("language"),
            instructions=final_instructions
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
