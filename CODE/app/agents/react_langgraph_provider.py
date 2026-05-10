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
        from langchain_openai import ChatOpenAI
        from app.core.config import get_settings

        settings = get_settings()
        # Use Ollama's OpenAI-compatible endpoint for reliable tool calling.
        # The native ChatOllama endpoint broke tool calling in Ollama 0.12.x.
        llm = ChatOpenAI(
            model=settings.ollama_model,
            base_url=f"{settings.ollama_base_url}/v1",
            api_key="ollama",
            temperature=0.7,
        )

        # Store user for tool access
        self._current_user = user

        # Create tools with user context
        tools = self._create_tools()

        # System prompt for academic advisor with conversation-first approach
        system_prompt = """You are a warm, empathetic academic advisor - like a career counselor who genuinely cares about students.

YOUR PERSONALITY:
- Friendly and conversational (like talking to a trusted friend)
- Empathetic and supportive (acknowledge feelings before problem-solving)
- Encouraging and positive (celebrate wins, offer hope during challenges)
- Patient and clear (explain complex prerequisites step-by-step)

CONVERSATION-FIRST APPROACH:

0. FOLLOW-UP RESPONSES - CHECK CONVERSATION HISTORY:
   - Short replies ("yes", "no", "ok", etc.) are responses to YOUR previous message
   - Look at what you last said and act accordingly
   - If you offered something and they agree, DO IT (call the appropriate tools)
   - If they decline, acknowledge and offer alternatives
   - NEVER treat a follow-up as a new conversation start

1. GREETINGS & SMALL TALK - NO TOOLS NEEDED:
   - "Hello", "Hi", "How are you", "Thank you", "Goodbye"
   - Respond warmly and ask what they need help with
   - Do NOT call tools for simple greetings

2. EMOTIONAL SUPPORT - EMPATHY FIRST, THEN TOOLS:
   - If student seems stressed/worried/overwhelmed:
     * Start: "I understand this feels overwhelming..."
     * Then: Call tools to provide practical help
   - If student is confused:
     * Start: "Let's break this down together..."
     * Then: Use tools + diagrams to clarify
   - If student is excited:
     * Start: "I love your enthusiasm!"
     * Then: Support their goals with data

3. INFORMATION QUERIES - USE TOOLS WITH NARRATIVE:
   - "What courses have I completed?" → Call get_completed_courses
   - BUT frame it: "Let me pull up your transcript... [tool results] → You've completed 8 courses with a 3.4 GPA - excellent work!"
   - NEVER say "Tool returned..." - integrate data naturally

4. PLANNING QUERIES - INTERACTIVE MULTI-TURN:
   - "Help me plan next semester"
   - Ask clarifying questions:
     * "What's your priority this semester - lighter workload or advancing quickly?"
     * "Any specific courses you're interested in?"
   - Present options, get confirmation, THEN use create_study_plan

5. REFLECTION QUERIES - NO NEW TOOLS:
   - "Why did you recommend this?"
   - Explain reasoning from previous tool calls
   - Show prerequisite logic, GPA considerations, etc.

RESPONSE STRUCTURE (ALWAYS FOLLOW):
1. ACKNOWLEDGMENT: "Great question!" / "I can help with that."
2. MAIN CONTENT: Tool results woven into natural explanation
3. CLOSING: Follow-up question OR encouragement OR next step

CRITICAL RULES:
- Respond in the SAME LANGUAGE as the user's question
- Use tools when needed, but prioritize conversation quality
- Never invent courses or data - only use tool results
- If you don't have data, say so clearly and offer alternatives

**INFORMATION RETRIEVAL STRATEGY:**

When answering questions, follow this priority:

1. **Academic Database FIRST** (Primary Source):
   - Student's transcript, GPA, progress (get_completed_courses, get_current_courses)
   - Course prerequisites and availability (get_available_courses)
   - Degree curriculum and requirements (get_degree_curriculum)
   - Study plans (get_student_plan, create_study_plan)

   Example: "What courses have I passed?" → get_completed_courses()
   Example: "What can I take next semester?" → get_available_courses()

2. **Uploaded Documents When Needed** (Supplementary Enhancement):
   Use search_documents to add detail when academic tools don't provide enough:
   - Course syllabi for topic breakdowns
   - Lecture notes for concept explanations
   - University policies not in curriculum database
   - Assignment details and grading criteria

   Example: "What topics are in Advanced AI?" → get_degree_curriculum() FIRST, then search_documents("Advanced AI syllabus") for details

3. **Web Search LAST** (External Information):
   - Information not in database or documents
   - Current events, job market, industry trends
   - Real-time information

   Example: "What's the current job market for CS?" → web_search("computer science job market 2024")

**Combining Sources for Best Answers:**
Often the best answers use academic data enhanced with document details:
- User: "Should I take Advanced AI next semester?"
  → get_available_courses() # Check if student can enroll (prerequisites)
  → get_completed_courses() # See what student has finished
  → search_documents("Advanced AI syllabus topics") # Get course details for decision
  → Synthesize: "You're eligible for Advanced AI since you've completed [prereqs from database]. Your GPA of [from transcript] shows you're prepared. The syllabus shows it covers [from documents], building on [courses you've taken]."
"""

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
            """Search uploaded documents using semantic search to enhance answers with supplementary details.

            Use this tool to ADD DETAIL when academic database tools don't provide enough information:
            - Course syllabi with detailed topic breakdowns
            - Lecture notes explaining specific concepts
            - University policies and regulations
            - Assignment details, grading criteria, or exam information
            - Study materials uploaded by the student

            This tool searches through:
            - Private files uploaded by the student (lecture notes, personal materials)
            - Public files uploaded by administrators (syllabi, university policies)

            Returns relevant text chunks with source filenames for citations.

            **When to use this tool:**
            - Student explicitly asks about syllabus, lecture notes, or uploaded materials
            - Academic tools (get_completed_courses, get_curriculum) provided the answer but more detail needed
            - Student needs specific examples or explanations from their materials
            - You want to cite sources from the student's own documents

            **When NOT to use this tool first:**
            - Questions about student's progress, GPA, or completed courses → use get_completed_courses
            - Questions about what courses to take or recommendations → use get_course_recommendations
            - Questions about degree requirements → use get_degree_curriculum

            Args:
                query: Search query describing what information you're looking for
                       (e.g., "Advanced AI syllabus topics", "grading policy", "midterm preparation")

            Returns:
                Dict with:
                - relevant_chunks: List of text chunks matching the query
                - sources: List of source filenames
                - count: Number of chunks found

            **Example Usage:**
            - User: "What topics are covered in Machine Learning?"
              → First: get_degree_curriculum() to see course info
              → Then: search_documents("Machine Learning syllabus topics") for detailed breakdown
            - User: "Show me my lecture notes on neural networks"
              → search_documents("neural networks lecture notes")
            - User: "What's the policy on late assignments?"
              → search_documents("late assignment policy")
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
                "gpa_scale": "0-100",
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
            """NEVER use this for course recommendations — use get_course_recommendations instead.

            Get the full list of courses the student can enroll in (prerequisite filtering only).
            Use this ONLY when the user explicitly asks to see ALL available/eligible courses:
            - "What can I enroll in?"
            - "List available courses"
            - "Which courses have I met the prerequisites for?"

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

        @tool
        async def get_student_profile_summary() -> dict:
            """Get a comprehensive summary of the student's academic profile.

            Use this when the student asks broad questions like:
            - "How am I doing?" / "How's my progress?"
            - "Where am I in my degree?"
            - "Give me a summary of my academic progress"
            - "What's my overall status?"

            Returns:
                Dict with GPA, completed credits, in-progress courses, strengths, summary
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

            # Get schooling and curriculum in parallel
            schooling_result = await self.tool_executor.execute(
                tool_name="get_student_schooling",
                parameters={
                    "student_id": str(self._current_user.id),
                    "degree_id": degree_id
                },
                user=self._current_user
            )

            curriculum_result = await self.tool_executor.execute(
                tool_name="get_degree_curriculum",
                parameters={"degree_id": degree_id},
                user=self._current_user
            )

            if schooling_result.error or curriculum_result.error:
                return {"error": "Could not retrieve academic data"}

            # Calculate summary statistics
            schooling = schooling_result.result
            curriculum = curriculum_result.result

            completed_courses = schooling.get("schooling_records", [])
            in_progress_courses = schooling.get("in_progress_subjects", [])
            gpa = schooling.get("gpa", 0.0)
            total_credits_earned = schooling.get("total_credits", 0)

            # Use degree's defined total credits
            total_required_credits = curriculum.get("total_credits", 0)
            if total_required_credits == 0:
                total_required_credits = sum(
                    sum(course.get("credits", 0) for course in semester.get("subjects", []))
                    for semester in curriculum.get("curriculum", [])
                )

            remaining_credits = total_required_credits - total_credits_earned
            progress_percentage = (total_credits_earned / total_required_credits * 100) if total_required_credits > 0 else 0

            # Find strongest areas (courses with highest grades)
            graded_courses = [c for c in completed_courses if c.get("grade") is not None]
            if graded_courses:
                graded_courses.sort(key=lambda x: x.get("grade", 0), reverse=True)
                top_courses = graded_courses[:3]
                strengths = [c.get("subject_name", c.get("subject_id")) for c in top_courses]
            else:
                strengths = []

            return {
                "gpa": round(gpa, 2),
                "gpa_scale": "0-100",
                "completed_credits": total_credits_earned,
                "remaining_credits": remaining_credits,
                "total_required_credits": total_required_credits,
                "progress_percentage": round(progress_percentage, 1),
                "completed_courses_count": len(completed_courses),
                "in_progress_courses_count": len(in_progress_courses),
                "in_progress_courses": [c.get("subject_name", c.get("subject_id")) for c in in_progress_courses],
                "strengths": strengths,
                "summary": f"Completed {total_credits_earned}/{total_required_credits} credits ({progress_percentage:.1f}% of degree)"
            }

        @tool
        async def save_student_goal(goal_text: str, category: str = "general") -> dict:
            """Save a student's stated goal or career interest for future reference.

            Use when student mentions future aspirations or goals:
            - Career interests: "I want to work in data science"
            - Academic goals: "I want to graduate by 2026"
            - Personal goals: "I want to study abroad"
            - Skill development: "I want to learn machine learning"

            Args:
                goal_text: The goal statement
                category: Goal category - "career", "academic", "personal", or "general"

            Returns:
                Confirmation that goal was saved
            """
            # Note: This will be stored in conversation metadata
            # For now, return confirmation. Future: integrate with conversation service
            return {
                "success": True,
                "goal_saved": goal_text,
                "category": category,
                "message": f"I've noted your {category} goal: '{goal_text}'. I'll keep this in mind as we plan your path forward!"
            }

        @tool
        async def get_course_recommendations(algorithm: str = "all") -> dict:
            """Get personalized course recommendations using multiple ML algorithms.

            ALWAYS use this tool when the student asks for recommendations, suggestions,
            or advice on what courses to take. This includes:
            - "What do you recommend?" / "que me recomiendas?"
            - "What should I take next?" / "que deberia cursar?"
            - "Which courses should I enroll in?" / "a que materias me inscribo?"
            - "Help me choose courses" / "ayudame a elegir materias"
            - "What are the best courses for me?"
            - Any question about course recommendations, suggestions, or prioritization

            This tool runs 3 different ML algorithms and returns combined results:
            - Random Forest: Predicts pass probability using student history and course difficulty
            - Sequential Pattern Mining: Discovers common course sequences from successful students
            - Pattern Mining: Finds similar students and recommends what they took next

            Synthesize the results: when multiple algorithms agree on a course, highlight it
            as a strong recommendation. When they disagree, mention the different perspectives.

            Returns:
                Dict with recommendations from each algorithm for synthesis
            """
            degree_id = "LIC-SIS-2019"

            result = await self.tool_executor.execute(
                tool_name="get_course_recommendations",
                parameters={"degree_id": degree_id, "algorithm": "all"},
                user=self._current_user
            )

            if result.error:
                return {"error": result.error}

            data = result.result
            recommendations = data.get("recommendations", {})
            algorithms_used = data.get("algorithms_used")

            if algorithms_used:
                # Compact text format — raw JSON overwhelms the 8B model
                lines = []
                for algo_name in algorithms_used:
                    algo_recs = recommendations.get(algo_name, [])
                    top = algo_recs[:5]  # Top 5 per algorithm
                    lines.append(f"\n## {algo_name}")
                    for r in top:
                        name = r.get("subject_name", r.get("subject_id", "?"))
                        score = r.get("final_score", 0)
                        core = " [CORE]" if r.get("is_core") else ""
                        lines.append(f"- {name} (score: {score}){core}")

                return {
                    "summary": "\n".join(lines),
                    "note": "Courses in multiple algorithms = strong recommendation. [CORE] = required.",
                }

            # Single algorithm fallback
            recs_list = recommendations if isinstance(recommendations, list) else []
            top = recs_list[:5]
            lines = []
            for r in top:
                name = r.get("subject_name", r.get("subject_id", "?"))
                score = r.get("final_score", 0)
                core = " [CORE]" if r.get("is_core") else ""
                lines.append(f"- {name} (score: {score}){core}")

            return {
                "summary": "\n".join(lines),
                "note": "Higher score = stronger recommendation. [CORE] = required.",
            }

        return [
            search_documents,
            get_completed_courses,
            get_current_courses,
            get_course_recommendations,
            get_available_courses,
            get_degree_curriculum,
            get_student_plan,
            web_search,
            create_study_plan,
            get_student_profile_summary,
            save_student_goal,
        ]

    def _detect_followup(
        self, query: str, conversation_history: Optional[list]
    ) -> Optional[str]:
        """Detect if a short query is a follow-up to a previous assistant message.

        Returns an enhanced query with context, or None if not a follow-up.
        """
        if not conversation_history or len(conversation_history) < 2:
            return None

        # Only enhance short messages (likely responses, not new queries)
        if len(query.split()) > 5:
            return None

        # Get the last assistant message
        last_assistant = None
        for msg in reversed(conversation_history):
            if msg["role"] == "assistant":
                last_assistant = msg["content"]
                break

        if not last_assistant:
            return None

        # Truncate to last 500 chars to keep context manageable
        context_snippet = last_assistant[-500:]

        return (
            f'The student responded: "{query}"\n\n'
            f"This is a follow-up to your previous message which ended with:\n"
            f'"""{context_snippet}"""\n\n'
            f"Interpret their response in the context of what you previously said. "
            f"If they are agreeing, follow through on what you offered. "
            f"If they are declining, acknowledge and offer alternatives. "
            f"If they are asking for clarification, clarify."
        )

    def _detect_emotional_context(self, query: str) -> Optional[str]:
        """Detect emotional context from query keywords."""
        query_lower = query.lower()

        stress_keywords = ['overwhelmed', 'stressed', 'worried', 'anxious', 'too much', 'can\'t handle']
        confusion_keywords = ['confused', 'lost', 'don\'t understand', 'don\'t get', 'unclear']
        excitement_keywords = ['excited', 'can\'t wait', 'looking forward', 'thrilled']

        if any(keyword in query_lower for keyword in stress_keywords):
            return "stressed"
        elif any(keyword in query_lower for keyword in confusion_keywords):
            return "confused"
        elif any(keyword in query_lower for keyword in excitement_keywords):
            return "excited"

        return None

    async def execute_query(
        self,
        query: str,
        user: UserInDB,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Process user query using ReAct agent with conversation-first approach."""

        # Extract language parameter
        language = kwargs.get("language")

        # Detect follow-up responses and enhance with context
        followup_enhanced = self._detect_followup(query, conversation_history)
        if followup_enhanced:
            enhanced_query = followup_enhanced
            logger.info("Detected short follow-up response, enhancing with context")
        else:
            enhanced_query = query

        # Detect emotional context for better conversation handling
        emotional_context = self._detect_emotional_context(query)
        if emotional_context:
            logger.info(f"Detected emotional context: {emotional_context}")

        # Initialize agent with user context
        await self._initialize_agent(user)

        # Add language instruction to query if specified
        if language:
            if language == "spanish":
                enhanced_query = f"{enhanced_query}\n\n[IMPORTANT: Respond in Spanish]"
            elif language == "english":
                enhanced_query = f"{enhanced_query}\n\n[IMPORTANT: Respond in English]"
            logger.info(f"Language specified: {language}")

        # Configure thread for conversation persistence
        config = {
            "configurable": {
                "thread_id": conversation_id or str(user.id)
            }
        }

        # Execute agent
        try:
            # Build message list with conversation history
            messages = []
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            messages.append(HumanMessage(content=enhanced_query))

            result = await self.agent.ainvoke(
                {"messages": messages},
                config=config
            )

            # Extract answer from last AI message
            messages = result.get("messages", [])
            logger.info(f"[DEBUG] Agent returned {len(messages)} messages")
            for _dbg_msg in messages:
                logger.info(f"[DEBUG] msg type={type(_dbg_msg).__name__} tool_calls={getattr(_dbg_msg, 'tool_calls', [])} content_preview={repr((_dbg_msg.content or '')[:80])}")
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
