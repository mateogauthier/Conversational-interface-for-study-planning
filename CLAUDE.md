# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a RAG-powered Study Planning API that allows students to upload study materials and query them using Retrieval-Augmented Generation. The system combines vector-based semantic search (ChromaDB) with LLM responses (Ollama) to provide intelligent answers based on uploaded documents.

## Essential Commands

### Docker (Recommended)

**Important**: Use `docker compose` (with space) not `docker-compose` (with hyphen).

```bash
# Development (with hot-reload) - run from repository root
docker compose up
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
docker compose logs -f ollama

# Access container shell
docker exec -it study-planning-api bash
docker exec -it study-planning-ollama bash

# Pull Ollama model manually
docker exec study-planning-ollama ollama pull llama2:latest
```

**See [DOCKER-QUICKSTART.md](DOCKER-QUICKSTART.md) for detailed Docker usage guide.**

### Native Development (Without Docker)

```bash
# Start the API server (from CODE/ directory)
./scripts/start_server.sh
# This script handles virtual environment activation, dependency checks,
# Ollama service startup, and launches FastAPI at http://localhost:8000

# Alternative: Manual server start
cd CODE
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Testing

```bash
# With Docker (run inside container)
docker exec study-planning-api python tests/test_direct.py

# Native (direct on host)
cd CODE
python tests/test_direct.py

# API endpoint tests (server must be running)
python tests/test_rag.py

# Full system demonstration
python tests/demo_rag.py
```

### Dependencies

```bash
# Docker automatically handles dependencies

# Native: Install all dependencies
cd CODE
pip install -r requirements.txt
```

## Architecture

### Three-Layer Service Architecture

The application follows a clean separation of concerns:

1. **API Layer** ([app/api/routes/](CODE/app/api/routes/))
   - [files.py](CODE/app/api/routes/files.py): File upload, listing, deletion
   - [rag.py](CODE/app/api/routes/rag.py): RAG search and query endpoints
   - [llm.py](CODE/app/api/routes/llm.py): Direct LLM interaction endpoints

2. **Service Layer** ([app/services/](CODE/app/services/))
   - [file_service.py](CODE/app/services/file_service.py): File validation, storage, metadata management
   - [rag_service.py](CODE/app/services/rag_service.py): Document processing, embedding, vector search
   - [llm_service.py](CODE/app/services/llm_service.py): Ollama integration, prompt construction, language detection

3. **Core Layer** ([app/core/](CODE/app/core/))
   - [config.py](CODE/app/core/config.py): Centralized configuration with environment variable support
   - [exceptions.py](CODE/app/core/exceptions.py): Custom exception hierarchy

### Key Technical Details

**RAG Pipeline** ([rag_service.py:98-148](CODE/app/services/rag_service.py#L98-L148)):
1. Documents are loaded via LangChain loaders (PDF, Word, Excel, Text, Markdown)
2. Text is split into chunks using `RecursiveCharacterTextSplitter` (default: 1000 chars, 200 overlap)
3. Chunks are embedded using SentenceTransformer (`all-MiniLM-L6-v2`)
4. Embeddings are stored in ChromaDB with metadata (source file, chunk index)
5. Queries are embedded and matched using cosine similarity

**LLM Integration** ([llm_service.py:129-162](CODE/app/services/llm_service.py#L129-L162)):
- The `generate_with_context()` method constructs prompts with retrieved context
- Automatic language detection based on Spanish indicators in queries
- Context truncation to prevent timeouts (configurable via `MAX_CONTEXT_LENGTH` env var)
- Fallback model handling if requested model is unavailable

**Service Singleton Pattern**:
Each service module exports a global singleton instance (e.g., `rag_service`, `llm_service`, `file_service`). Routes inject these via FastAPI dependencies ([app/api/dependencies.py](CODE/app/api/dependencies.py)).

## Configuration

All configuration is centralized in [app/core/config.py](CODE/app/core/config.py). Key settings can be overridden via environment variables in `CODE/.env`:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:latest
UPLOAD_DIR=data/uploads
DEFAULT_LANGUAGE=auto  # Options: auto, spanish, english
RESPONSE_INSTRUCTIONS=  # Custom instructions for LLM responses
MAX_CONTEXT_LENGTH=1500  # Max chars of context sent to LLM
```

## Working with the Codebase

### Adding New File Types

1. Add extension to `allowed_extensions` in [config.py:29](CODE/app/core/config.py#L29)
2. Add loader logic in [rag_service.py:73-96](CODE/app/services/rag_service.py#L73-L96)
3. Add description in [file_service.py:35-46](CODE/app/services/file_service.py#L35-L46)

### Modifying RAG Behavior

- **Chunk size/overlap**: Adjust `chunk_size` and `chunk_overlap` in [config.py:35-36](CODE/app/core/config.py#L35-L36)
- **Number of results**: Change `max_chunks_for_context` in [config.py:37](CODE/app/core/config.py#L37)
- **Embedding model**: Update `embedding_model` in [config.py:34](CODE/app/core/config.py#L34) (must be compatible with SentenceTransformer)

### Language Detection Logic

The system auto-detects Spanish vs English based on keyword matching ([llm_service.py:164-179](CODE/app/services/llm_service.py#L164-L179)). Spanish indicators include: 'qué', 'cómo', 'cuándo', 'dónde', 'por qué', etc.

### Ollama Service Management

The [start_server.sh](CODE/scripts/start_server.sh) script attempts multiple methods to start Ollama:
1. Using [manage_ollama.sh](CODE/scripts/manage_ollama.sh) helper
2. Via systemctl (if installed as system service)
3. Direct background process (`ollama serve`)
4. Docker container

If Ollama is not available, the API will still start but LLM endpoints will return appropriate errors.

## Data Flow

**Document Upload Flow**:
1. File uploaded via `POST /files/upload/` → [files.py](CODE/app/api/routes/files.py)
2. File validated and saved → [file_service.py](CODE/app/services/file_service.py)
3. File processed into chunks → [rag_service.py:process_document()](CODE/app/services/rag_service.py#L98)
4. Chunks embedded and stored in ChromaDB

**Query Flow**:
1. Query received via `POST /rag/query/` → [rag.py:76-126](CODE/app/api/routes/rag.py#L76-L126)
2. Query embedded and similar chunks retrieved → [rag_service.py:retrieve_relevant_chunks()](CODE/app/services/rag_service.py#L150)
3. Context generated from chunks → [rag_service.py:generate_context()](CODE/app/services/rag_service.py#L181)
4. LLM generates answer using context → [llm_service.py:generate_with_context()](CODE/app/services/llm_service.py#L129)
5. Response returned with sources and relevant chunks

## Docker Architecture

### Container Services

**Two-Container Architecture**:
1. **fastapi-app**: The main application (FastAPI + ChromaDB + SentenceTransformer)
   - Port: 8000 (exposed to host)
   - Depends on: ollama service
   - Volumes: source code (dev only), uploads, chroma_db

2. **ollama**: LLM service (Ollama with models)
   - Port: 11434 (exposed in dev, internal-only in prod)
   - Volumes: ollama-models (persists downloaded models)
   - Optional: GPU support (uncomment deploy section in docker-compose.yml)

### Volume Management

**Named Volumes** (persist data across container restarts):
- `uploads`: User-uploaded documents (CODE/data/uploads)
- `chroma_db`: Vector database with embeddings (CODE/data/chroma_db)
- `ollama-models`: Downloaded LLM models (~2GB+ per model)

**Bind Mount** (development only):
- `./CODE:/app`: Source code hot-reload (changes reflected immediately)

### Development Workflow

**Making Code Changes**:
1. Edit files in `CODE/` directory
2. Changes are automatically reflected (hot-reload enabled)
3. NO rebuild needed for code changes
4. Only rebuild when dependencies change: `docker-compose up --build`

**When to Rebuild**:
- Changed `requirements.txt`: Rebuild required
- Changed Dockerfile: Rebuild required
- Changed code only: No rebuild needed (bind mount)

**Managing Data**:
```bash
# Backup uploads volume
docker run --rm -v study-planning-api_uploads:/data -v $(pwd):/backup ubuntu tar czf /backup/uploads-backup.tar.gz -C /data .

# Restore uploads volume
docker run --rm -v study-planning-api_uploads:/data -v $(pwd):/backup ubuntu tar xzf /backup/uploads-backup.tar.gz -C /data

# Reset all data (WARNING: deletes everything)
docker-compose down -v
```

### Docker vs Native Development

**Use Docker when**:
- You want consistent environment across team
- You don't want to install Ollama/Python locally
- You're deploying to production
- You need GPU support for Ollama

**Use Native when**:
- You're debugging low-level issues
- You need faster iteration (no container overhead)
- You're testing Ollama configurations
- Docker is not available

## Important Notes

- **Docker**: All paths are relative to `/app` inside container
- **Native**: All paths assume execution from the `CODE/` directory as the working directory
- The virtual environment must be activated before running any Python scripts (native only)
- ChromaDB data is persisted in `CODE/data/chroma_db/` (native) or `chroma_db` volume (Docker)
- Uploaded files are stored in `CODE/data/uploads/` (native) or `uploads` volume (Docker)
- The API uses FastAPI's automatic OpenAPI documentation at `/docs` and `/redoc`
- **Docker entrypoint**: [docker-entrypoint.sh](CODE/scripts/docker-entrypoint.sh) waits for Ollama and pulls default model
- **Environment variables**: Set in docker-compose.yml (Docker) or CODE/.env (native)
