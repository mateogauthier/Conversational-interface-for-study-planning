# Study Planning Conversational Interface

A production-ready study planning system powered by **LangGraph agents** and Retrieval-Augmented Generation (RAG). Upload documents, ask questions in natural language, and receive intelligent AI-generated answers backed by your content—secured with Auth0 authentication and user management.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19+-61dafb.svg)](https://reactjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agents-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-FF6B6B.svg)](https://ollama.ai)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com)
[![Auth0](https://img.shields.io/badge/Auth0-Secured-EB5424.svg)](https://auth0.com)

## 🚀 What's New

### LangGraph Agent Migration (Production-Ready)

The system now uses **LangGraph** for reliable, deterministic agent workflow instead of unreliable LLM-based decision making:

- ✅ **Deterministic Routing** - Python logic decides tool execution (no LLM guessing)
- ✅ **Complete File Reading** - Reads entire documents, not just chunks
- ✅ **Exhaustive Data Extraction** - Regex finds ALL matching entries (e.g., all courses from a specific year)
- ✅ **No Hallucination** - Python extracts facts, LLM only formats
- ✅ **Production-Tested** - LangGraph is battle-tested for reliable multi-step execution

**Migration Details**: See [LANGGRAPH_MIGRATION.md](LANGGRAPH_MIGRATION.md) for complete technical details.

## ✨ Features

### 🤖 Intelligent Agent System

**LangGraph-Powered Workflow:**
```
START → search_documents → should_read_file?
         ├─ YES → read_file_content → extract_data → generate_answer → END
         └─ NO  → generate_answer → END
```

- **Deterministic flow control** - No LLM deciding when to stop
- **Automatic file reading** - Reads complete files when search finds relevant chunks
- **Year-based extraction** - Programmatically finds ALL entries for requested years (2017-2024)
- **Context-efficient** - Sends only relevant data to LLM (saves tokens)

### 📚 RAG-Powered Q&A

- 🔍 **Semantic Search** - Vector-based search using ChromaDB and SentenceTransformers
- 📁 **Multi-format Support** - PDF, Word, Excel, text, and Markdown files
- 🌍 **Multi-language** - Auto-detect or specify response language (English/Spanish)
- 💬 **Conversation History** - Track and continue multi-turn conversations
- 🎯 **User-Filtered Results** - Each user only sees their own files + public files

### 🔐 User Management & Security

- **Auth0 Authentication** - Secure JWT-based authentication
- **Role-Based Access** - Student and admin roles with different permissions
- **Multi-Tenant Files** - Private student files + public admin files
- **User Statistics** - Track queries, uploads, feedback, and activity

### 📊 Feedback System

- **Like/Dislike Ratings** - On individual assistant responses
- **Written Comments** - Detailed feedback with timestamps
- **Admin Dashboard** - Paginated list with filtering (rating, user, file, date range)
- **LLM Summarization** - AI-powered analysis of feedback patterns
- **File Statistics** - Track views, usage, likes/dislikes per file

### 🐳 Production-Ready Deployment

- **Docker Compose** - 4-service architecture (frontend, backend, MongoDB, Ollama)
- **Hot-Reload Development** - Code changes reflect instantly
- **GPU Acceleration** - Optional NVIDIA GPU support for Ollama
- **Persistent Volumes** - MongoDB data, vector DB, and uploaded files
- **Health Checks** - Built-in monitoring endpoints

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [API Documentation](#api-endpoints)
- [Agent System](#langgraph-agent-details)
- [Configuration](#configuration)
- [Development](#development-workflow)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### Prerequisites

- **Docker Desktop** (10GB+ memory allocated)
- **Auth0 Account** (free tier works)
- **10GB+ disk space** (for Docker images and LLM models)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning
```

### 2. Setup Auth0

**Create Applications:**
1. [Auth0 Dashboard](https://manage.auth0.com) → Applications
2. Create **Single Page Application** (for frontend)
3. Create **API** (for backend)
4. Create **Machine to Machine Application** (for backend client)

**Configure Settings:**
- **Allowed Callback URLs**: `http://localhost:3000`
- **Allowed Logout URLs**: `http://localhost:3000`
- **Allowed Web Origins**: `http://localhost:3000`

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your Auth0 credentials
nano .env
```

**Required Variables:**
```bash
# Frontend Auth0 (Public - embedded in JavaScript)
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your_frontend_client_id
VITE_AUTH0_AUDIENCE=https://your-api-audience
VITE_AUTH0_REDIRECT_URI=http://localhost:3000

# Backend Auth0 (SENSITIVE - Never commit!)
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_AUDIENCE=https://your-api-audience
AUTH0_CLIENT_ID=your_backend_client_id
AUTH0_CLIENT_SECRET=your_backend_client_secret

# Agent Configuration
AGENT_PROVIDER=langgraph  # Use LangGraph agent (recommended)

# MongoDB
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=change_this_password
MONGO_DATABASE_NAME=study_planning

# Ollama
OLLAMA_MODEL=gemma3:latest
DEFAULT_LANGUAGE=spanish
```

### 4. Start Application

```bash
# Start all services (first time: 10-20 minutes)
docker compose up

# Or run in background
docker compose up -d

# View logs
docker compose logs -f
```

**Startup Process:**
1. ⏳ Docker builds containers (~5-10 min)
2. ⏳ Ollama downloads model (~4GB, 10-20 min)
3. ⏳ MongoDB initializes database
4. ✅ Services become available

### 5. Access Application

- 🎨 **Web UI**: http://localhost:3000
- 🌐 **API**: http://localhost:8000
- 📚 **API Docs**: http://localhost:8000/docs
- 🗄️ **MongoDB**: mongodb://localhost:27017

## 🏗️ Architecture

### Four-Service Docker Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Network                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────┐  ┌──────────────┐  ┌───────────┐      │
│  │  Frontend  │  │  FastAPI +   │  │  MongoDB  │      │
│  │  (React)   │──│  LangGraph   │──│   (DB)    │      │
│  │  Port 3000 │  │  Port 8000   │  │ Port 27017│      │
│  └────────────┘  └──────┬───────┘  └───────────┘      │
│                         │                               │
│                  ┌──────▼────────┐                     │
│                  │    Ollama     │                     │
│                  │     (LLM)     │                     │
│                  │  Port 11434   │                     │
│                  └───────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

### LangGraph Agent Workflow

```
┌─────────────────────────────────────────────────────┐
│                   User Query                         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
            ┌──────────────────┐
            │ search_documents │  ← Find relevant chunks
            └─────────┬────────┘    (ChromaDB + embeddings)
                      │
                      ▼
            ┌──────────────────┐
            │ should_read_file?│  ← Deterministic routing
            └─────────┬────────┘    (Python logic, not LLM)
                      │
         ┌────────────┴────────────┐
         │                         │
      YES│                         │NO
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│read_file_content│      │ generate_answer │
│  (Complete)     │      │  (From chunks)  │
└────────┬────────┘      └────────┬────────┘
         │                         │
         ▼                         │
┌─────────────────┐               │
│extract_by_year  │               │
│ (Regex/Python)  │               │
└────────┬────────┘               │
         │                         │
         └────────────┬────────────┘
                      │
                      ▼
            ┌──────────────────┐
            │ generate_answer  │  ← LLM formats data
            │   (Format only)  │    (No searching)
            └─────────┬────────┘
                      │
                      ▼
            ┌──────────────────┐
            │   Save to DB     │
            │  (Conversation)  │
            └─────────┬────────┘
                      │
                      ▼
            ┌──────────────────┐
            │     Response     │
            └──────────────────┘
```

**Key Benefits:**
- ✅ **No infinite loops** - Clear termination conditions
- ✅ **No missed data** - Python regex finds EVERYTHING
- ✅ **Faster** - Only relevant data sent to LLM
- ✅ **Reliable** - Deterministic execution path

### Persistent Volumes

- **`uploads`** - User-uploaded documents
- **`chroma_db`** - Vector embeddings database
- **`ollama-models`** - Downloaded LLM models (~2-4GB each)
- **`mongo-data`** - MongoDB database files

## 📡 API Endpoints

### 🤖 Agent Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/rag/query` | Query with LangGraph agent (full workflow) |
| `POST` | `/rag/search` | Search documents only (no LLM) |
| `GET` | `/rag/stats` | User statistics |

**Query Example:**
```bash
curl -X POST "http://localhost:8000/rag/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "puedes decirme mis notas del 2024?",
    "n_results": 15,
    "language": "auto",
    "conversation_id": "optional-conversation-id"
  }'
```

**Response:**
```json
{
  "success": true,
  "query": "puedes decirme mis notas del 2024?",
  "answer": "Encontré 6 materias del año 2024:\n1. Taller de seguridad informática...",
  "context_used": "...",
  "n_chunks_found": 5,
  "sources": ["escolaridad mateo gauthier.pdf"],
  "model_used": "gemma3:latest",
  "conversation_id": "507f1f77bcf86cd799439011",
  "message_id": "507f1f77bcf86cd799439012"
}
```

### 📁 File Management

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/files/upload` | Upload document (private/public) | All/Admin |
| `GET` | `/files/` | List accessible files | All |
| `GET` | `/files/{filename}` | Get file metadata | All |
| `DELETE` | `/files/{filename}` | Delete file | Owner/Admin |
| `GET` | `/files/supported/extensions` | List supported types | All |

### 👤 User Management

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/users/me` | Current user profile | All |
| `GET` | `/users/me/stats` | Current user statistics | All |
| `PATCH` | `/users/me` | Update profile | All |

### 💬 Conversations

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/conversations/` | List conversations | All |
| `GET` | `/conversations/{id}` | Get conversation details | All |
| `DELETE` | `/conversations/{id}` | Delete conversation | All |

### 📊 Feedback

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/feedback/message` | Submit like/dislike + comment | All |
| `POST` | `/feedback/` | Submit general feedback | All |

### 👨‍💼 Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/admin/feedback` | List all feedback (paginated) |
| `GET` | `/admin/feedback/stats` | Feedback statistics |
| `POST` | `/admin/feedback/summary` | AI-powered feedback summary |
| `GET` | `/admin/feedback/file/{filename}` | Feedback for specific file |
| `GET` | `/admin/users` | List all users |
| `GET` | `/admin/users/{id}` | User details |
| `GET` | `/admin/stats` | System-wide statistics |

## 🤖 LangGraph Agent Details

### How It Works

**1. Search Phase**
```python
# Agent searches for relevant document chunks
search_results = await rag_service.search_documents_async(
    query="puedes decirme mis notas del 2024?",
    user=current_user,
    n_results=15
)
# Returns: 5 chunks from "escolaridad mateo gauthier.pdf"
```

**2. Routing Decision (Deterministic)**
```python
# Python logic decides what to do next
def _should_read_file(state):
    if state.get("file_content"):
        return "generate"  # Already have file

    chunks = state["search_results"].get("relevant_chunks", [])
    if chunks:
        return "read_file"  # Found chunks → read complete file

    return "generate"  # No chunks → generate from search
```

**3. File Reading**
```python
# Reads COMPLETE file (not just chunks)
content = await file_service.extract_text_from_file(
    "escolaridad mateo gauthier.pdf"
)
# Returns: 5,478 characters (entire file)
```

**4. Data Extraction (Python Regex)**
```python
# Programmatically extract ALL matching entries
def _extract_entries_by_year(content, year="2024"):
    entries = []
    for line in content.split('\n'):
        if re.search(r'\d{2}/\d{2}/2024', line):
            entries.append(line)
    return entries
# Returns: 6 lines with dates containing "2024"
```

**5. LLM Formatting**
```python
# LLM only formats the data (no searching)
prompt = f"""
I found {len(entries)} entries for year 2024.
Format them in Spanish as a numbered list.

Entries:
{'\n'.join(entries)}
"""
# LLM receives: Already extracted data, just format it!
```

### Adding New Tools

See [ADDING_TOOLS.md](CODE/app/agents/ADDING_TOOLS.md) for complete guide.

**Quick Example:**
```python
async def my_custom_tool_node(state: AgentState) -> Dict[str, Any]:
    # Your tool logic here
    result = do_something()

    return {
        "my_data": result,
        "agent_steps": [thinking_step, tool_step, result_step],
        "tools_executed": ["my_custom_tool"]
    }

# Add to graph
workflow.add_node("my_tool", my_custom_tool_node)
workflow.add_edge("search_documents", "my_tool")
workflow.add_edge("my_tool", "generate_answer")
```

## ⚙️ Configuration

### Agent Provider Selection

```bash
# .env file
AGENT_PROVIDER=langgraph  # Recommended (production-ready)
# AGENT_PROVIDER=local    # Old LLM-based agent (deprecated)
```

### Supported LLM Models

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `gemma3:latest` | 5.0GB | Fast | Excellent | **Recommended** |
| `llama2:latest` | 3.8GB | Medium | Good | Balanced |
| `mistral` | 4.1GB | Medium | Better | Higher quality |
| `phi` | 1.6GB | Fast | Good | Limited resources |

**Change Model:**
```bash
# Edit .env
OLLAMA_MODEL=mistral

# Restart
docker compose restart fastapi-app
```

### Supported File Types

| Type | Extensions | Loader |
|------|------------|--------|
| PDF | `.pdf` | PyPDF |
| Word | `.doc`, `.docx` | python-docx |
| Excel | `.xls`, `.xlsx` | openpyxl |
| Text | `.txt` | TextLoader |
| Markdown | `.md` | TextLoader |

## 🛠️ Development Workflow

### Making Code Changes

**Backend (Hot-reload enabled):**
```bash
# Edit files in CODE/
# Changes reflect instantly - no rebuild needed!

# View logs
docker compose logs -f fastapi-app
```

**Frontend:**
```bash
# Edit files in FRONTEND/

# Rebuild container
docker compose up --build frontend

# Or use native dev (faster)
cd FRONTEND
npm run dev
# Access at http://localhost:5173
```

### Adding Dependencies

**Backend:**
```bash
# Add to CODE/requirements.txt
echo "pandas==2.0.0" >> CODE/requirements.txt

# Rebuild
docker compose up --build fastapi-app
```

**Frontend:**
```bash
cd FRONTEND
npm install axios
docker compose up --build frontend
```

### Database Operations

```bash
# Access MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p password

# Switch to database
use study_planning

# View collections
show collections

# Query users
db.users.find().pretty()

# Make user admin
db.users.updateOne(
  { auth0_id: "auth0|123456789" },
  { $set: { role: "admin" } }
)

# View conversations
db.conversations.find({ auth0_id: "auth0|123456789" }).limit(5).pretty()

# Count feedback
db.feedback.countDocuments()
```

### Testing

```bash
# Backend unit tests
docker exec study-planning-api python tests/test_direct.py

# API tests (server must be running)
docker exec study-planning-api python tests/test_rag.py
```

## 🚀 Production Deployment

### Production Mode

```bash
# Start production environment
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

### Production Features

- ✅ **No bind mount** - Uses baked-in code
- ✅ **4 Uvicorn workers** - Concurrent requests
- ✅ **Resource limits** - CPU/memory constraints
- ✅ **Internal networking** - Ollama not exposed
- ✅ **Optimized builds** - Multi-stage Dockerfiles

### Security Checklist

- [ ] Change MongoDB password in `.env`
- [ ] Use strong Auth0 secrets
- [ ] Enable HTTPS (reverse proxy)
- [ ] Configure CORS properly
- [ ] Set up firewall rules
- [ ] Regular MongoDB backups
- [ ] Monitor logs for security events
- [ ] Update dependencies regularly

## 🔧 Troubleshooting

### "LLM service not available" (503 Error)

**Cause**: Insufficient Docker memory

**Fix**:
```bash
# Docker Desktop → Settings → Resources
# Increase Memory to 10GB minimum
# Apply & Restart

docker compose down
docker compose up -d
```

### Auth0 Login Fails

**Cause**: Incorrect redirect URIs

**Fix**:
1. Auth0 Dashboard → Application Settings
2. Set **Allowed Callback URLs**: `http://localhost:3000`
3. Set **Allowed Logout URLs**: `http://localhost:3000`
4. Set **Allowed Web Origins**: `http://localhost:3000`
5. Verify `.env` credentials match
6. Rebuild: `docker compose up --build frontend`

### MongoDB Connection Error

```bash
# Check status
docker compose ps mongodb

# View logs
docker compose logs -f mongodb

# Verify credentials
cat .env | grep MONGO

# Restart
docker compose restart mongodb
```

### Agent Returns Incomplete Results

**Issue**: Agent only finding partial data (e.g., 2 courses instead of 6)

**Check**:
1. Verify `AGENT_PROVIDER=langgraph` in `.env`
2. Check logs: `docker compose logs -f fastapi-app | grep "Programmatically extracted"`
3. Should see: `"Programmatically extracted 6 entries for year 2024"`

**Verify Workflow**:
```bash
# Check agent logs
docker compose logs fastapi-app | grep -E "(LangGraph|Found.*chunks|extracted.*entries)"
```

### GPU Not Working

```bash
# Check NVIDIA drivers
nvidia-smi

# Install Container Toolkit (Fedora/RHEL)
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU access
docker run --rm --gpus all ubuntu nvidia-smi
docker exec study-planning-ollama nvidia-smi

# Restart
docker compose down && docker compose up -d
```

## 📚 Project Structure

```
Conversational-interface-for-study-planning/
├── .env                            # Your secrets (gitignored)
├── .env.example                    # Environment template
├── docker-compose.yml              # Development setup
├── docker-compose.prod.yml         # Production setup
├── LANGGRAPH_MIGRATION.md         # Agent migration details
├── CODE/                           # Backend
│   ├── app/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── agents/
│   │   │   ├── langgraph_provider.py   # LangGraph agent ⭐
│   │   │   ├── local_provider.py       # Old agent (deprecated)
│   │   │   ├── base.py                 # Agent interfaces
│   │   │   ├── tools/                  # Tool registry
│   │   │   └── ADDING_TOOLS.md         # Tool guide
│   │   ├── api/routes/
│   │   │   ├── rag.py             # RAG + agent endpoints
│   │   │   ├── files.py           # File management
│   │   │   ├── users.py           # User profiles
│   │   │   ├── admin.py           # Admin tools
│   │   │   ├── conversations.py   # Chat history
│   │   │   └── feedback.py        # Feedback system
│   │   ├── services/
│   │   │   ├── rag_service.py     # ChromaDB + embeddings
│   │   │   ├── llm_service.py     # Ollama integration
│   │   │   ├── file_service.py    # File handling
│   │   │   ├── user_service.py    # User management
│   │   │   ├── conversation_service.py
│   │   │   └── feedback_service.py
│   │   ├── core/
│   │   │   ├── config.py          # Settings
│   │   │   ├── security.py        # Auth0 JWT
│   │   │   └── exceptions.py      # Custom errors
│   │   └── db/
│   │       ├── database.py        # MongoDB async
│   │       ├── models.py          # Pydantic models
│   │       └── collections.py     # Collection schemas
│   ├── requirements.txt           # Python deps (+ langgraph)
│   └── Dockerfile
├── FRONTEND/                       # Frontend
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── package.json
│   └── Dockerfile
└── README.md                       # This file
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Test thoroughly (especially agent workflows)
4. Ensure no secrets in commits
5. Commit: `git commit -m "Add amazing feature"`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

**Agent Testing Checklist:**
- [ ] Test year-specific queries (e.g., "notas del 2024")
- [ ] Verify complete data extraction (not partial)
- [ ] Check agent logs for deterministic routing
- [ ] Test with different file types
- [ ] Verify conversation context maintained

## 📖 Documentation

- **[LANGGRAPH_MIGRATION.md](LANGGRAPH_MIGRATION.md)** - Complete agent migration details
- **[ADDING_TOOLS.md](CODE/app/agents/ADDING_TOOLS.md)** - Guide for adding agent tools
- **[CLAUDE.md](CLAUDE.md)** - Technical guidance for Claude Code
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation (when running)

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent workflow framework ⭐
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Auth0](https://auth0.com/) - Authentication platform
- [MongoDB](https://www.mongodb.com/) - NoSQL database
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - LLM application framework
- [React](https://react.dev/) - Frontend framework
- [Vite](https://vitejs.dev/) - Frontend build tool

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/repo/issues)
- **Docs**: See documentation links above
- **API**: http://localhost:8000/docs (when running)

---

**Built for students, powered by LangGraph agents** 🎓🤖🚀
