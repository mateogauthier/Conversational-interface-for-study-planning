# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG-powered Study Planning Conversational Interface with full authentication and user management. The system combines Auth0 authentication, MongoDB persistence, vector-based semantic search (ChromaDB), and LLM responses (Ollama) to provide an intelligent Q&A platform for students and administrators.

**Key Features:**
- Auth0 JWT authentication with role-based access control (student/admin)
- MongoDB database for users, conversations, feedback, and file metadata
- RAG pipeline for document processing and intelligent Q&A
- Conversation history with context-aware responses
- User feedback system for quality improvement
- Multi-tenant file management (private student files + public admin files)

## Essential Commands

### Docker (Recommended)

**Important**: Use `docker compose` (with space) not `docker-compose` (with hyphen).

```bash
# Development (with hot-reload) - run from repository root
docker compose up
# Access Frontend at http://localhost:3000
# Access API at http://localhost:8000
# Access API docs at http://localhost:8000/docs
# Code changes are reflected immediately (no rebuild needed)

# Development (rebuild containers)
docker compose up --build

# Development (run in background)
docker compose up -d

# Production deployment
docker compose -f docker-compose.prod.yml up -d

# Stop containers
docker compose down

# Stop containers and remove volumes (WARNING: deletes all data)
docker compose down -v

# View logs
docker compose logs -f fastapi-app
docker compose logs -f frontend
docker compose logs -f mongodb
docker compose logs -f ollama

# Access container shells
docker exec -it study-planning-api bash
docker exec -it study-planning-mongodb mongosh -u admin -p password
docker exec -it study-planning-ollama bash

# Pull Ollama model manually
docker exec study-planning-ollama ollama pull llama2:latest

# MongoDB operations
docker exec -it study-planning-mongodb mongosh -u admin -p password
# In mongosh:
# use study_planning
# db.users.find().pretty()
# db.conversations.find().pretty()
```

### Frontend Development

```bash
# Native development (hot-reload)
cd FRONTEND
npm install
npm run dev
# Access at http://localhost:5173 (Vite dev server)

# Production build
npm run build

# Lint
npm run lint
```

### Testing

```bash
# Backend unit tests
docker exec study-planning-api python tests/test_direct.py

# Native (direct on host)
cd CODE
python tests/test_direct.py

# API endpoint tests (server must be running)
python tests/test_rag.py
```

### Dependencies

```bash
# Docker automatically handles dependencies

# Backend: Install Python dependencies
cd CODE
pip install -r requirements.txt

# Frontend: Install Node dependencies
cd FRONTEND
npm install
```

## Architecture

### Four-Service Docker Architecture

The application runs as four interconnected Docker containers:

1. **frontend** (React + Nginx)
   - Port: 3000 → 80
   - React 19 with Auth0 integration
   - Vite for build, Nginx for serving

2. **fastapi-app** (FastAPI + ChromaDB + SentenceTransformer)
   - Port: 8000
   - Main application backend
   - Depends on: mongodb, ollama

3. **mongodb** (MongoDB 7.0)
   - Port: 27017
   - Stores users, conversations, feedback, file metadata
   - Persistent storage via `mongo-data` volume

4. **ollama** (Ollama LLM)
   - Port: 11434
   - Runs LLM models (llama2, mistral, etc.)
   - GPU-accelerated (with NVIDIA Container Toolkit)
   - Persistent models via `ollama-models` volume

### Backend: Five-Layer Architecture

The backend follows clean architecture with clear separation of concerns:

1. **API Layer** ([app/api/routes/](CODE/app/api/routes/))
   - [files.py](CODE/app/api/routes/files.py): File upload, listing, deletion (with permission checks)
   - [rag.py](CODE/app/api/routes/rag.py): RAG search and query endpoints (user-filtered)
   - [llm.py](CODE/app/api/routes/llm.py): Direct LLM interaction endpoints
   - [users.py](CODE/app/api/routes/users.py): User profile management
   - [admin.py](CODE/app/api/routes/admin.py): Admin-only endpoints
   - [conversations.py](CODE/app/api/routes/conversations.py): Conversation history management
   - [feedback.py](CODE/app/api/routes/feedback.py): User feedback submission

2. **Service Layer** ([app/services/](CODE/app/services/))
   - [auth_service.py](CODE/app/services/auth_service.py): Auth0 token verification, user creation
   - [user_service.py](CODE/app/services/user_service.py): User CRUD, statistics, permissions
   - [conversation_service.py](CODE/app/services/conversation_service.py): Conversation and message management
   - [file_service.py](CODE/app/services/file_service.py): File validation, storage, metadata
   - [rag_service.py](CODE/app/services/rag_service.py): Document processing, embedding, vector search
   - [llm_service.py](CODE/app/services/llm_service.py): Ollama integration, prompt construction

3. **Database Layer** ([app/db/](CODE/app/db/))
   - [database.py](CODE/app/db/database.py): MongoDB async connection singleton
   - [models.py](CODE/app/db/models.py): Pydantic models for MongoDB documents
   - [collections.py](CODE/app/db/collections.py): Collection name constants and schemas

4. **Core Layer** ([app/core/](CODE/app/core/))
   - [config.py](CODE/app/core/config.py): Centralized configuration with environment variables
   - [security.py](CODE/app/core/security.py): JWT verification, Auth0 integration, JWKS caching
   - [exceptions.py](CODE/app/core/exceptions.py): Custom exception hierarchy

5. **API Dependencies** ([app/api/dependencies.py](CODE/app/api/dependencies.py))
   - Dependency injection for all services
   - Authentication middleware (`get_current_user`)
   - Role-based access control (`get_current_admin`, `get_current_student`)

### Key Technical Details

#### Authentication & Authorization ([security.py:76-239](CODE/app/core/security.py#L76-L239))

**JWT Verification Flow**:
1. Extract JWT from `Authorization: Bearer <token>` header
2. Fetch Auth0 JWKS (JSON Web Key Set) with caching
3. Match token's `kid` (key ID) to find correct RSA public key
4. Verify token signature, issuer, audience, and expiration
5. Extract role from JWT claims (multiple strategies):
   - Check `roles` claim (Auth0 RBAC)
   - Check custom namespace claims
   - Check `permissions` claim (e.g., `role:admin`)
   - M2M tokens (ending in `@clients`) default to admin
   - Authenticated users without roles default to student

**Role Strategies**:
- **Admin**: Full access to all endpoints, can manage public files, view all users
- **Student**: Can only access own files and conversations

#### Multi-Tenant File Management ([file_service.py](CODE/app/services/file_service.py))

**File Ownership Model**:
- **Private files** (`is_public=false`): Uploaded by students, only accessible to owner
- **Public files** (`is_public=true`): Uploaded by admins, accessible to all users

**Metadata Storage**:
- File physical storage: `CODE/data/uploads/` (or `uploads` volume)
- File metadata: MongoDB `file_metadata` collection
- Tracks: owner, visibility, size, chunk count, feedback stats

**RAG Filtering**:
- When querying ChromaDB, results filtered by `user_id` (private files) or `is_public=true`
- Ensures users only see context from files they have access to

#### Conversation Management ([conversation_service.py](CODE/app/services/conversation_service.py))

**Multi-Turn Conversation Support**:
- Each query can optionally include `conversation_id` to continue existing conversation
- If no `conversation_id`, a new conversation is created with auto-generated title
- Conversation history is retrieved and included in LLM context window
- History truncation: ~24,000 chars (~6,000 tokens) to fit within model context limits

**Context Window Management**:
- Total context (llama2 default): ~8,000 tokens
- Reserved for RAG context chunks: ~1,500 chars (~375 tokens)
- Reserved for system prompt: ~300 tokens
- Reserved for current query: ~200 tokens
- Reserved for response buffer: ~500 tokens
- **Remaining for history**: ~6,000 tokens (~24,000 chars)

**Message Storage**:
- Conversations stored in `conversations` collection (metadata, title, user_id)
- Messages stored in `messages` collection (role, content, timestamp, sources)
- Separation allows efficient pagination and filtering

#### RAG Pipeline ([rag_service.py:98-148](CODE/app/services/rag_service.py#L98-L148))

**Document Processing**:
1. Documents loaded via LangChain loaders (PDF, Word, Excel, Text, Markdown)
2. Text split into chunks using `RecursiveCharacterTextSplitter` (default: 1000 chars, 200 overlap)
3. Chunks embedded using SentenceTransformer (`all-MiniLM-L6-v2`)
4. Embeddings stored in ChromaDB with metadata (source file, chunk index, user_id, is_public)
5. File metadata updated in MongoDB with chunk count and processed status

**Query Flow**:
1. User submits query via `/rag/query/` → [rag.py:76-126](CODE/app/api/routes/rag.py#L76-L126)
2. Query embedded using same SentenceTransformer model
3. ChromaDB similarity search with user filtering (private + public files)
4. Top N chunks retrieved and context assembled
5. Conversation history retrieved (if conversation_id provided)
6. LLM generates answer using context + history → [llm_service.py:generate_with_context()](CODE/app/services/llm_service.py#L129)
7. Response saved to conversation (new message added)
8. User statistics incremented (query count, last activity)
9. Response returned with sources, chunks, and conversation_id

#### LLM Integration ([llm_service.py:129-162](CODE/app/services/llm_service.py#L129-L162))

**Prompt Construction**:
- System instructions (configurable via `RESPONSE_INSTRUCTIONS` env var)
- Conversation history (if continuing conversation)
- RAG context chunks from documents
- Current user query
- Language-specific instructions (auto-detected or specified)

**Language Detection** ([llm_service.py:164-179](CODE/app/services/llm_service.py#L164-L179)):
- Auto-detects Spanish vs English based on keyword matching
- Spanish indicators: 'qué', 'cómo', 'cuándo', 'dónde', 'por qué', etc.
- Can be overridden via `language` parameter in request

**Context Truncation**:
- Max context length configurable via `MAX_CONTEXT_LENGTH` env var (default: 1500 chars)
- Prevents timeouts with large document sets
- Fallback model handling if requested model unavailable

#### User Service ([user_service.py](CODE/app/services/user_service.py))

**Auto-User Creation**:
- When user logs in via Auth0, backend checks if user exists in MongoDB
- If not, creates new user document with Auth0 ID, email, role
- Role extracted from JWT token using multi-strategy approach
- Default role: student (unless admin role in token)

**Statistics Tracking**:
- Upload count and storage bytes (incremented on file upload)
- Query count (incremented on RAG query)
- Last activity timestamp
- Feedback stats (likes/dislikes given)

**Admin Operations**:
- List all users with pagination
- View user details and statistics
- System-wide statistics aggregation

### Service Singleton Pattern

Each service module exports a global singleton instance:
- `llm_service` (LLMService)
- `rag_service` (RAGService)
- `file_service` (FileService) - initialized with database
- `user_service` (UserService) - initialized with database
- `conversation_service` (ConversationService) - initialized in [main.py](CODE/app/main.py) startup

Routes inject services via FastAPI dependencies ([dependencies.py](CODE/app/api/dependencies.py)).

### Startup Lifecycle ([main.py](CODE/app/main.py))

**On Application Startup**:
1. Connect to MongoDB ([database.py:connect()](CODE/app/db/database.py#L20))
2. Initialize conversation service with database
3. Create indexes (auto-created on first query)
4. Log successful initialization

**On Application Shutdown**:
1. Disconnect from MongoDB gracefully
2. Close connection pools

## Configuration

All configuration is centralized in [config.py](CODE/app/core/config.py). Settings are loaded from environment variables.

**Environment File Location**:
- Root `.env` file (loaded by docker-compose.yml)
- Variables prefixed with `VITE_` are for frontend (public, embedded in JS)
- Variables without prefix are for backend (sensitive, server-only)

**Key Settings**:

```bash
# Auth0 Configuration (Backend - SENSITIVE)
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_AUDIENCE=https://your-api-audience
AUTH0_CLIENT_ID=your_backend_client_id
AUTH0_CLIENT_SECRET=your_backend_client_secret  # NEVER COMMIT!

# Auth0 Configuration (Frontend - PUBLIC)
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your_frontend_client_id
VITE_AUTH0_AUDIENCE=https://your-api-audience
VITE_AUTH0_REDIRECT_URI=http://localhost:3000

# MongoDB Configuration
MONGO_URI=mongodb://admin:password@mongodb:27017/?authSource=admin
MONGO_DATABASE_NAME=study_planning
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=password  # CHANGE IN PRODUCTION!

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama2:latest

# RAG Configuration
DEFAULT_LANGUAGE=spanish  # Options: auto, spanish, english
RESPONSE_INSTRUCTIONS=  # Custom instructions for LLM responses
MAX_CONTEXT_LENGTH=1500  # Max chars of context sent to LLM
UPLOAD_DIR=data/uploads
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CHUNKS_FOR_CONTEXT=5
EMBEDDING_MODEL=all-MiniLM-L6-v2

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

## Working with the Codebase

### Adding a New Endpoint

1. **Define request/response models** in [app/models/requests.py](CODE/app/models/requests.py) and [responses.py](CODE/app/models/responses.py)
2. **Add business logic** to appropriate service in [app/services/](CODE/app/services/)
3. **Create route handler** in [app/api/routes/](CODE/app/api/routes/)
4. **Add authentication** using `Depends(get_current_user)` or `Depends(get_current_admin)`
5. **Include router** in [main.py](CODE/app/main.py): `app.include_router(your_router)`

### Adding Auth0 Role-Based Access

**Setting User Role in Auth0**:
1. Go to Auth0 Dashboard → User Management → Users
2. Select user → Roles tab → Assign Role
3. Or add to JWT token via Auth0 Action/Rule

**Checking Role in Endpoint**:
```python
from app.api.dependencies import get_current_admin, get_current_user

# Admin-only endpoint
@router.get("/admin-only")
async def admin_endpoint(
    current_user: UserInDB = Depends(get_current_admin)
):
    # Only admins can access
    pass

# Any authenticated user
@router.get("/authenticated")
async def user_endpoint(
    current_user: UserInDB = Depends(get_current_user)
):
    # Any authenticated user can access
    # Check current_user.role if needed
    pass
```

### Adding New File Types

1. Add extension to `allowed_extensions` in [config.py](CODE/app/core/config.py)
2. Add LangChain loader in [rag_service.py:_load_document()](CODE/app/services/rag_service.py#L73)
3. Add description in [file_service.py:get_supported_extensions()](CODE/app/services/file_service.py#L35)

### Modifying RAG Behavior

- **Chunk size/overlap**: Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` in `.env`
- **Number of results**: Change `MAX_CHUNKS_FOR_CONTEXT` in `.env`
- **Embedding model**: Update `EMBEDDING_MODEL` (must be SentenceTransformer compatible)
- **User filtering**: Modify `_get_user_filter()` in [rag_service.py](CODE/app/services/rag_service.py)

### Adding Database Collections

1. **Define collection name** in [collections.py](CODE/app/db/collections.py)
2. **Create Pydantic model** in [models.py](CODE/app/db/models.py)
3. **Create service class** in [app/services/](CODE/app/services/)
4. **Add dependency** in [dependencies.py](CODE/app/api/dependencies.py)
5. **Create indexes** (if needed) in service `__init__` or startup event

### Managing MongoDB

```bash
# Access MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p password

# Switch to database
use study_planning

# View collections
show collections

# Query users
db.users.find().pretty()

# Find user by email
db.users.findOne({email: "user@example.com"})

# Update user role to admin
db.users.updateOne(
  {auth0_id: "auth0|123456789"},
  {$set: {role: "admin"}}
)

# View conversations for user
db.conversations.find({auth0_id: "auth0|123456789"}).pretty()

# Count total documents
db.users.countDocuments()
db.conversations.countDocuments()
db.messages.countDocuments()

# Create index (if needed)
db.users.createIndex({auth0_id: 1}, {unique: true})
db.file_metadata.createIndex({user_id: 1})
db.conversations.createIndex({auth0_id: 1, updated_at: -1})
```

## Data Flow

### User Authentication Flow

1. Frontend redirects to Auth0 login
2. User authenticates with Auth0
3. Auth0 redirects to frontend with authorization code
4. Frontend exchanges code for JWT access token
5. Frontend includes token in API requests: `Authorization: Bearer <token>`
6. Backend dependency `get_current_user()` verifies token → [dependencies.py:79](CODE/app/api/dependencies.py#L79)
7. Auth service verifies JWT with Auth0 JWKS → [security.py:verify_token()](CODE/app/core/security.py#L76)
8. User service gets or creates user in MongoDB → [auth_service.py](CODE/app/services/auth_service.py)
9. Request proceeds with authenticated `UserInDB` object

### Document Upload Flow

1. File uploaded via `POST /files/upload/` → [files.py](CODE/app/api/routes/files.py)
2. User authenticated and role checked
3. File validated (extension, size) → [file_service.py](CODE/app/services/file_service.py)
4. File saved to disk (`uploads/` directory or volume)
5. File metadata saved to MongoDB with user_id and is_public flag
6. File processed into chunks → [rag_service.py:process_document()](CODE/app/services/rag_service.py#L98)
7. Chunks embedded and stored in ChromaDB with user_id and is_public metadata
8. User statistics incremented (upload count, storage bytes)
9. Response returned with file metadata

### Query Flow (with Conversation History)

1. Query received via `POST /rag/query/` → [rag.py:76-126](CODE/app/api/routes/rag.py#L76-L126)
2. User authenticated and user_id extracted
3. If `conversation_id` provided, retrieve conversation history → [conversation_service.py](CODE/app/services/conversation_service.py)
4. If no `conversation_id`, create new conversation with auto-generated title
5. Query embedded using SentenceTransformer
6. ChromaDB similarity search with user filtering (user's private files + public files)
7. Top N chunks retrieved and context assembled → [rag_service.py:generate_context()](CODE/app/services/rag_service.py#L181)
8. LLM generates answer using context + history → [llm_service.py:generate_with_context()](CODE/app/services/llm_service.py#L129)
9. User message added to conversation → [conversation_service.py:add_message()](CODE/app/services/conversation_service.py#L103)
10. Assistant message added to conversation with sources
11. User statistics incremented (query count, last activity)
12. Response returned with answer, sources, chunks, and conversation_id

### Feedback Submission Flow

1. Feedback submitted via `POST /feedback/` → [feedback.py](CODE/app/api/routes/feedback.py)
2. User authenticated
3. Verify conversation and message belong to user
4. Create feedback document in MongoDB
5. Update file metadata feedback stats (if source files identified)
6. User statistics incremented (feedback count)
7. Response returned with confirmation

## Docker Architecture

### Named Volumes (Persistent Data)

- **`uploads`**: User-uploaded documents (`CODE/data/uploads`)
- **`chroma_db`**: Vector database with embeddings (`CODE/data/chroma_db`)
- **`ollama-models`**: Downloaded LLM models (~2-4GB per model)
- **`mongo-data`**: MongoDB database files (users, conversations, feedback)

### Bind Mount (Development Only)

- `./CODE:/app`: Backend source code hot-reload
- `./FRONTEND:/app`: Frontend source code (for dev)

### Development Workflow

**Making Code Changes**:
1. Edit files in `CODE/` (backend) or `FRONTEND/` (frontend) directory
2. Backend changes auto-reload (hot-reload enabled)
3. Frontend requires rebuild: `docker compose up --build frontend`
4. NO rebuild needed for backend code changes
5. Only rebuild when dependencies change: `docker compose up --build`

**When to Rebuild**:
- Changed `CODE/requirements.txt`: Rebuild backend
- Changed `FRONTEND/package.json`: Rebuild frontend
- Changed Dockerfile: Rebuild respective service
- Changed docker-compose.yml: Restart services
- Changed code only: No rebuild needed (bind mount for backend)

### GPU Support

**NVIDIA GPU Acceleration** (Optional):
- Ollama container configured to use NVIDIA GPUs for faster inference
- Requires: NVIDIA GPU, drivers (450.80.02+), NVIDIA Container Toolkit
- Automatic CPU fallback if GPU not available

**Install NVIDIA Container Toolkit (Fedora/RHEL)**:
```bash
sudo dnf config-manager --add-repo https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**Verify GPU Access**:
```bash
nvidia-smi
docker run --rm --gpus all ubuntu nvidia-smi
docker exec study-planning-ollama nvidia-smi
```

## Important Notes

- **Auth0 Required**: All API endpoints (except `/`, `/health`) require valid JWT token
- **Multi-Tenancy**: Files are isolated by user (private) or shared (public)
- **Conversation Context**: History automatically included when conversation_id provided
- **Role Assignment**: New users default to "student" role, assign "admin" in Auth0 or MongoDB
- **ChromaDB Filtering**: Vector search automatically filtered by user permissions
- **MongoDB Async**: All database operations use Motor (async MongoDB driver)
- **CORS**: Configured for frontend origin (http://localhost:3000)
- **Environment Variables**: Root `.env` file used by all services
- **Docker Paths**: All paths relative to `/app` inside containers
- **Native Paths**: All paths assume execution from `CODE/` directory
- **OpenAPI Docs**: Available at `/docs` (Swagger) and `/redoc` (ReDoc)
