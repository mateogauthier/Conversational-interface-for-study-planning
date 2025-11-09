# RAG-powered Study Planning API

A complete study planning system with a modern React frontend and FastAPI backend that uses Retrieval-Augmented Generation (RAG) to help students interact with their study materials. Upload documents, ask questions, and get intelligent answers backed by your own content.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb.svg)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-FF6B6B.svg)](https://ollama.ai)

## Features

- 🎨 **Modern React Frontend**: Beautiful, responsive UI with drag-and-drop upload and chat interface
- 📁 **Multi-format Document Upload**: PDF, Word, Excel, text, and Markdown files
- 🔍 **Semantic Search**: Vector-based search using ChromaDB and sentence transformers
- 🤖 **RAG with LLM**: Intelligent responses powered by Ollama (llama2, mistral, etc.)
- 🌍 **Multi-language Support**: Auto-detect or specify response language (English/Spanish)
- 🐳 **Docker Ready**: One-command deployment with hot-reload for development
- 📊 **Document Management**: Track, query, and manage your study materials
- 🔄 **RESTful API**: Clean endpoints with automatic OpenAPI documentation
- 💾 **Persistent Storage**: Docker volumes for uploads, embeddings, and models

## Quick Start

### Docker (Recommended)

**Prerequisites:** Docker Desktop with **10GB+ memory** allocated

```bash
# Clone the repository
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning

# Start the application (development mode with hot-reload)
docker compose up

# Or run in background
docker compose up -d

# View logs
docker compose logs -f
```

**First startup**: Docker will build the containers (~5-10 min) and Ollama will download the llama2 model (~4GB, 10-20 min). Subsequent starts are much faster.

**Access the Application:**
- 🎨 **Frontend (Web UI)**: http://localhost:3000
- 🌐 **Backend API**: http://localhost:8000
- 📚 **API Documentation**: http://localhost:8000/docs
- 📖 **Alternative Docs**: http://localhost:8000/redoc

**Important**: If you get a 503 error when querying the LLM, you need to increase Docker Desktop's memory allocation to at least 10GB in Settings → Resources. See the [Troubleshooting](#troubleshooting) section below.

### Native Setup (Without Docker)

<details>
<summary>Click to expand native installation instructions</summary>

**Requirements:**
- Python 3.8+
- Ollama installed locally
- 4GB+ RAM

```bash
cd CODE

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
./scripts/start_server.sh
# Or manually:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

</details>

## Usage Examples

### 1. Upload Documents

```bash
# Upload a PDF
curl -X POST "http://localhost:8000/files/upload" \
  -F "file=@study-notes.pdf"

# Upload multiple files
curl -X POST "http://localhost:8000/files/upload" \
  -F "file=@chapter1.pdf" \
  -F "file=@chapter2.docx"
```

### 2. Query with RAG + LLM

```bash
# Ask a question (get AI-generated answer with sources)
curl -X POST "http://localhost:8000/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the main topics in machine learning?",
    "n_results": 5,
    "language": "auto"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "RAG query with LLM completion successful",
  "query": "What are the main topics in machine learning?",
  "answer": "Based on your documents, the main topics in machine learning include...",
  "context_used": "Retrieved context from your documents...",
  "n_chunks_found": 5,
  "sources": ["study-notes.pdf", "ml-textbook.pdf"],
  "relevant_chunks": [...],
  "model_used": "llama2:latest"
}
```

### 3. Search Without LLM (Just Retrieval)

```bash
# Search for relevant chunks without AI answer
curl -X POST "http://localhost:8000/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "neural networks",
    "n_results": 3,
    "use_llm": false
  }'
```

### 4. Direct LLM Query (No RAG)

```bash
# Ask the LLM directly without document context
curl -X POST "http://localhost:8000/llm/query" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain gradient descent in simple terms."
  }'
```

### 5. Manage Files

```bash
# List all uploaded files
curl http://localhost:8000/files/

# Get file info
curl http://localhost:8000/files/study-notes.pdf

# Delete a file
curl -X DELETE http://localhost:8000/files/study-notes.pdf

# Get RAG statistics
curl http://localhost:8000/rag/stats
```

## API Endpoints

### 📁 File Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/files/upload` | Upload one or more documents |
| `GET` | `/files/` | List all uploaded files |
| `GET` | `/files/{filename}` | Get file metadata |
| `DELETE` | `/files/{filename}` | Delete a file and its embeddings |
| `GET` | `/files/supported/extensions` | List supported file types |

### 🔍 RAG Operations
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/rag/query` | Query with RAG + LLM (full answer) |
| `POST` | `/rag/search` | Search documents (retrieval only) |
| `GET` | `/rag/stats` | Get collection statistics |
| `POST` | `/rag/reset` | Clear all documents and embeddings |
| `GET` | `/rag/health` | Check RAG service status |

### 🤖 LLM Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/llm/query` | Direct LLM query (no RAG) |
| `GET` | `/llm/status` | Check LLM service status |
| `GET` | `/llm/models` | List available Ollama models |
| `POST` | `/llm/models/{model_name}/ensure` | Download/verify model |
| `GET` | `/llm/health` | Check LLM connectivity |

### ❤️ System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint |
| `GET` | `/health` | Overall health check |

## Frontend (Web UI)

The React frontend provides a user-friendly interface for all API features:

### Quick Access
- **Web Interface**: http://localhost:3000 (after running `docker compose up`)
- **Development Mode**: See [FRONTEND_QUICKSTART.md](FRONTEND_QUICKSTART.md)

### Pages
- **Home**: System dashboard with statistics and quick actions
- **Upload**: Drag-and-drop file upload with progress tracking
- **Query**: Chat interface for asking questions about your documents
- **Files**: Manage uploaded documents (view, delete)

### Development
```bash
# Start frontend dev server (with hot-reload)
cd FRONTEND
npm install
npm run dev
# Access at http://localhost:3000
```

For detailed frontend documentation, see:
- [FRONTEND/README.md](FRONTEND/README.md) - Complete frontend guide
- [FRONTEND_QUICKSTART.md](FRONTEND_QUICKSTART.md) - Quick start guide

## Docker Commands

```bash
# Development workflow
docker compose up              # Start all services (frontend + backend + LLM)
docker compose up -d           # Start in background
docker compose logs -f         # View logs
docker compose logs -f frontend # View frontend logs only
docker compose ps              # Check status
docker compose down            # Stop containers

# When dependencies change (requirements.txt or package.json)
docker compose up --build      # Rebuild and start

# Production deployment
docker compose -f docker-compose.prod.yml up -d

# Manage Ollama models
docker exec study-planning-ollama ollama list              # List models
docker exec study-planning-ollama ollama pull mistral      # Pull model
docker exec study-planning-ollama ollama pull tinyllama    # Small model

# Access container shells
docker exec -it study-planning-api bash
docker exec -it study-planning-ollama bash

# Clean restart (keeps data)
docker compose down && docker compose up -d

# Full reset (WARNING: deletes all data)
docker compose down -v
```

## Project Structure

```
Conversational-interface-for-study-planning/
├── CODE/                           # Application source code
│   ├── app/
│   │   ├── main.py                # FastAPI entry point
│   │   ├── api/
│   │   │   ├── dependencies.py    # Dependency injection
│   │   │   └── routes/
│   │   │       ├── files.py       # File upload/management
│   │   │       ├── llm.py         # LLM endpoints
│   │   │       └── rag.py         # RAG query endpoints
│   │   ├── core/
│   │   │   ├── config.py          # Settings & environment
│   │   │   └── exceptions.py      # Custom exceptions
│   │   ├── models/
│   │   │   ├── requests.py        # Request schemas
│   │   │   └── responses.py       # Response schemas
│   │   ├── services/
│   │   │   ├── file_service.py    # File handling logic
│   │   │   ├── llm_service.py     # Ollama integration
│   │   │   └── rag_service.py     # RAG & ChromaDB logic
│   │   └── utils/                 # Utility functions
│   ├── data/
│   │   ├── uploads/               # Uploaded files (Docker volume)
│   │   └── chroma_db/             # Vector database (Docker volume)
│   ├── scripts/
│   │   ├── docker-entrypoint.sh   # Container startup script
│   │   ├── start_server.sh        # Native server startup
│   │   └── manage_ollama.sh       # Ollama management
│   ├── tests/
│   │   ├── test_direct.py         # Unit tests
│   │   ├── test_rag.py            # API tests
│   │   └── demo_rag.py            # Full demo
│   └── requirements.txt           # Python dependencies
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Development setup
├── docker-compose.prod.yml         # Production setup
├── .dockerignore                   # Docker build exclusions
├── DOCKER-QUICKSTART.md            # Docker detailed guide
├── TROUBLESHOOTING.md              # Common issues & solutions
├── CLAUDE.md                       # Claude Code guidance
└── README.md                       # This file
```

## Architecture

### System Overview

```
┌─────────────────┐
│   Client API   │
│    Requests    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         FastAPI Application         │
│  ┌─────────────────────────────┐   │
│  │     API Routes Layer        │   │
│  │  /files  /rag  /llm         │   │
│  └────────────┬────────────────┘   │
│               │                     │
│  ┌────────────▼────────────────┐   │
│  │     Service Layer           │   │
│  │  • FileService              │   │
│  │  • RAGService               │   │
│  │  • LLMService               │   │
│  └──┬────────┬────────┬────────┘   │
│     │        │        │             │
└─────┼────────┼────────┼─────────────┘
      │        │        │
      ▼        ▼        ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Uploads  │ │ ChromaDB │ │  Ollama  │
│ (Volume) │ │ (Vector  │ │   LLM    │
│          │ │  Store)  │ │ Container│
└──────────┘ └──────────┘ └──────────┘
```

### RAG Query Flow

1. **Upload**: User uploads document → Parsed → Chunked → Embedded → Stored in ChromaDB
2. **Query**: User asks question → Embedded → Similar chunks retrieved → Context assembled
3. **Generate**: Context + Query → Ollama LLM → AI-generated answer → Returned with sources

### Docker Architecture

**Two-Container Setup:**
- **fastapi-app**: Main API (FastAPI + ChromaDB + Embeddings)
- **ollama**: LLM service (isolated, communicates via internal network)

**Named Volumes (Persistent):**
- `uploads`: User-uploaded documents
- `chroma_db`: Vector embeddings database
- `ollama-models`: Downloaded LLM models (~2-4GB each)

**Development Features:**
- Source code bind mount (`./CODE:/app`) enables hot-reload
- Code changes reflect instantly without rebuild
- Only rebuild when `requirements.txt` changes

## Configuration

### Environment Variables

Set in `docker-compose.yml` (Docker) or `CODE/.env` (native):

```bash
# Ollama LLM Configuration
OLLAMA_BASE_URL=http://ollama:11434    # Docker: service name
OLLAMA_MODEL=llama2:latest             # Default model

# Application Settings
UPLOAD_DIR=data/uploads                # Upload storage
DEFAULT_LANGUAGE=auto                  # Response language (auto/english/spanish)
RESPONSE_INSTRUCTIONS=                 # Custom LLM instructions
MAX_CONTEXT_LENGTH=1500                # Max context chars for RAG

# Advanced (optional)
CHROMADB_PATH=data/chroma_db           # Vector DB path
COLLECTION_NAME=study_materials        # ChromaDB collection
EMBEDDING_MODEL=all-MiniLM-L6-v2       # Sentence transformer model
CHUNK_SIZE=500                         # Text chunk size
CHUNK_OVERLAP=50                       # Chunk overlap
```

### Supported Models

**Recommended Models:**
- `llama2:latest` (3.8GB) - Default, good quality
- `mistral` (4.1GB) - Higher quality
- `phi` (1.6GB) - Faster, smaller
- `tinyllama` (600MB) - Minimal memory

**Change model:**
```bash
# In docker-compose.yml, change OLLAMA_MODEL environment variable
# Or pull and use on-demand:
docker exec study-planning-ollama ollama pull mistral
curl -X POST http://localhost:8000/rag/query \
  -d '{"prompt": "...", "model": "mistral"}'
```

## Supported File Types

| Type | Extensions | Supported |
|------|------------|-----------|
| **PDF** | `.pdf` | ✅ |
| **Word** | `.doc`, `.docx` | ✅ |
| **Excel** | `.xls`, `.xlsx` | ✅ |
| **Text** | `.txt` | ✅ |
| **Markdown** | `.md` | ✅ |

## Testing

```bash
# With Docker
docker exec study-planning-api python tests/test_direct.py     # Unit tests
docker exec study-planning-api python tests/test_rag.py        # API tests
docker exec study-planning-api python tests/demo_rag.py        # Full demo

# Native (from CODE/ directory)
python tests/test_direct.py
python tests/test_rag.py
python tests/demo_rag.py
```

## Troubleshooting

### 503 Error: "LLM service not available"

**Problem**: Ollama can't load the model due to insufficient memory.

**Solution**: Increase Docker Desktop memory to **8GB+**
1. Open Docker Desktop → Settings → Resources
2. Increase Memory slider to 8GB
3. Apply & Restart
4. Run: `docker compose down && docker compose up -d`

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

### Common Issues

```bash
# Check container status
docker compose ps

# View logs
docker compose logs -f fastapi-app
docker compose logs -f ollama

# Verify Ollama is working
curl http://localhost:11434/api/tags

# Check API health
curl http://localhost:8000/health

# Reset everything (clean slate)
docker compose down -v
docker compose up -d
```

## Development Workflow

### Making Code Changes (Docker)

1. Edit files in `CODE/` directory
2. **Changes auto-reload** - no rebuild needed!
3. View logs: `docker compose logs -f fastapi-app`

### When to Rebuild

```bash
# ONLY rebuild when:
# - Changed requirements.txt
# - Changed Dockerfile
# - Changed docker-compose.yml

docker compose up --build
```

### Adding Dependencies

```bash
# 1. Add to CODE/requirements.txt
echo "pandas" >> CODE/requirements.txt

# 2. Rebuild
docker compose up --build
```

## Production Deployment

```bash
# Use production compose file (no source bind mount, multiple workers)
docker compose -f docker-compose.prod.yml up -d

# Check logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

**Production differences:**
- No source code bind mount (uses baked-in code)
- 4 Uvicorn workers for concurrency
- Resource limits enforced
- Ollama port not exposed to host

## Requirements

### Docker Setup
- Docker Desktop with **8GB+ memory allocated**
- 10GB+ disk space (for images and models)

### Native Setup
- Python 3.8+
- Ollama installed locally
- 4GB+ RAM recommended
- 2GB+ disk space for models

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Commit: `git commit -m "Add feature"`
5. Push: `git push origin feature-name`
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - LLM application framework
- [Sentence Transformers](https://www.sbert.net/) - Embeddings library

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/Conversational-interface-for-study-planning/issues)
- **Documentation**: See `DOCKER-QUICKSTART.md` and `TROUBLESHOOTING.md`
- **API Docs**: http://localhost:8000/docs (when running)

---

**Made with ❤️ for students everywhere**
