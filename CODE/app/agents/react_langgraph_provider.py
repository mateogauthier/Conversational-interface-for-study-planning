"""ReAct-based LangGraph agent using create_react_agent."""

import asyncio
import logging
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.db.models import UserInDB
from app.tools.http_executor import HTTPToolExecutor
from app.agents.base import AgentProvider, AgentResponse, AgentStep
from app.agents.plan_generator import generate_study_plan

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
            format="",  # Explicitly disable JSON mode to allow tool calling
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

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. ALWAYS use tools to get student data - NEVER guess or make up information
2. When asked about student's courses, grades, or plans - YOU MUST call the appropriate tool
3. Do NOT ask clarifying questions if the query is clear - just call the tool
4. Only mention courses/data explicitly returned by tools
5. Always respond in the SAME LANGUAGE as the user's question

Examples:
- "What courses have I completed?" -> Call get_completed_courses immediately
- "What courses can I take?" -> Call get_available_courses immediately
- "Generate a study plan" -> Call create_study_plan immediately

Do not invent data - always use tool results. DO NOT respond without calling tools first when student data is needed."""

        # Create agent without checkpointing for now
        # TODO: Add persistent checkpointing for conversation memory
        logger.info(f"Creating ReAct agent with {len(tools)} tools for model {settings.ollama_model}")
        self.agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt
        )
        logger.info("ReAct agent created successfully")

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
        async def get_completed_courses() -> dict:
            """Get student's COMPLETED courses with final grades and GPA.

            Use this when the user asks about:
            - Completed courses, passed courses, finished courses
            - Final grades, marks, scores
            - GPA, grade point average, academic average
            - Which courses make up the GPA
            - Earned credits

            Returns ONLY courses that have been fully completed with final grades.
            These courses count toward GPA calculation.

            Returns:
                Dict with completed_courses list, total_credits_earned, gpa, course_count
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

            # Return only completed courses data
            data = result.result
            return {
                "completed_courses": data.get("schooling_records", []),
                "total_credits_earned": data.get("total_credits", 0),
                "gpa": data.get("gpa", 0.0),
                "course_count": len(data.get("schooling_records", []))
            }

        @tool
        async def get_current_courses() -> dict:
            """Get student's CURRENT in-progress courses (currently enrolled).

            Use this when the user asks about:
            - Current courses, ongoing courses, courses in progress
            - What they are currently taking or enrolled in
            - Active enrollments this semester

            Returns ONLY courses currently being taken.
            These do NOT have final grades yet and do NOT count toward current GPA.

            Returns:
                Dict with in_progress_courses list, course_count, note
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

            # Return only in-progress courses data
            data = result.result
            in_progress = data.get("in_progress_subjects", [])
            return {
                "in_progress_courses": in_progress,
                "course_count": len(in_progress),
                "note": "These courses do not yet have final grades and do not affect current GPA"
            }

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
            """Get the student's EXISTING study plan (read-only).

            Use this ONLY when the user asks to VIEW or SEE an already saved plan:
            - Show my plan, view my plan
            - What's my current plan, do I have a plan
            - View my schedule, see my schedule

            DO NOT use this to CREATE a new plan - use create_study_plan instead.

            Returns:
                Dict with existing study plan or empty if none exists
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

        @tool
        async def create_study_plan(
            target_graduation_semester: str = None,
            credits_per_semester_preference: int = 15,
            include_electives: bool = True,
            prioritize_early_graduation: bool = False
        ) -> dict:
            """Generate a NEW complete semester-by-semester study plan to graduation.

            Creates a detailed plan with specific courses for each future semester,
            ensuring all prerequisites are met and credit loads are realistic.

            Use this when user asks to CREATE, GENERATE, or MAKE a study plan for:
            - Future semesters, next year, next semester, remaining courses
            - Graduation planning, career planning
            - Study schedule creation

            Examples of when to use:
            - Create my study plan, generate a plan, make me a plan
            - Plan for next year, plan for next semester
            - When can I graduate, graduation timeline
            - Plan my remaining semesters, schedule my courses

            IMPORTANT:
            - Only uses real courses from the curriculum. Never invents courses.
            - This CREATES a new plan and saves it to the database.
            - User can then view it in the Study Plan tab of the UI.

            Args:
                target_graduation_semester: Target graduation (e.g., "2027-2") or None for auto
                credits_per_semester_preference: Preferred credits per semester (12-20, default 15)
                include_electives: Whether to include elective courses (default True)
                prioritize_early_graduation: Maximize credits to graduate faster (default False)

            Returns:
                Dict with complete study plan or error if generation fails
            """
            # Step 1: Get student's degree
            degree_result = await self.tool_executor.execute(
                tool_name="get_student_degree",
                parameters={},
                user=self._current_user
            )

            if degree_result.error:
                return {
                    "success": False,
                    "error": "Could not retrieve student degree",
                    "details": degree_result.error
                }

            degree_id = degree_result.result.get("degree_id")

            # Step 2: Fetch schooling and curriculum in parallel
            schooling_task = self.tool_executor.execute(
                tool_name="get_student_schooling",
                parameters={"student_id": str(self._current_user.id), "degree_id": degree_id},
                user=self._current_user
            )

            curriculum_task = self.tool_executor.execute(
                tool_name="get_degree_curriculum",
                parameters={"degree_id": degree_id},
                user=self._current_user
            )

            schooling_result, curriculum_result = await asyncio.gather(
                schooling_task, curriculum_task
            )

            if schooling_result.error:
                return {
                    "success": False,
                    "error": "Could not retrieve academic history",
                    "details": schooling_result.error
                }

            if curriculum_result.error:
                return {
                    "success": False,
                    "error": "Could not retrieve degree curriculum",
                    "details": curriculum_result.error
                }

            # Step 3: Transform schooling data to expected format
            # AGENT_API returns 'schooling_records' but plan_generator expects 'completed_subjects'
            schooling_data = schooling_result.result.copy()
            schooling_data["completed_subjects"] = schooling_data.pop("schooling_records", [])
            # in_progress_subjects is already correct
            # Add current_semester if not present
            if "current_semester" not in schooling_data:
                schooling_data["current_semester"] = "2025-1"

            # Step 4: Generate plan using pure Python algorithm
            plan_result = generate_study_plan(
                schooling=schooling_data,
                curriculum=curriculum_result.result,
                target_graduation=target_graduation_semester,
                credits_preference=credits_per_semester_preference,
                include_electives=include_electives,
                prioritize_early=prioritize_early_graduation
            )

            if not plan_result.get("success"):
                return plan_result

            # Step 5: Save plan to database
            update_result = await self.tool_executor.execute(
                tool_name="update_student_plan",
                parameters={
                    "student_id": self._current_user.auth0_id,
                    "degree_id": degree_id,
                    "plan_data": {
                        "semester_plans": plan_result["semester_plans"],
                        "plan_name": "AI-Generated Plan"
                    }
                },
                user=self._current_user
            )

            if update_result.error:
                return {
                    "success": False,
                    "error": f"Plan generated but failed to save: {update_result.error}",
                    "plan_details": plan_result
                }

            # Return complete result with plan details
            return {
                "success": True,
                "plan_created": True,
                "plan_saved": True,
                "degree_id": degree_id,
                "total_semesters": plan_result["total_semesters"],
                "total_remaining_credits": plan_result["total_remaining_credits"],
                "estimated_graduation": plan_result["estimated_graduation"],
                "semester_plans": plan_result["semester_plans"],
                "summary": plan_result["summary"],
                "warnings": plan_result.get("warnings", [])
            }

        return [
            search_documents,
            get_completed_courses,
            get_current_courses,
            get_available_courses,
            get_degree_curriculum,
            get_student_plan,
            web_search,
            create_study_plan,
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
                name="get_completed_courses",
                description="Get student's completed courses with final grades and GPA",
                parameters_schema={"type": "object", "properties": {}},
                safety=ToolSafety.SAFE
            ),
            Tool(
                name="get_current_courses",
                description="Get student's current in-progress courses (currently enrolled)",
                parameters_schema={"type": "object", "properties": {}},
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
