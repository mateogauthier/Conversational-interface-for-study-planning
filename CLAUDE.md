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

**LangGraph Agent System** (`CODE/app/agents/`):
- **Deterministic routing**: Python logic controls tool execution (not LLM guessing)
- **State management**: LangGraph's `AgentState` TypedDict tracks workflow
- **Complete file reading**: Reads entire documents after finding relevant chunks
- **Python-based extraction**: Uses regex/Python for exhaustive data extraction (no hallucination)
- **LLM for formatting only**: LLM receives pre-extracted data and only formats responses

**Agent Providers** (configurable via `AGENT_PROVIDER` env var):
- `langgraph` - **Recommended**: Production-ready with deterministic flow
- `local` - Deprecated LLM-based agent
- `api` - Remote agent via HTTP

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
│   ├── langgraph_provider.py    # ⭐ LangGraph agent (recommended)
│   ├── local_provider.py        # Deprecated LLM-based agent
│   ├── api_provider.py          # Agent provider factory
│   ├── base.py                  # AgentProvider interface
│   └── tools/                   # Tool registry
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

## LangGraph Agent Workflow

The agent follows a deterministic workflow (not LLM-controlled):

```
START
  ↓
search_documents (ChromaDB semantic search)
  ↓
should_read_file? (Python logic, not LLM)
  ├─ YES → read_file_content → extract_data (regex/Python) → generate_answer
  └─ NO → generate_answer (from chunks only)
  ↓
save_conversation
  ↓
END
```

**Critical Points**:
- Routing decisions are in Python, not LLM calls
- File reading is complete (not chunked)
- Data extraction uses regex/Python (exhaustive, no hallucination)
- LLM only formats pre-extracted data

### Adding New Agent Tools

See `CODE/app/agents/ADDING_TOOLS.md` for detailed guide. Quick summary:

1. Create tool function with `AgentState` parameter
2. Add node to LangGraph workflow
3. Define routing logic (Python, not LLM)
4. Update state schema if needed

Example:
```python
async def my_tool_node(state: AgentState) -> Dict[str, Any]:
    result = do_something(state["query"])
    return {
        "my_data": result,
        "agent_steps": [thinking_step, tool_step],
        "tools_executed": ["my_tool"]
    }

# Add to graph
workflow.add_node("my_tool", my_tool_node)
workflow.add_edge("search_documents", "my_tool")
```

## Environment Configuration

Copy `.env.example` to `.env` and configure:

**Critical Variables**:
- `AGENT_PROVIDER=langgraph` - Use LangGraph agent (recommended)
- `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` - Auth0 backend credentials
- `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID` - Auth0 frontend credentials (public)
- `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD` - MongoDB credentials
- `OLLAMA_MODEL` - LLM model (e.g., `gemma3:latest`, `llama2:latest`)

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

**Agent returns incomplete results**:
- Verify `AGENT_PROVIDER=langgraph` in `.env`
- Check logs for "Programmatically extracted X entries"
- LangGraph should show deterministic routing, not LLM loops

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
- `POST /rag/query` - Execute LangGraph agent workflow
- `POST /files/upload` - Upload document (private or public)
- `GET /conversations/` - List user's chat history
- `POST /feedback/message` - Submit like/dislike on response
- `GET /admin/*` - Admin-only endpoints (users, stats, feedback)
