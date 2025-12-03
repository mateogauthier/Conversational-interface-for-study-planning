"""
LangGraph-based agent provider with proper state management and tool extensibility.

This agent uses LangGraph for reliable multi-step execution with deterministic flow control.
Adding new tools is as simple as:
1. Register the tool in AVAILABLE_TOOLS
2. LangGraph automatically handles execution and state management
"""
import logging
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any, List
from operator import add

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.agents.base import AgentProvider, AgentResponse, AgentStep, ToolCall, Tool
from app.db.models import UserInDB

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the agent workflow.

    LangGraph automatically manages this state across all nodes.
    """
    # User inputs
    query: str
    user: UserInDB
    conversation_id: Optional[str]

    # Tool execution results
    search_results: Optional[Dict[str, Any]]
    file_content: Optional[Dict[str, Any]]
    file_metadata: Optional[Dict[str, Any]]

    # Agent tracking
    agent_steps: Annotated[Sequence[AgentStep], add]  # Append-only list
    tools_executed: Annotated[Sequence[str], add]
    iteration: int

    # Final output
    answer: Optional[str]
    error: Optional[str]


class LangGraphAgentProvider(AgentProvider):
    """LangGraph-based agent with deterministic flow control.

    Architecture:
    - Each tool is a node in the graph
    - Routing logic is deterministic (no LLM deciding when to stop)
    - State is automatically managed by LangGraph
    - Adding new tools: just add to AVAILABLE_TOOLS and create a node
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
        **kwargs  # Accept any additional arguments for compatibility
    ):
        """Initialize LangGraph agent provider.

        Args:
            llm_service: LLM service for generating responses
            rag_service: RAG service for document search
            conversation_service: Conversation management
            file_service: File operations
            user_service: User management
            max_iterations: Maximum iterations to prevent infinite loops
            auto_approve_reads: Whether to auto-approve read operations (unused in LangGraph)
            **kwargs: Additional arguments for compatibility
        """
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.conversation_service = conversation_service
        self.file_service = file_service
        self.user_service = user_service
        self.max_iterations = max_iterations
        self.auto_approve_reads = auto_approve_reads  # Store but not used (no confirmations in LangGraph)

        # Build the workflow graph
        self.app = self._build_graph()

        logger.info("LangGraph agent provider initialized with deterministic routing")

    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph.

        Graph structure:
        START -> search_documents -> should_read_file?
                                   ├─> YES -> read_file_content -> generate_answer -> END
                                   └─> NO -> generate_answer -> END
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("search_documents", self._search_documents_node)
        workflow.add_node("read_file_content", self._read_file_content_node)
        workflow.add_node("generate_answer", self._generate_answer_node)

        # Set entry point
        workflow.set_entry_point("search_documents")

        # Add conditional routing
        workflow.add_conditional_edges(
            "search_documents",
            self._should_read_file,
            {
                "read_file": "read_file_content",
                "generate": "generate_answer"
            }
        )

        # Connect read_file to generate_answer
        workflow.add_edge("read_file_content", "generate_answer")

        # Connect generate_answer to END
        workflow.add_edge("generate_answer", END)

        return workflow.compile()

    async def execute_query(
        self,
        query: str,
        user: UserInDB,
        conversation_id: Optional[str] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Execute a query using LangGraph workflow.

        Args:
            query: User's query text
            user: Authenticated user
            conversation_id: Optional conversation ID
            auto_approve_tools: Whether to auto-approve destructive tools
            **kwargs: Additional parameters

        Returns:
            AgentResponse with results
        """
        try:
            # Get or create conversation
            if not conversation_id:
                conversation_id = await self.conversation_service.create_conversation(
                    user_id=str(user.id),
                    auth0_id=user.auth0_id,
                    first_message=query
                )

            # Get conversation history (truncated to fit context window)
            conversation_history = await self.conversation_service.get_conversation_history(
                conversation_id=conversation_id
            )

            # Initialize state
            initial_state: AgentState = {
                "query": query,
                "user": user,
                "conversation_id": conversation_id,
                "search_results": None,
                "file_content": None,
                "file_metadata": None,
                "agent_steps": [],
                "tools_executed": [],
                "iteration": 0,
                "answer": None,
                "error": None
            }

            # Run the graph
            final_state = await self.app.ainvoke(initial_state)

            # Save assistant message
            message_id = await self.conversation_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_state["answer"],
                metadata={
                    "tools_executed": list(final_state["tools_executed"]),
                    "agent_steps_count": len(final_state["agent_steps"]),
                    "iterations_completed": final_state["iteration"]
                }
            )

            # Build response
            return AgentResponse(
                answer=final_state["answer"],
                agent_steps=list(final_state["agent_steps"]),
                tools_executed=list(final_state["tools_executed"]),
                pending_confirmations=[],
                requires_confirmation=False,
                is_complete=True,
                conversation_id=conversation_id,
                message_id=message_id,
                iterations_completed=final_state["iteration"],
                max_iterations=self.max_iterations
            )

        except Exception as e:
            logger.error(f"Error in LangGraph agent execution: {e}", exc_info=True)
            raise

    async def _search_documents_node(self, state: AgentState) -> Dict[str, Any]:
        """Search for relevant documents.

        This is a node in the LangGraph workflow.
        """
        step_num = len(state["agent_steps"]) + 1

        # Add "thinking" step
        thinking_step = AgentStep(
            step_number=step_num,
            step_type="thought",
            content=f"Iteration {state['iteration'] + 1}: Searching documents for relevant information"
        )

        try:
            # Execute search
            search_results = await self.rag_service.search_documents_async(
                query=state["query"],
                user=state["user"],
                n_results=15
            )

            # Add tool execution step
            tool_step = AgentStep(
                step_number=step_num + 1,
                step_type="tool_call",
                content="Executing search_documents",
                tool_call=ToolCall(
                    tool_name="search_documents",
                    parameters={"query": state["query"], "n_results": 15}
                )
            )

            # Add result step
            result_step = AgentStep(
                step_number=step_num + 2,
                step_type="result",
                content=f"Found {search_results.get('n_chunks_found', 0)} document chunks",
                tool_call=ToolCall(
                    tool_name="search_documents",
                    parameters={"query": state["query"]},
                    result=search_results
                )
            )

            return {
                "search_results": search_results,
                "agent_steps": [thinking_step, tool_step, result_step],
                "tools_executed": ["search_documents"],
                "iteration": state["iteration"] + 1
            }

        except Exception as e:
            logger.error(f"Error in search_documents_node: {e}")
            error_step = AgentStep(
                step_number=step_num + 1,
                step_type="error",
                content=f"Search failed: {str(e)}"
            )
            return {
                "agent_steps": [thinking_step, error_step],
                "error": str(e)
            }

    def _should_read_file(self, state: AgentState) -> str:
        """Determine if we should read the complete file.

        This is deterministic routing logic - no LLM needed!

        Decision logic:
        - If search found chunks from a file AND we haven't read the file yet -> read_file
        - Otherwise -> generate answer with what we have
        """
        # Check if we already have file content
        if state.get("file_content"):
            return "generate"

        # Check if search found results
        search_results = state.get("search_results")
        if not search_results or search_results.get("n_chunks_found", 0) == 0:
            return "generate"

        # Extract filename from first chunk (field is 'relevant_chunks' not 'chunks')
        chunks = search_results.get("relevant_chunks", [])
        if not chunks:
            return "generate"

        # If we found chunks, read the complete file
        logger.info(f"Found {len(chunks)} chunks, will read complete file")
        return "read_file"

    async def _read_file_content_node(self, state: AgentState) -> Dict[str, Any]:
        """Read complete file content.

        This node extracts the filename from search results and reads the full file.
        """
        step_num = len(state["agent_steps"]) + 1

        try:
            # Extract filename from search results (field is 'relevant_chunks')
            chunks = state["search_results"].get("relevant_chunks", [])
            if not chunks:
                return {"agent_steps": [], "error": "No chunks to extract filename from"}

            # Filename is in metadata.file_name (chunks are Pydantic objects, metadata is dict)
            first_chunk = chunks[0]
            metadata = first_chunk.metadata if hasattr(first_chunk, 'metadata') else first_chunk.get("metadata", {})
            filename = metadata.get("file_name")
            if not filename:
                return {"agent_steps": [], "error": "Could not extract filename from search results"}

            thinking_step = AgentStep(
                step_number=step_num,
                step_type="thought",
                content=f"Reading complete file: {filename}"
            )

            # Read file content
            content = await self.file_service.extract_text_from_file(filename)

            if not content:
                error_step = AgentStep(
                    step_number=step_num + 1,
                    step_type="error",
                    content=f"Failed to read file: {filename}"
                )
                return {
                    "agent_steps": [thinking_step, error_step],
                    "error": f"Failed to read {filename}"
                }

            # Get file metadata
            file_meta = await self.file_service.get_file_metadata_by_name(filename)

            tool_step = AgentStep(
                step_number=step_num + 1,
                step_type="tool_call",
                content=f"Executing read_file_content",
                tool_call=ToolCall(
                    tool_name="read_file_content",
                    parameters={"filename": filename}
                )
            )

            result_step = AgentStep(
                step_number=step_num + 2,
                step_type="result",
                content=f"Successfully read COMPLETE file '{filename}' ({len(content)} characters)",
                tool_call=ToolCall(
                    tool_name="read_file_content",
                    parameters={"filename": filename},
                    result={
                        "filename": filename,
                        "content": content,
                        "file_size": file_meta.file_size if file_meta else 0,
                        "chunk_count": file_meta.chunk_count if file_meta else 0
                    }
                )
            )

            # Track file view
            await self.file_service.track_file_view(filename)

            return {
                "file_content": {"filename": filename, "content": content},
                "file_metadata": file_meta.dict() if file_meta else None,
                "agent_steps": [thinking_step, tool_step, result_step],
                "tools_executed": ["read_file_content"]
            }

        except Exception as e:
            logger.error(f"Error in read_file_content_node: {e}")
            error_step = AgentStep(
                step_number=step_num,
                step_type="error",
                content=f"File read failed: {str(e)}"
            )
            return {
                "agent_steps": [error_step],
                "error": str(e)
            }

    def _extract_entries_by_year(self, content: str, year: str) -> List[Dict[str, str]]:
        """Extract all entries from file content that contain the specified year.

        This is deterministic Python code - no LLM involved, so it finds EVERYTHING.
        """
        import re

        entries = []
        lines = content.split('\n')

        # Look for lines with dates containing the year (DD/MM/YYYY format)
        date_pattern = rf'\d{{2}}/\d{{2}}/{year}'

        for i, line in enumerate(lines):
            if re.search(date_pattern, line):
                # Found a line with a date from the requested year
                # Extract the full entry (usually includes course name, code, date, grade)
                entries.append({
                    "line_number": i + 1,
                    "content": line.strip()
                })

        return entries

    async def _generate_answer_node(self, state: AgentState) -> Dict[str, Any]:
        """Generate final answer using LLM.

        This node analyzes all gathered information and produces the final response.
        """
        step_num = len(state["agent_steps"]) + 1

        thinking_step = AgentStep(
            step_number=step_num,
            step_type="thought",
            content="Generating final answer based on gathered information"
        )

        try:
            # Build context from tool results
            # Priority: file_content > search_results (to save context space)
            context_parts = []
            enhanced_query = state["query"]

            if state.get("file_content"):
                # We have complete file content
                file_content = state["file_content"]
                filename = file_content.get("filename", "unknown")
                content = file_content.get("content", "")

                # Check if this is a year-specific query - if so, extract entries deterministically
                year_match = None
                for year in ["2024", "2023", "2022", "2021", "2020", "2019", "2018", "2017"]:
                    if year in state["query"]:
                        year_match = year
                        break

                if year_match:
                    # Extract all entries with that year programmatically
                    entries = self._extract_entries_by_year(content, year_match)

                    logger.info(f"Programmatically extracted {len(entries)} entries for year {year_match}")

                    # Build context with only the relevant entries
                    context_parts.append(f"Complete file: {filename}")
                    context_parts.append(f"Entries found for year {year_match}: {len(entries)}")
                    context_parts.append("\nMatching entries:")
                    for entry in entries:
                        context_parts.append(f"Line {entry['line_number']}: {entry['content']}")

                    # Simplified query for LLM - just format the data we found
                    enhanced_query = f"""The user asked: {state["query"]}

I have already searched the complete file and found {len(entries)} entries for year {year_match}.
Your task is to format this information in a clear, user-friendly response in Spanish.

Present all {len(entries)} entries in a numbered list with course name, code, date, and grade."""

                else:
                    # Not a year-specific query - send full content
                    context_parts.append(f"Complete file: {filename}")
                    context_parts.append(f"Content:\n{content}")

            elif state.get("search_results"):
                # Only have search results - include them
                search_results = state["search_results"]
                context_parts.append(f"Tool: search_documents")
                context_parts.append(f"Result: {search_results}")

            context = "\n\n".join(context_parts) if context_parts else "No information available."

            # Build instructions based on what data we have
            instructions = self._build_instructions(state)

            # Generate answer
            response = await self.llm_service.generate_with_context(
                prompt=enhanced_query,
                context=context,
                conversation_history=[],
                instructions=instructions
            )

            answer = response["response"]

            result_step = AgentStep(
                step_number=step_num + 1,
                step_type="result",
                content="Answer generated successfully"
            )

            return {
                "answer": answer,
                "agent_steps": [thinking_step, result_step]
            }

        except Exception as e:
            logger.error(f"Error in generate_answer_node: {e}")
            error_step = AgentStep(
                step_number=step_num + 1,
                step_type="error",
                content=f"Answer generation failed: {str(e)}"
            )
            return {
                "answer": f"I encountered an error while generating the answer: {str(e)}",
                "agent_steps": [thinking_step, error_step],
                "error": str(e)
            }

    def _build_instructions(self, state: AgentState) -> str:
        """Build context-aware instructions for the LLM.

        This provides different instructions depending on what data we have.
        """
        instructions = ""

        if state.get("file_content"):
            # We have complete file content
            instructions = """
**CRITICAL INSTRUCTION - COMPLETE FILE CONTENT AVAILABLE**:
You have access to the COMPLETE content of the file, not just search chunks.
You MUST read through the ENTIRE file content line by line and extract ALL matching entries.

**MANDATORY EXHAUSTIVE SEARCH**:
When the user asks for information from a specific year (e.g., 2024):
1. Scan through EVERY LINE of the file content provided
2. Find EVERY occurrence of dates containing that year (e.g., 'DD/MM/2024' or just '2024')
3. Extract the COMPLETE information for EACH matching entry (course name, code, date, grade)
4. Count how many entries you found and list ALL of them
5. DO NOT stop after finding just a few - continue searching until you've read the entire content

**DATE FORMAT**:
- Dates are in DD/MM/YYYY format (e.g., '19/12/2024' means December 19th, 2024)
- The year is the last 4 digits in the date
- Search for BOTH the full date pattern AND standalone year mentions

**VERIFICATION**:
After extracting all entries, verify:
- Did you read the entire file content?
- Did you check every line for the requested year?
- Are you confident you found ALL occurrences?

**ANTI-HALLUCINATION**:
Only report information explicitly present in the file content. If after thoroughly
searching the ENTIRE content you find no entries for the requested year, tell the user
honestly that no entries were found for that specific year.

**EXAMPLE FORMAT** (for grade queries):
"Encontré X materias del año 2024:
1. [Course name] ([code]) - [date] - [grade]%
2. [Course name] ([code]) - [date] - [grade]%
..."
"""
        elif state.get("search_results"):
            # Only have search chunks
            instructions = """
**PARTIAL INFORMATION**:
You only have search result chunks, not complete file content. Base your answer ONLY
on what you see in these chunks. Do NOT invent or extrapolate information.

If the information seems incomplete, tell the user that you only found partial
information.
"""
        else:
            # No data
            instructions = """
**NO INFORMATION FOUND**:
No relevant information was found in the documents. Tell the user honestly that you
could not find the requested information.
"""

        return instructions

    async def confirm_action(
        self,
        confirmation_id: str,
        approved: bool,
        user: UserInDB,
    ) -> AgentResponse:
        """Confirm or deny a pending tool execution.

        Note: In LangGraph architecture, confirmations would be handled differently,
        potentially as interrupts or human-in-the-loop nodes.
        """
        # TODO: Implement confirmation handling with LangGraph interrupts
        return AgentResponse(
            answer="Confirmation handling not yet implemented in LangGraph provider",
            is_complete=True
        )

    async def get_available_tools(self, user: UserInDB) -> List[Tool]:
        """Get list of tools available to the user.

        Returns:
            List of Tool definitions for the LangGraph agent
        """
        return [
            Tool(
                name="search_documents",
                description="Search through uploaded documents using RAG to find relevant information",
                parameters={"query": "Search query text"}
            ),
            Tool(
                name="read_file_content",
                description="Read the complete content of a specific file",
                parameters={"filename": "Name of the file to read"}
            )
        ]

    async def is_available(self) -> bool:
        """Check if the LangGraph agent provider is available.

        Returns:
            True if all required services are available, False otherwise
        """
        try:
            # Check if LLM service is available
            if not self.llm_service:
                return False

            # Check if RAG service is available
            if not self.rag_service:
                return False

            # Check if file service is available
            if not self.file_service:
                return False

            return True

        except Exception as e:
            logger.error(f"LangGraph provider availability check failed: {e}")
            return False
