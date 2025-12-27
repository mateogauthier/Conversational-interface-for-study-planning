# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A production-ready study planning system powered by **LangGraph agents** and Retrieval-Augmented Generation (RAG). The application allows users to upload documents (PDF, Word, Excel, etc.), ask questions in natural language, and receive AI-generated answers backed by their content—secured with Auth0 authentication.

## Architecture

### Four-Service Docker Architecture

The application consists of 4 main services running in Docker:

1. **Frontend** (React + Vite) - Port 3000
   - Location: `FRONTEND/`
   - Auth0 authentication
   - Material design components
   - Markdown rendering with Mermaid diagram support

2. **Backend API** (FastAPI + Python) - Port 8000
   - Location: `CODE/`
   - LangGraph agent system
   - RAG with ChromaDB
   - MongoDB for persistence
   - Auth0 JWT validation

3. **Agent Tools API** (FastAPI) - Port 8002
   - Location: `AGENT_API/`
   - Separate microservice for agent tool execution
   - Provides endpoints for file operations, search, stats

4. **Supporting Services**:
   - **MongoDB** (Port 27017) - User data, conversations, feedback
   - **ChromaDB** (Port 8001) - Vector embeddings for semantic search
   - **Ollama** (Port 11434) - Local LLM inference with GPU support

### Key Architectural Patterns

**ReAct Agent System** (`CODE/app/agents/`):
- **LLM-based tool selection**: Uses LangGraph's `create_react_agent()` where the LLM intelligently chooses which tools to call based on user queries
- **Function calling**: Llama 3.1 with native tool/function calling support
- **Python-based prerequisite validation**: Deterministic course filtering in tool implementations
- **No instruction bloat**: Tool descriptions guide LLM behavior instead of brittle prompt engineering
- **Automatic workflow**: ReAct pattern handles reasoning → action → observation loop

**Agent Providers** (configurable via `AGENT_PROVIDER` env var):
- `react` - **Recommended**: ReAct-based LangGraph agent with intelligent tool routing (fast, simple)
- `instructor` - **Advanced**: Instructor-enhanced ReAct with structured iterative reasoning (explicit planning, validation, better error handling)
- `api` - Remote agent via HTTP (stub implementation for future external service)

**Multi-Tenant File System**:
- Private student files (owner only)
- Public admin files (visible to all)
- Files stored in MongoDB GridFS
- Semantic search via ChromaDB with user filtering

**Authentication Flow**:
- Frontend gets JWT from Auth0
- Backend validates JWT on every request
- User roles: `student` (default) and `admin`
- First-time users auto-created in MongoDB

## Common Development Commands

### Docker Compose (Primary Development Method)

```bash
# Start all services (first time: 10-20 min for Ollama model download)
docker compose up

# Start in background
docker compose up -d

# View logs for specific service
docker compose logs -f fastapi-app
docker compose logs -f frontend

# Rebuild after dependency changes
docker compose up --build fastapi-app
docker compose up --build frontend

# Stop all services
docker compose down

# Production mode (no bind mounts, multi-worker)
docker compose -f docker-compose.prod.yml up -d
```

### Backend Development

**Hot-reload is enabled by default** - changes to `CODE/` automatically reload:

```bash
# No rebuild needed for code changes!
# Just edit files and watch logs:
docker compose logs -f fastapi-app

# Run tests
docker exec study-planning-api python tests/test_direct.py
docker exec study-planning-api python tests/test_rag.py

# Add Python dependencies
# 1. Edit CODE/requirements.txt
# 2. Rebuild:
docker compose up --build fastapi-app
```

### Frontend Development

```bash
# Option 1: Docker (slower rebuild)
docker compose up --build frontend

# Option 2: Native dev server (faster, recommended)
cd FRONTEND
npm install
npm run dev  # Runs on port 5173 with hot-reload

# Build for production
npm run build

# Lint
npm run lint
```

### Database Operations

```bash
# Access MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p password

# Common MongoDB operations
use study_planning
show collections
db.users.find().pretty()
db.conversations.find({ auth0_id: "auth0|123..." }).limit(5)

# Make user an admin
db.users.updateOne(
  { auth0_id: "auth0|123456789" },
  { $set: { role: "admin" } }
)

# View feedback
db.feedback.find().sort({ created_at: -1 }).limit(10)
```

### Ollama Model Management

```bash
# List available models
docker exec study-planning-ollama ollama list

# Pull a new model
docker exec study-planning-ollama ollama pull gemma3:latest

# Change model: Edit .env
OLLAMA_MODEL=gemma3:latest
# Then restart:
docker compose restart fastapi-app
```

## Code Structure

### Backend (`CODE/app/`)

```
app/
├── main.py                      # FastAPI entry, startup events
├── agents/
│   ├── react_langgraph_provider.py  # ⭐ ReAct agent (recommended)
│   ├── api_provider.py          # Agent provider factory
│   └── base.py                  # AgentProvider interface
├── api/
│   ├── dependencies.py          # Auth dependencies
│   └── routes/
│       ├── rag.py              # RAG queries, agent execution
│       ├── files.py            # File upload/list/delete
│       ├── users.py            # User profile, stats
│       ├── admin.py            # Admin endpoints
│       ├── conversations.py    # Chat history
│       ├── feedback.py         # Like/dislike ratings
│       └── agent.py            # Agent-specific endpoints
├── services/
│   ├── rag_service.py          # ChromaDB + embeddings
│   ├── llm_service.py          # Ollama integration
│   ├── file_service.py         # GridFS file handling
│   ├── user_service.py         # User CRUD
│   ├── conversation_service.py # Chat history
│   └── feedback_service.py     # Feedback CRUD
├── core/
│   ├── config.py               # Settings (loads from .env)
│   ├── security.py             # Auth0 JWT validation
│   └── exceptions.py           # Custom errors
├── db/
│   ├── database.py             # MongoDB async connection
│   ├── models.py               # Pydantic models
│   └── collections.py          # Collection schemas
├── models/
│   └── responses.py            # API response models
└── tools/
    └── http_executor.py        # HTTP tool execution for agents
```

### Frontend (`FRONTEND/src/`)

```
src/
├── main.jsx                    # App entry
├── App.jsx                     # Root component, routing
├── components/                 # Reusable UI components
├── pages/                      # Page-level components
├── services/                   # API clients
├── context/                    # React context (auth, etc.)
├── config/                     # Frontend config
└── i18n.js                     # Internationalization
```

## ReAct Agent Workflow

The agent uses LangGraph's `create_react_agent()` with intelligent tool selection:

```
START
  ↓
User Query → LLM analyzes query
  ↓
LLM decides which tool(s) to call based on:
  - Tool descriptions (docstrings)
  - Query intent
  - Available context
  ↓
Tool Execution (one or more):
  - search_documents: Search uploaded files
  - get_student_schooling: Get completed/in-progress courses, GPA
  - get_available_courses: Get enrollable courses (Python prerequisite validation)
  - get_degree_curriculum: Get full degree curriculum
  - get_student_plan: Get personalized study plan
  - web_search: Search the web
  ↓
LLM receives tool results
  ↓
LLM generates natural language response
  ↓
END
```

**Critical Points**:
- **LLM-based routing**: The LLM intelligently selects which tools to call (no hardcoded rules)
- **ReAct pattern**: Reasoning → Acting → Observing loop until answer is complete
- **Python validation**: Prerequisite checking done deterministically in `get_available_courses` tool
- **No instruction bloat**: Tool behavior defined by clear docstrings, not brittle prompts
- **Multi-language support**: Automatically responds in same language as query (Spanish/English)

## Instructor-Enhanced Agent Workflow (Advanced)

The `instructor` agent provider adds structured iterative reasoning on top of ReAct:

```
START
  ↓
1. PLANNING PHASE (Instructor)
   - Analyze user intent
   - Determine optimal strategy
   - Identify required tools
   - Plan execution steps
   - Anticipate challenges
   - ASK QUESTIONS if information is missing or ambiguous
  ↓
  [If clarification needed] → PAUSE, ask user question, wait for answer → Resume
  ↓
2. EXECUTION PHASE (ReAct iterations)
   For each iteration (max 5):
     - Execute tools via ReAct agent
     - Collect structured results
     - Assess if sufficient information gathered
     - Decide next action if needed
  ↓
3. VALIDATION PHASE (Instructor)
   - Validate answer completeness
   - Calculate confidence score
   - Identify supporting evidence
   - Flag caveats or limitations
  ↓
4. FINAL ANSWER
   - Structured response with confidence
   - Clear evidence trail
   - Explicit limitations noted
  ↓
END
```

**Why use Instructor agent?**
- **Explicit planning**: Agent explains its reasoning before execution
- **Interactive questioning**: Agent asks clarifying questions when needed (see [AGENT_QUESTIONS_GUIDE.md](AGENT_QUESTIONS_GUIDE.md))
- **Better error recovery**: Structured validation catches incomplete answers
- **Confidence scoring**: Know how sure the agent is about its answer
- **Evidence tracking**: Clear trail of what information supports the answer
- **Iterative refinement**: Agent can recognize when it needs more information

**When to use each agent:**
- `react` - Fast, straightforward queries; production use
- `instructor` - Complex multi-step problems requiring validation; development/debugging

### Adding New Agent Tools

Adding tools to the ReAct agent is simple:

1. Define a tool function decorated with `@tool` in [react_langgraph_provider.py](CODE/app/agents/react_langgraph_provider.py#L75):

```python
@tool
async def my_new_tool(param1: str, param2: int = 5) -> dict:
    """Tool description that the LLM will read.

    Use this when the user asks about X, Y, or Z.

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2 (default: 5)

    Returns:
        Dict with results
    """
    # Tool implementation
    result = await self.tool_executor.execute(
        tool_name="my_tool_endpoint",
        parameters={"param1": param1, "param2": param2},
        user=self._current_user
    )

    if result.error:
        return {"error": result.error}

    return result.result
```

2. Add to tool list in `_create_tools()`:

```python
return [
    search_documents,
    get_student_schooling,
    # ... other tools ...
    my_new_tool,  # Add here
]
```

That's it! The LLM will automatically discover and use your tool based on its description.

## Environment Configuration

Copy `.env.example` to `.env` and configure:

**Critical Variables**:
- `AGENT_PROVIDER` - Agent type: `react` (recommended, fast) or `instructor` (advanced, structured reasoning)
- `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` - Auth0 backend credentials
- `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID` - Auth0 frontend credentials (public)
- `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD` - MongoDB credentials
- `OLLAMA_MODEL` - LLM model with function calling support (e.g., `llama3.1:8b`, `qwen2.5:7b`)
  - **Note**: Model MUST support tool/function calling. Gemma and Llama 2 do NOT support this.
  - **For Instructor**: Model must also support JSON output mode for structured responses

**Optional Variables**:
- `DEFAULT_LANGUAGE=auto` - Response language (auto, english, spanish)
- `MAX_CONTEXT_LENGTH=1500` - Max context characters sent to LLM
- `OLLAMA_TIMEOUT=180` - LLM timeout in seconds

## Testing

```bash
# Backend unit tests
docker exec study-planning-api python tests/test_direct.py

# RAG integration tests (requires running server)
docker exec study-planning-api python tests/test_rag.py

# Test with actual queries
docker exec study-planning-api python tests/demo_rag.py
```

## Common Issues & Debugging

**LLM service not available (503 Error)**:
- Increase Docker memory to 10GB+ in Docker Desktop settings
- Check Ollama logs: `docker compose logs -f ollama`
- Verify model downloaded: `docker exec study-planning-ollama ollama list`

**Auth0 login fails**:
- Verify redirect URIs in Auth0 dashboard match `.env`
- Check both frontend and backend Auth0 credentials
- Rebuild frontend after `.env` changes: `docker compose up --build frontend`

**Agent returns tool/function calling errors**:
- Verify `AGENT_PROVIDER=react` in `.env`
- Check model supports function calling: `llama3.1:8b`, `qwen2.5:7b` work
- Gemma and Llama 2 models do NOT support tools - use Llama 3.1+
- Error "does not support tools (status code: 400)" means wrong model

**Agent returns incomplete/wrong results**:
- Check agent logs for tool calls: `docker compose logs -f fastapi-app`
- Verify LLM is calling appropriate tools (should see "Calling get_student_schooling")
- Test query phrasing - be specific ("que materias estoy cursando?" vs "hola")

**MongoDB connection error**:
- Check credentials in `.env` match `docker-compose.yml`
- Verify MongoDB is healthy: `docker compose ps mongodb`
- View logs: `docker compose logs -f mongodb`

**ChromaDB/Vector search issues**:
- Files auto-reindex on startup
- Force reindex: restart backend with `docker compose restart fastapi-app`
- Check logs for "Starting automatic file reindexing"

## Security Notes

- **Never commit `.env`** - Contains Auth0 secrets and MongoDB passwords
- Frontend Auth0 credentials are public (embedded in JS bundle)
- Backend Auth0 credentials must stay secret (server-side only)
- User file access enforced via Auth0 user ID matching
- Admin endpoints check `role == "admin"` in JWT claims

## API Documentation

When running, interactive API docs available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Key endpoints:
- `POST /rag/query` - Execute ReAct agent workflow
- `POST /files/upload` - Upload document (private or public)
- `GET /conversations/` - List user's chat history
- `POST /feedback/message` - Submit like/dislike on response
- `GET /admin/*` - Admin-only endpoints (users, stats, feedback)
