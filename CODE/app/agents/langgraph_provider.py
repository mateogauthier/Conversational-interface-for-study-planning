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
from app.tools.http_executor import HTTPToolExecutor

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the agent workflow.

    LangGraph automatically manages this state across all nodes.
    """
    # User inputs
    query: str
    user: UserInDB
    conversation_id: Optional[str]
    language: Optional[str]  # Language preference for LLM responses

    # Tool execution results
    search_results: Optional[Dict[str, Any]]
    web_search_results: Optional[Dict[str, Any]]
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

        # Initialize HTTP tool executor for calling Agent API
        self.tool_executor = HTTPToolExecutor()

        # Build the workflow graph
        self.app = self._build_graph()

        logger.info("LangGraph agent provider initialized with deterministic routing and web search")

    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph.

        Graph structure:
        START -> classify_query -> route_initial?
                                 ├─> search_documents -> route_after_search?
                                 │                     ├─> web_search -> generate_answer -> END
                                 │                     └─> generate_answer -> END (chunks found)
                                 └─> generate_answer -> END (conversational queries)
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("classify_query", self._classify_query_node)
        workflow.add_node("search_documents", self._search_documents_node)
        workflow.add_node("web_search", self._web_search_node)
        workflow.add_node("generate_answer", self._generate_answer_node)

        # Set entry point to classification
        workflow.set_entry_point("classify_query")

        # Add initial routing after classification
        workflow.add_conditional_edges(
            "classify_query",
            self._route_initial,
            {
                "search": "search_documents",
                "generate": "generate_answer"
            }
        )

        # Add conditional routing after document search
        workflow.add_conditional_edges(
            "search_documents",
            self._route_after_search,
            {
                "web_search": "web_search",
                "generate": "generate_answer"
            }
        )

        # Connect web_search to generate_answer
        workflow.add_edge("web_search", "generate_answer")

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

            # Extract language preference from kwargs
            language = kwargs.get("language", "auto")  # Default to "auto" for Spanish detection

            # Initialize state
            initial_state: AgentState = {
                "query": query,
                "user": user,
                "conversation_id": conversation_id,
                "language": language,
                "search_results": None,
                "web_search_results": None,
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

    async def _classify_query_node(self, state: AgentState) -> Dict[str, Any]:
        """Classify the query to determine if tools are needed.

        This node detects conversational queries (greetings, thanks, casual chat)
        and skips tool execution entirely for better UX and performance.
        """
        step_num = len(state["agent_steps"]) + 1

        # Add classification step
        classification_step = AgentStep(
            step_number=step_num,
            step_type="thought",
            content="Analyzing query type to determine appropriate response strategy"
        )

        return {
            "agent_steps": [classification_step],
            "iteration": state["iteration"] + 1
        }

    def _route_initial(self, state: AgentState) -> str:
        """Route query based on classification.

        Conversational queries (greetings, thanks, casual chat) skip tools entirely.
        Informational queries proceed to search.

        Returns:
            "generate" for conversational queries, "search" for informational queries
        """
        query_lower = state["query"].lower().strip()

        # Conversational patterns (greetings, thanks, casual chat)
        conversational_patterns = [
            # Greetings (English and Spanish)
            "hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening",
            "hola", "buenos días", "buenas tardes", "buenas noches", "saludos", "qué tal",
            # Thanks
            "thank", "thanks", "gracias", "appreciate", "thank you", "muchas gracias",
            # Goodbyes
            "bye", "goodbye", "see you", "adiós", "hasta luego", "chao",
            # Casual
            "how are you", "what's up", "sup", "como estas", "cómo estás",
            "who are you", "what can you do", "quién eres", "qué puedes hacer",
            # Very short queries (likely conversational)
        ]

        # Check if query matches conversational patterns
        is_conversational = any(pattern in query_lower for pattern in conversational_patterns)

        # Also check if query is very short (1-3 words) and doesn't contain question indicators
        words = query_lower.split()
        question_indicators = ["what", "how", "why", "when", "where", "who", "which",
                              "qué", "cómo", "por qué", "cuándo", "dónde", "quién", "cuál"]
        is_short_without_question = (
            len(words) <= 3 and
            not any(word in words for word in question_indicators)
        )

        if is_conversational or is_short_without_question:
            logger.info(f"Conversational query detected - skipping tool execution: '{state['query']}'")
            return "generate"

        logger.info(f"Informational query detected - proceeding with tool execution: '{state['query']}'")
        return "search"

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

    def _route_after_search(self, state: AgentState) -> str:
        """Determine next step after initial search: web_search or generate.

        Intelligent routing based on query type and search results.

        Decision logic:
        1. Check if query explicitly needs web search (weather, news, current events, etc.)
        2. If document search found results -> generate answer with chunks (don't read full files)
        3. If NO documents found -> fallback to web search to try answering
        """
        query_lower = state["query"].lower()

        # Keywords that explicitly indicate web search is needed
        web_keywords = [
            # Current/realtime information
            "today", "now", "current", "latest", "recent", "breaking",
            # Weather
            "weather", "temperature", "forecast", "clima", "temperatura",
            # News
            "news", "noticias", "headlines",
            # Time-sensitive
            "happening", "trending", "this week", "this month",
            # External lookups
            "wikipedia", "definition", "what is", "who is", "when did",
            # Live data
            "stock", "price", "exchange rate", "cryptocurrency",
            # Location information
            "donde", "where", "ubicada", "ubicado", "located", "address", "dirección",
            "location", "ubicación", "lugar", "place", "how to get", "como llegar"
        ]

        # Check if query explicitly needs web search
        needs_web_search = any(keyword in query_lower for keyword in web_keywords)

        if needs_web_search:
            logger.info(f"Query requires web search: matched keywords")
            return "web_search"

        # Check document search results
        search_results = state.get("search_results")
        if search_results and search_results.get("n_chunks_found", 0) > 0:
            # Found relevant document chunks - use them directly (no need to read full file)
            logger.info(f"Found {search_results.get('n_chunks_found', 0)} document chunks - generating answer")
            return "generate"

        # NO documents found - fallback to web search
        # This allows the agent to try finding information on the web when documents don't have it
        logger.info(f"No relevant documents found - falling back to web search")
        return "web_search"

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

    async def _web_search_node(self, state: AgentState) -> Dict[str, Any]:
        """Execute web search using DuckDuckGo via Agent API.

        This node is called when the query requires real-time web information.
        """
        step_num = len(state["agent_steps"]) + 1

        thinking_step = AgentStep(
            step_number=step_num,
            step_type="thought",
            content="Searching the web for current information"
        )

        try:
            # Execute web search via Agent API
            tool_call_result = await self.tool_executor.execute(
                tool_name="web_search",
                parameters={
                    "query": state["query"],
                    "max_results": 5
                },
                user=state["user"]
            )

            # Add tool execution step
            tool_step = AgentStep(
                step_number=step_num + 1,
                step_type="tool_call",
                content="Executing web_search",
                tool_call=tool_call_result
            )

            # Extract results
            if tool_call_result.error:
                # Web search failed
                logger.warning(f"Web search failed: {tool_call_result.error}")
                result_step = AgentStep(
                    step_number=step_num + 2,
                    step_type="result",
                    content=f"Web search failed: {tool_call_result.error}",
                    tool_call=tool_call_result
                )

                return {
                    "web_search_results": {"results": [], "result_count": 0, "error": tool_call_result.error},
                    "agent_steps": [thinking_step, tool_step, result_step],
                    "tools_executed": ["web_search"]
                }

            # Web search succeeded
            web_results = tool_call_result.result
            result_count = web_results.get("result_count", 0)

            logger.info(f"Web search found {result_count} results")

            result_step = AgentStep(
                step_number=step_num + 2,
                step_type="result",
                content=f"Web search completed: {result_count} results found",
                tool_call=tool_call_result
            )

            return {
                "web_search_results": web_results,
                "agent_steps": [thinking_step, tool_step, result_step],
                "tools_executed": ["web_search"]
            }

        except Exception as e:
            logger.error(f"Error in web_search_node: {e}")
            error_step = AgentStep(
                step_number=step_num,
                step_type="error",
                content=f"Web search failed: {str(e)}"
            )
            return {
                "agent_steps": [thinking_step, error_step],
                "error": str(e),
                "web_search_results": {"results": [], "result_count": 0, "error": str(e)}
            }

    def _extract_entries_by_year(self, content: str, year: str) -> List[Dict[str, str]]:
        """Extract all entries from file content that contain the specified year.

        This is deterministic Python code - no LLM involved, so it finds EVERYTHING.
        Supports multiple date formats: DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD, YYYY/MM/DD
        """
        import re

        entries = []
        lines = content.split('\n')

        # Multiple date patterns to support various formats
        date_patterns = [
            rf'\d{{2}}/\d{{2}}/{year}',      # DD/MM/YYYY or MM/DD/YYYY
            rf'\d{{2}}-\d{{2}}-{year}',      # DD-MM-YYYY or MM-DD-YYYY
            rf'{year}/\d{{2}}/\d{{2}}',      # YYYY/MM/DD
            rf'{year}-\d{{2}}-\d{{2}}',      # YYYY-MM-DD
            rf'\b{year}\b'                    # Standalone year mention
        ]

        for i, line in enumerate(lines):
            # Check if any date pattern matches
            for pattern in date_patterns:
                if re.search(pattern, line):
                    entries.append({
                        "line_number": i + 1,
                        "content": line.strip()
                    })
                    break  # Don't add the same line multiple times

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
            # Priority: file_content > web_search_results > search_results
            context_parts = []
            enhanced_query = state["query"]

            # Check for web search results first (most specific/timely)
            if state.get("web_search_results") and state["web_search_results"].get("result_count", 0) > 0:
                web_results = state["web_search_results"]
                context_parts.append("Web Search Results:")
                for idx, result in enumerate(web_results.get("results", [])[:5], 1):
                    title = result.get("title", "No title")
                    snippet = result.get("snippet", "No description")
                    url = result.get("url", "")
                    context_parts.append(f"\n{idx}. {title}")
                    context_parts.append(f"   {snippet}")
                    if url:
                        context_parts.append(f"   Source: {url}")

                enhanced_query = f"""The user asked: {state["query"]}

I have searched the web and found {web_results.get("result_count", 0)} results.
Your task is to synthesize this information into a clear, helpful response.

If the search returned 0 results or encountered errors, explain that web search is temporarily unavailable but offer to help with other questions."""

            elif state.get("file_content"):
                # We have complete file content
                file_content = state["file_content"]
                filename = file_content.get("filename", "unknown")
                content = file_content.get("content", "")

                # Check if this is a year-specific query - if so, extract entries deterministically
                year_match = None
                import re
                # Look for 4-digit years in the query (e.g., 2024, 2023, etc.)
                year_pattern = r'\b(19\d{2}|20\d{2})\b'  # Matches years from 1900-2099
                year_matches = re.findall(year_pattern, state["query"])
                if year_matches:
                    year_match = year_matches[0]  # Use the first year found

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
Your task is to format this information in a clear, user-friendly response.

Present all {len(entries)} entries in a numbered list, preserving the information shown in each line."""

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
                instructions=instructions,
                language=state.get("language", "auto")
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
When the user asks for information from a specific time period (e.g., year, month, date range):
1. Scan through EVERY LINE of the file content provided
2. Find EVERY occurrence matching the user's criteria
3. Extract the COMPLETE information for EACH matching entry
4. Count how many entries you found and list ALL of them
5. DO NOT stop after finding just a few - continue searching until you've read the entire content

**DATE FORMAT DETECTION**:
- Automatically detect the date format used in the file (e.g., DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD)
- Extract dates accurately based on the detected format
- Search for BOTH full date patterns AND standalone time period mentions

**VERIFICATION**:
After extracting all entries, verify:
- Did you read the entire file content?
- Did you check every line for the requested criteria?
- Are you confident you found ALL occurrences?

**ANTI-HALLUCINATION**:
Only report information explicitly present in the file content. If after thoroughly
searching the ENTIRE content you find no entries matching the user's criteria, tell the user
honestly that no entries were found.

**RESPONSE FORMAT**:
Present results in a clear, numbered list format that:
- Shows the count of entries found
- Lists each entry with all its information
- Maintains the original information structure from the file
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
                name="web_search",
                description="Search the web using DuckDuckGo for current information not available in documents",
                parameters={"query": "Search query", "max_results": "Number of results (default: 5)"}
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
