"""Instructor-enhanced ReAct agent with structured iterative reasoning.

This agent uses Instructor for structured planning and validation while leveraging
LangGraph's ReAct pattern for multi-tool iterative problem solving.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import instructor
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from enum import Enum

from app.db.models import UserInDB
from app.tools.http_executor import HTTPToolExecutor
from app.agents.base import AgentProvider, AgentResponse, AgentStep
from app.agents.react_langgraph_provider import ReActLangGraphProvider

logger = logging.getLogger(__name__)


class ReasoningStrategy(str, Enum):
    """Strategy for solving the user's query."""
    DIRECT_ANSWER = "direct_answer"  # Can answer without tools
    SINGLE_TOOL = "single_tool"  # Need one tool
    MULTI_TOOL_SEQUENTIAL = "multi_tool_sequential"  # Need multiple tools in sequence
    MULTI_TOOL_PARALLEL = "multi_tool_parallel"  # Need multiple tools in parallel
    ITERATIVE_REFINEMENT = "iterative_refinement"  # Need to iterate and refine


class ClarificationQuestion(BaseModel):
    """Question the agent needs answered before proceeding."""

    question: str = Field(description="The question to ask the user")
    reason: str = Field(description="Why this information is needed")
    options: Optional[List[str]] = Field(None, description="Suggested options if applicable")


class QueryPlan(BaseModel):
    """Structured plan for answering a user query."""

    user_intent: str = Field(
        description="What the user is trying to accomplish"
    )

    strategy: ReasoningStrategy = Field(
        description="Strategy to use for solving this query"
    )

    required_tools: List[str] = Field(
        default_factory=list,
        description="Tools needed to answer this query"
    )

    execution_steps: List[str] = Field(
        default_factory=list,
        description="Step-by-step plan for execution"
    )

    expected_challenges: List[str] = Field(
        default_factory=list,
        description="Potential issues or edge cases to watch for"
    )

    clarification_needed: Optional[ClarificationQuestion] = Field(
        None,
        description="Question to ask user before proceeding (if information is missing or ambiguous)"
    )

    can_answer_now: bool = Field(
        default=False,
        description="Whether we can answer without executing tools"
    )

    reasoning: str = Field(
        description="Detailed reasoning for this plan"
    )


class ToolResult(BaseModel):
    """Structured result from a tool execution."""

    tool_name: str = Field(description="Name of the tool executed")
    success: bool = Field(description="Whether execution succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the result (0-1)"
    )


class IterationResult(BaseModel):
    """Result of one reasoning iteration."""

    iteration_number: int = Field(description="Which iteration this is")

    findings: str = Field(
        description="What we learned in this iteration"
    )

    tools_used: List[ToolResult] = Field(
        default_factory=list,
        description="Tools executed in this iteration"
    )

    is_sufficient: bool = Field(
        default=False,
        description="Whether we have enough information to answer"
    )

    next_action: Optional[str] = Field(
        None,
        description="What to do next if not sufficient"
    )

    partial_answer: Optional[str] = Field(
        None,
        description="Partial answer based on current information"
    )


class FinalAnswer(BaseModel):
    """Structured final answer with validation."""

    answer: str = Field(
        description="The final answer to the user's query"
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in this answer (0-1)"
    )

    tools_used: List[str] = Field(
        default_factory=list,
        description="Tools that contributed to this answer"
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="Key pieces of evidence supporting this answer"
    )

    caveats: List[str] = Field(
        default_factory=list,
        description="Important caveats or limitations"
    )

    is_complete: bool = Field(
        default=True,
        description="Whether this answer is complete"
    )


class InstructorReActProvider(AgentProvider):
    """ReAct agent enhanced with Instructor for structured iterative reasoning."""

    def __init__(self, tool_executor: HTTPToolExecutor):
        self.tool_executor = tool_executor
        self.base_agent = ReActLangGraphProvider(tool_executor)
        self._current_user = None
        self.max_iterations = 5

    async def _create_planner(self, user: UserInDB):
        """Create Instructor client for structured planning."""
        from openai import AsyncOpenAI
        from app.core.config import get_settings

        settings = get_settings()

        # Use Ollama's OpenAI-compatible endpoint
        base_client = AsyncOpenAI(
            base_url=f"{settings.ollama_base_url}/v1",  # Ollama's OpenAI endpoint
            api_key="ollama"  # Dummy key - Ollama doesn't require auth
        )

        # Wrap with Instructor
        return instructor.from_openai(
            base_client,
            mode=instructor.Mode.JSON
        )

    async def _plan_query(self, query: str, user: UserInDB) -> QueryPlan:
        """Use Instructor to create a structured plan for the query."""

        client = await self._create_planner(user)

        planning_prompt = f"""You are an academic advisor planning how to help a student.

Available tools:
- search_documents: Search uploaded files
- get_completed_courses: Get completed courses with final grades and GPA
- get_current_courses: Get in-progress courses currently enrolled
- get_available_courses: Get enrollable courses (prerequisites validated)
- get_degree_curriculum: Get full degree curriculum
- get_student_plan: View existing saved study plan
- create_study_plan: Generate NEW study plan and save to database
- web_search: Search the web

Important distinctions:
- Use create_study_plan when user wants to GENERATE/CREATE a plan for future semesters
- Use get_student_plan when user wants to VIEW an existing saved plan
- Use get_completed_courses for GPA and past performance
- Use get_current_courses for ongoing enrollments

User query: "{query}"

Create a detailed plan for answering this query. Think step-by-step:
1. What is the user trying to accomplish?
2. What information do we need?
3. Which tools should we use and in what order?
4. What could go wrong?

IMPORTANT: If the query is ambiguous or missing critical information, set clarification_needed with a specific question to ask the user. For example:
- If user asks for "a study plan" but doesn't specify graduation date or credit preferences
- If user's intent could mean multiple different things
- If you need to know user preferences to give a good answer

Ask clarifying questions to provide the best possible help."""

        try:
            # Use Instructor to get structured plan
            from app.core.config import get_settings
            settings = get_settings()

            plan = await client.chat.completions.create(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": "You are a strategic planner. Output valid JSON."},
                    {"role": "user", "content": planning_prompt}
                ],
                response_model=QueryPlan,
                temperature=0.3
            )

            return plan

        except Exception as e:
            logger.warning(f"Structured planning failed, using fallback: {e}")
            # Fallback: simple plan
            return QueryPlan(
                user_intent=f"Answer: {query}",
                strategy=ReasoningStrategy.MULTI_TOOL_SEQUENTIAL,
                required_tools=["get_student_schooling"],
                execution_steps=["Execute available tools", "Synthesize answer"],
                expected_challenges=[],
                can_answer_now=False,
                reasoning="Fallback plan - execute tools and synthesize"
            )

    async def _execute_iteration(
        self,
        query: str,
        plan: QueryPlan,
        iteration: int,
        previous_results: List[IterationResult],
        user: UserInDB
    ) -> IterationResult:
        """Execute one iteration of the ReAct loop."""

        # Build context from previous iterations
        context = ""
        if previous_results:
            context = "\n\nPrevious findings:\n"
            for prev in previous_results:
                context += f"- Iteration {prev.iteration_number}: {prev.findings}\n"

        # Execute ReAct agent
        agent_response = await self.base_agent.execute_query(
            query=f"{query}\n\nPlan: {plan.reasoning}\nCurrent iteration: {iteration}{context}",
            user=user,
            conversation_id=f"instructor_{user.id}_{iteration}"
        )

        # Extract tools used
        tools_used = []
        for step in agent_response.agent_steps:
            if step.step_type == "tool_call":
                # Parse tool result from step content
                tools_used.append(ToolResult(
                    tool_name=step.content.split("Calling ")[1].split(" ")[0] if "Calling" in step.content else "unknown",
                    success=True,  # If it's in the steps, it executed
                    data={},
                    confidence=0.8
                ))

        return IterationResult(
            iteration_number=iteration,
            findings=agent_response.answer,
            tools_used=tools_used,
            is_sufficient=True,  # For now, assume one iteration is enough
            partial_answer=agent_response.answer
        )

    async def _validate_answer(
        self,
        query: str,
        iterations: List[IterationResult],
        user: UserInDB
    ) -> FinalAnswer:
        """Use Instructor to validate and structure the final answer."""

        client = await self._create_planner(user)

        # Compile all findings
        all_findings = "\n\n".join([
            f"Iteration {it.iteration_number}: {it.findings}"
            for it in iterations
        ])

        validation_prompt = f"""Review the findings and create a final answer.

Original query: "{query}"

Findings from agent execution:
{all_findings}

Create a complete, validated answer with:
1. Clear, direct answer
2. Confidence level (0-1)
3. Supporting evidence
4. Any important caveats

Be honest about confidence and limitations."""

        try:
            from app.core.config import get_settings
            settings = get_settings()

            final_answer = await client.chat.completions.create(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": "You are validating an answer. Output valid JSON."},
                    {"role": "user", "content": validation_prompt}
                ],
                response_model=FinalAnswer,
                temperature=0.2
            )

            return final_answer

        except Exception as e:
            logger.warning(f"Answer validation failed, using last iteration: {e}")
            # Fallback: use last iteration's answer
            last_iteration = iterations[-1] if iterations else None
            return FinalAnswer(
                answer=last_iteration.partial_answer if last_iteration else "Unable to generate answer",
                confidence=0.7,
                tools_used=[t.tool_name for it in iterations for t in it.tools_used],
                evidence=["Based on tool execution results"],
                caveats=["Answer validation failed - using direct agent output"],
                is_complete=True
            )

    async def execute_query(
        self,
        query: str,
        user: UserInDB,
        conversation_id: Optional[str] = None,
        auto_approve_tools: bool = False,
        **kwargs
    ) -> AgentResponse:
        """Execute query with structured iterative reasoning.

        Args:
            query: User's query or answer to a previous question
            user: User making the request
            conversation_id: Conversation ID
            auto_approve_tools: Whether to auto-approve tools
            **kwargs: Additional params including question_id and answer_to_question
        """

        self._current_user = user
        agent_steps = []
        iteration_results = []

        # Check if this is an answer to a previous question
        question_id = kwargs.get("question_id")
        answer_to_question = kwargs.get("answer_to_question")

        if question_id and answer_to_question:
            # User is providing an answer - incorporate it into the query
            original_query = kwargs.get("original_query", query)
            query = f"{original_query}\n\nUser provided additional information: {answer_to_question}"

            agent_steps.append(AgentStep(
                step_number=1,
                step_type="thought",
                content=f"✓ Received answer to clarification question: {answer_to_question}"
            ))

        try:
            # Step 1: Create structured plan using Instructor
            agent_steps.append(AgentStep(
                step_number=len(agent_steps) + 1,
                step_type="thought",
                content="📋 Creating structured plan for query..."
            ))

            plan = await self._plan_query(query, user)

            agent_steps.append(AgentStep(
                step_number=2,
                step_type="thought",
                content=f"✓ Plan created:\n- Intent: {plan.user_intent}\n- Strategy: {plan.strategy.value}\n- Required tools: {', '.join(plan.required_tools)}\n- Reasoning: {plan.reasoning}"
            ))

            # Check if clarification is needed
            if plan.clarification_needed:
                from app.agents.base import AgentQuestion
                import uuid

                question_id = str(uuid.uuid4())

                agent_steps.append(AgentStep(
                    step_number=len(agent_steps) + 1,
                    step_type="thought",
                    content=f"❓ Need clarification: {plan.clarification_needed.reason}"
                ))

                return AgentResponse(
                    answer=f"I need more information to help you better:\n\n{plan.clarification_needed.question}",
                    agent_steps=agent_steps,
                    pending_questions=[
                        AgentQuestion(
                            question_id=question_id,
                            question=plan.clarification_needed.question,
                            context=plan.clarification_needed.reason,
                            options=plan.clarification_needed.options,
                            is_required=True,
                            conversation_id=conversation_id or "unknown"
                        )
                    ],
                    requires_user_input=True,
                    is_complete=False,
                    iterations_completed=0,
                    conversation_id=conversation_id
                )

            # If we can answer directly, do it
            if plan.can_answer_now:
                agent_steps.append(AgentStep(
                    step_number=3,
                    step_type="answer",
                    content="Can answer directly without tools"
                ))

                return AgentResponse(
                    answer="Based on general knowledge, I can answer directly.",
                    agent_steps=agent_steps,
                    is_complete=True,
                    iterations_completed=0
                )

            # Step 2: Execute iterations
            for iteration in range(1, self.max_iterations + 1):
                agent_steps.append(AgentStep(
                    step_number=len(agent_steps) + 1,
                    step_type="thought",
                    content=f"🔄 Starting iteration {iteration}/{self.max_iterations}..."
                ))

                iteration_result = await self._execute_iteration(
                    query=query,
                    plan=plan,
                    iteration=iteration,
                    previous_results=iteration_results,
                    user=user
                )

                iteration_results.append(iteration_result)

                agent_steps.append(AgentStep(
                    step_number=len(agent_steps) + 1,
                    step_type="result",
                    content=f"✓ Iteration {iteration} complete:\n- Tools used: {', '.join([t.tool_name for t in iteration_result.tools_used])}\n- Findings: {iteration_result.findings[:200]}..."
                ))

                # Check if we have enough information
                if iteration_result.is_sufficient:
                    break

            # Step 3: Validate and structure final answer
            agent_steps.append(AgentStep(
                step_number=len(agent_steps) + 1,
                step_type="thought",
                content="✅ Validating final answer..."
            ))

            final_answer = await self._validate_answer(query, iteration_results, user)

            agent_steps.append(AgentStep(
                step_number=len(agent_steps) + 1,
                step_type="answer",
                content=f"Final answer (confidence: {final_answer.confidence:.0%})"
            ))

            # Build final response
            answer_text = final_answer.answer
            if final_answer.caveats:
                answer_text += "\n\n⚠️ Important notes:\n" + "\n".join([f"- {c}" for c in final_answer.caveats])

            return AgentResponse(
                answer=answer_text,
                agent_steps=agent_steps,
                tools_executed=final_answer.tools_used,
                is_complete=final_answer.is_complete,
                iterations_completed=len(iteration_results),
                max_iterations=self.max_iterations,
                conversation_id=conversation_id
            )

        except Exception as e:
            logger.error(f"Instructor ReAct agent error: {e}", exc_info=True)

            # Fallback to base ReAct agent
            agent_steps.append(AgentStep(
                step_number=len(agent_steps) + 1,
                step_type="error",
                content=f"Structured reasoning failed, falling back to base agent: {str(e)}"
            ))

            base_response = await self.base_agent.execute_query(
                query=query,
                user=user,
                conversation_id=conversation_id
            )

            # Merge steps
            base_response.agent_steps = agent_steps + base_response.agent_steps
            return base_response

    async def confirm_action(
        self,
        confirmation_id: str,
        approved: bool,
        user: UserInDB,
    ) -> AgentResponse:
        """Delegate to base agent."""
        return await self.base_agent.confirm_action(confirmation_id, approved, user)

    async def get_available_tools(self, user: UserInDB) -> list:
        """Delegate to base agent."""
        return await self.base_agent.get_available_tools(user)

    async def is_available(self) -> bool:
        """Check if provider is available."""
        return await self.base_agent.is_available()
