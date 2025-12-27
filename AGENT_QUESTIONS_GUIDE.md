# Agent Interactive Questions Feature

## Overview

The Instructor agent can now ask clarifying questions during its reasoning process to gather missing information from the user. This enables more accurate and personalized responses.

## How It Works

### 1. Agent Asks a Question

When the agent detects that the user's query is ambiguous or missing critical information, it will:

1. **Pause execution** before running any tools
2. **Create a clarification question** with context
3. **Return the question** to the user instead of a final answer

Example scenarios:
- User asks "create a study plan" but doesn't specify graduation date or credit preferences
- User's request could mean multiple things
- Agent needs user preferences to provide the best answer

### 2. User Provides Answer

The user responds with their answer, which is sent back to the agent along with:
- `question_id`: The ID of the question being answered
- `answer_to_question`: The user's response
- Original query context

### 3. Agent Continues with Answer

The agent:
1. Incorporates the user's answer into its planning
2. Continues execution with the additional information
3. Provides a complete, personalized response

## API Usage

### Request Format

```json
POST /agent/query
{
  "prompt": "create a study plan",
  "conversation_id": "abc123",
  "enable_agent": true
}
```

### Response with Question

```json
{
  "answer": "I need more information to help you better:\n\nWhen would you like to graduate?",
  "pending_questions": [
    {
      "question_id": "uuid-here",
      "question": "When would you like to graduate?",
      "context": "Need graduation timeline to create realistic semester plans",
      "options": ["2026-1", "2026-2", "2027-1", "2027-2"],
      "is_required": true,
      "conversation_id": "abc123"
    }
  ],
  "requires_user_input": true,
  "is_complete": false,
  "agent_steps": [
    {
      "step_type": "thought",
      "content": "📋 Creating structured plan for query..."
    },
    {
      "step_type": "thought",
      "content": "❓ Need clarification: Need graduation timeline to create realistic semester plans"
    }
  ]
}
```

### Answering the Question

```json
POST /agent/query
{
  "prompt": "create a study plan",
  "conversation_id": "abc123",
  "question_id": "uuid-here",
  "answer_to_question": "2027-1",
  "enable_agent": true
}
```

### Final Response

```json
{
  "answer": "Based on your target graduation of 2027-1, here's your personalized study plan:\n\n...",
  "is_complete": true,
  "requires_user_input": false,
  "agent_steps": [
    {
      "step_type": "thought",
      "content": "✓ Received answer to clarification question: 2027-1"
    },
    {
      "step_type": "thought",
      "content": "📋 Creating structured plan for query..."
    }
  ]
}
```

## Configuration

The questioning behavior is controlled by the Instructor agent's planning prompt. The agent will ask questions when:

1. **Query is ambiguous**: Multiple valid interpretations exist
2. **Missing critical parameters**: e.g., graduation date, credit preferences
3. **Need user preferences**: Personalization requires user input

## Question Types

### Open-Ended Questions
```json
{
  "question": "What is your target graduation date?",
  "options": null
}
```

### Multiple Choice Questions
```json
{
  "question": "How many credits do you prefer per semester?",
  "options": ["12 credits (light load)", "15 credits (standard)", "18 credits (heavy load)"]
}
```

## Frontend Integration

The frontend should:

1. **Detect `requires_user_input: true`** in the response
2. **Display the question** from `pending_questions[0].question`
3. **Show context** from `pending_questions[0].context`
4. **Render options** if provided (as buttons or dropdown)
5. **Submit answer** with `question_id` and `answer_to_question`

Example UI flow:
```
User: "create a study plan"
Agent: "When would you like to graduate?"
      [ 2026-1 ] [ 2026-2 ] [ 2027-1 ] [ 2027-2 ]

User clicks: "2027-1"
Agent: "Here's your study plan for graduation in 2027-1..."
```

## Technical Implementation

### Data Models

**ClarificationQuestion** (Pydantic model used internally):
```python
class ClarificationQuestion(BaseModel):
    question: str  # The question to ask
    reason: str    # Why this info is needed
    options: Optional[List[str]]  # Suggested options
```

**AgentQuestion** (API response model):
```python
class AgentQuestion(BaseModel):
    question_id: str
    question: str
    context: str
    options: Optional[List[str]]
    is_required: bool
    conversation_id: str
```

**QueryPlan** (updated to include clarification):
```python
class QueryPlan(BaseModel):
    user_intent: str
    strategy: ReasoningStrategy
    required_tools: List[str]
    clarification_needed: Optional[ClarificationQuestion]  # New field
    can_answer_now: bool
    reasoning: str
```

### Agent Logic

1. **Planning Phase**: LLM determines if clarification is needed
2. **If clarification needed**: Return question, set `is_complete=False`
3. **If answer provided**: Merge answer into query, continue execution
4. **If no clarification needed**: Execute tools as normal

## Examples

### Example 1: Study Plan Creation

**Query**: "create a study plan"

**Agent Response** (question):
```json
{
  "pending_questions": [{
    "question": "When would you like to graduate?",
    "context": "Need target graduation date to create a realistic semester-by-semester plan",
    "options": ["2026-1", "2026-2", "2027-1", "2027-2"]
  }],
  "requires_user_input": true
}
```

**User Answer**: "2027-1"

**Agent Response** (final):
```
Based on your target graduation of 2027-1, here's your study plan:

Semester 2025-1:
- FIS102: Física II
- CHEM101: Química
- ARCH101: Arquitectura de Computadoras

Semester 2025-2:
...
```

### Example 2: Credit Load Preference

**Query**: "plan my remaining courses"

**Agent Response** (question):
```json
{
  "pending_questions": [{
    "question": "How many credits per semester do you prefer?",
    "context": "Credit load affects graduation timeline and workload balance",
    "options": [
      "12 credits (light load, balanced life)",
      "15 credits (standard load)",
      "18 credits (heavy load, faster graduation)"
    ]
  }]
}
```

**User Answer**: "15 credits (standard load)"

**Agent Response** (final):
```
Based on a standard 15-credit load, you'll graduate in 2027-2...
```

## Benefits

1. **Better Accuracy**: Agent gets exactly the information it needs
2. **User Control**: Users provide preferences rather than agent guessing
3. **Transparency**: Users see why information is needed (context field)
4. **Flexibility**: Works for any type of clarification (dates, preferences, choices)
5. **Conversation Flow**: Maintains context across question/answer cycles

## Limitations

- Currently only one question at a time (no multi-question forms)
- Questions are generated by LLM, quality depends on prompt engineering
- Frontend must implement UI for displaying questions and collecting answers

## Future Enhancements

Potential improvements:
1. **Multi-question forms**: Ask multiple related questions at once
2. **Conditional questions**: Follow-up questions based on previous answers
3. **Validation**: Ensure answers meet expected format
4. **Default values**: Suggest defaults based on user history
5. **Skip option**: Allow users to skip optional questions
