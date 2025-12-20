"""ReAct-based LangGraph agent using create_react_agent."""

import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.db.models import UserInDB
from app.tools.http_executor import HTTPToolExecutor
from app.agents.base import AgentProvider, AgentResponse, AgentStep

logger = logging.getLogger(__name__)


class ReActLangGraphProvider(AgentProvider):
    """ReAct agent using LangGraph's create_react_agent."""

    def __init__(self, tool_executor: HTTPToolExecutor):
        self.tool_executor = tool_executor
        self.agent = None
        self._current_user = None  # Store user context for tools

    async def _initialize_agent(self, user: UserInDB):
        """Initialize agent with tools bound to current user."""
        from langchain_ollama import ChatOllama
        from app.core.config import get_settings

        settings = get_settings()
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.7,
        )

        # Store user for tool access
        self._current_user = user

        # Create tools with user context
        tools = self._create_tools()

        # System prompt for academic advisor
        system_prompt = """You are a friendly academic advisor assistant.

Your capabilities:
- Search uploaded documents for course materials and information
- Access student's academic records (completed courses, grades, GPA)
- Check available courses for enrollment (with prerequisite validation)
- View degree curriculum and requirements
- Search the web for current information
- Provide study planning recommendations

Guidelines:
- Always respond in the SAME LANGUAGE as the user's question
- Use tools to get accurate information before answering
- Only mention courses/data explicitly returned by tools
- Be conversational, helpful, and supportive
- If prerequisites are mentioned, they have been validated by the system

Do not invent data - always use tool results."""

        # Create agent without checkpointing for now
        # TODO: Add persistent checkpointing for conversation memory
        self.agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt
        )

    def _create_tools(self):
        """Create LangChain tools with access to user context."""

        @tool
        async def search_documents(query: str) -> dict:
            """Search uploaded documents for relevant information.

            Use this when the user asks about course materials, uploaded files,
            or content from their documents.

            Args:
                query: Search query describing what to look for

            Returns:
                Dict with search results including file names and relevant chunks
            """
            result = await self.tool_executor.execute(
                tool_name="search_documents",
                parameters={"query": query},
                user=self._current_user
            )

            if result.error:
                return {"error": result.error}

            return result.result

        @tool
        async def get_student_schooling(include_gpa: bool = True) -> dict:
            """Get student's academic transcript with completed courses and grades.

            Use this when the user asks about:
            - "What courses am I taking?" / "que materias estoy cursando?"
            - "What have I completed?" / "materias completadas"
            - "My grades" / "mis calificaciones"
            - "My GPA" / "mi promedio"
            - "My academic record" / "mi historial académico"

            Returns:
                Dict with completed_courses, in_progress_courses, total_credits, and GPA
            """
            # Get student degree first
            degree_result = await self.tool_executor.execute(
                tool_name="get_student_degree",
                parameters={},
                user=self._current_user
            )

            if degree_result.error:
                return {"error": "Could not retrieve student degree"}

            degree_id = degree_result.result.get("degree_id")
            if not degree_id:
                return {"error": "Student not enrolled in a degree program"}

            # Get schooling records
            result = await self.tool_executor.execute(
                tool_name="get_student_schooling",
                parameters={
                    "student_id": str(self._current_user.id),
                    "degree_id": degree_id
                },
                user=self._current_user
            )

            if result.error:
                return {"error": result.error}

            return result.result

        @tool
        async def get_available_courses() -> dict:
            """Get courses the student can enroll in with prerequisites validated.

            Use this when the user asks about:
            - "What can I enroll in?" / "a que materias puedo inscribirme?"
            - "Available courses" / "materias disponibles"
            - "What should I take next?" / "que debería inscribir?"
            - "Recommendations" / "recomendaciones"

            Returns:
                Dict with available courses (prerequisites already checked)
            """
            # Get degree ID
            degree_result = await self.tool_executor.execute(
                tool_name="get_student_degree",
                parameters={},
                user=self._current_user
            )

            if degree_result.error:
                return {"error": "Could not retrieve student degree"}

            degree_id = degree_result.result.get("degree_id")

            # Get both curriculum and schooling
            curriculum_result = await self.tool_executor.execute(
                tool_name="get_degree_curriculum",
                parameters={"degree_id": degree_id},
                user=self._current_user
            )

            schooling_result = await self.tool_executor.execute(
                tool_name="get_student_schooling",
                parameters={
                    "student_id": str(self._current_user.id),
                    "degree_id": degree_id
                },
                user=self._current_user
            )

            if curriculum_result.error or schooling_result.error:
                return {"error": "Could not retrieve course information"}

            # Filter available courses (Python-based validation)
            curriculum = curriculum_result.result.get("curriculum", [])
            schooling = schooling_result.result

            completed_ids = {
                c["subject_id"]
                for c in schooling.get("schooling_records", [])
            }
            in_progress_ids = {
                c["subject_id"]
                for c in schooling.get("in_progress_subjects", [])
            }

            available = []
            for semester_data in curriculum:
                for course in semester_data.get("subjects", []):
                    course_id = course["subject_id"]
                    prereqs = course.get("prerequisites", [])

                    # Skip completed or in-progress
                    if course_id in completed_ids or course_id in in_progress_ids:
                        continue

                    # Check prerequisites
                    missing_prereqs = [p for p in prereqs if p not in completed_ids]
                    if missing_prereqs:
                        continue

                    # Available!
                    available.append({
                        "subject_id": course_id,
                        "name": course.get("name", course_id),
                        "credits": course.get("credits", 0),
                        "prerequisites": prereqs,
                        "semester": semester_data.get("semester")
                    })

            return {
                "available_courses": available,
                "total_available": len(available),
                "completed_count": len(completed_ids),
                "in_progress_count": len(in_progress_ids)
            }

        @tool
        async def get_degree_curriculum(include_all_details: bool = False) -> dict:
            """Get the full degree curriculum with all courses and requirements.

            Use this when the user asks about:
            - "Curriculum" / "plan de estudios"
            - "Degree requirements" / "requisitos de la carrera"
            - "What's in my degree?" / "que incluye mi carrera?"
            - "Show curriculum" / "ver malla curricular"

            Returns:
                Dict with complete curriculum organized by semester
            """
            # Get degree ID
            degree_result = await self.tool_executor.execute(
                tool_name="get_student_degree",
                parameters={},
                user=self._current_user
            )

            if degree_result.error:
                return {"error": "Could not retrieve student degree"}

            degree_id = degree_result.result.get("degree_id")

            result = await self.tool_executor.execute(
                tool_name="get_degree_curriculum",
                parameters={"degree_id": degree_id},
                user=self._current_user
            )

            if result.error:
                return {"error": result.error}

            return result.result

        @tool
        async def get_student_plan() -> dict:
            """Get the student's personalized study plan.

            Use this when the user asks about:
            - "My study plan" / "mi plan de estudios"
            - "Semester schedule" / "horario del semestre"
            - "My plan" / "mi planificación"

            Returns:
                Dict with personalized study plan
            """
            result = await self.tool_executor.execute(
                tool_name="get_student_plan",
                parameters={"student_id": str(self._current_user.id)},
                user=self._current_user
            )

            if result.error:
                return {"error": result.error}

            return result.result

        @tool
        async def web_search(query: str) -> dict:
            """Search the web for current information.

            Use this when the user asks about:
            - Current events, news, weather
            - Information not in uploaded documents
            - Real-time data

            Args:
                query: Search query

            Returns:
                Dict with search results
            """
            result = await self.tool_executor.execute(
                tool_name="web_search",
                parameters={"query": query},
                user=self._current_user
            )

            if result.error:
                return {"error": result.error}

            return result.result

        return [
            search_documents,
            get_student_schooling,
            get_available_courses,
            get_degree_curriculum,
            get_student_plan,
            web_search,
        ]

    async def execute_query(
        self,
        query: str,
        user: UserInDB,
        conversation_id: Optional[str] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Process user query using ReAct agent."""

        # Initialize agent with user context
        await self._initialize_agent(user)

        # Configure thread for conversation persistence
        config = {
            "configurable": {
                "thread_id": conversation_id or str(user.id)
            }
        }

        # Execute agent
        try:
            result = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=query)]},
                config=config
            )

            # Extract answer from last AI message
            messages = result.get("messages", [])
            answer = ""
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    answer = msg.content
                    break

            # Build agent steps from message history
            agent_steps = []
            step_num = 1

            for msg in messages:
                if isinstance(msg, HumanMessage):
                    agent_steps.append(AgentStep(
                        step_number=step_num,
                        step_type="user_query",
                        content=msg.content
                    ))
                    step_num += 1
                elif isinstance(msg, AIMessage):
                    # Check if tool calls were made
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            agent_steps.append(AgentStep(
                                step_number=step_num,
                                step_type="tool_call",
                                content=f"Calling {tool_call.get('name', 'tool')} with args: {tool_call.get('args', {})}"
                            ))
                            step_num += 1
                    else:
                        agent_steps.append(AgentStep(
                            step_number=step_num,
                            step_type="answer",
                            content=msg.content
                        ))
                        step_num += 1

            return AgentResponse(
                answer=answer,
                agent_steps=agent_steps,
                conversation_id=conversation_id
            )

        except Exception as e:
            logger.error(f"ReAct agent error: {e}")
            return AgentResponse(
                answer=f"I encountered an error processing your request: {str(e)}",
                agent_steps=[
                    AgentStep(
                        step_number=1,
                        step_type="error",
                        content=str(e)
                    )
                ],
                conversation_id=conversation_id
            )

    async def confirm_action(
        self,
        confirmation_id: str,
        approved: bool,
        user: UserInDB,
    ) -> AgentResponse:
        """ReAct agent doesn't use confirmations - tools execute automatically."""
        return AgentResponse(
            answer="ReAct agent does not support manual confirmation - all tool calls execute automatically.",
            agent_steps=[],
            is_complete=True
        )

    async def get_available_tools(self, user: UserInDB) -> list:
        """Get list of tools available to the user."""
        # Return tool descriptions
        from app.agents.base import Tool, ToolSafety

        tools = [
            Tool(
                name="search_documents",
                description="Search uploaded documents for relevant information",
                parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                safety=ToolSafety.SAFE
            ),
            Tool(
                name="get_student_schooling",
                description="Get student's academic transcript with completed courses and grades",
                parameters_schema={"type": "object", "properties": {"include_gpa": {"type": "boolean"}}},
                safety=ToolSafety.SAFE
            ),
            Tool(
                name="get_available_courses",
                description="Get courses the student can enroll in with prerequisites validated",
                parameters_schema={"type": "object", "properties": {}},
                safety=ToolSafety.SAFE
            ),
            Tool(
                name="get_degree_curriculum",
                description="Get the full degree curriculum with all courses and requirements",
                parameters_schema={"type": "object", "properties": {"include_all_details": {"type": "boolean"}}},
                safety=ToolSafety.SAFE
            ),
            Tool(
                name="get_student_plan",
                description="Get the student's personalized study plan",
                parameters_schema={"type": "object", "properties": {}},
                safety=ToolSafety.SAFE
            ),
            Tool(
                name="web_search",
                description="Search the web for current information",
                parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                safety=ToolSafety.SAFE
            ),
        ]
        return tools

    async def is_available(self) -> bool:
        """Check if the ReAct agent provider is available."""
        return True  # Always available since it uses in-memory checkpointing
