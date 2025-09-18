# RAG-powered Study Planning API

A FastAPI-based conversational interface for study planning that uses Retrieval-Augmented Generation (RAG) to help students interact with their study materials.

## Features

- 📁 **File Upload**: Support for PDF, Word, Excel, text, and Markdown files
- 🔍 **Intelligent Search**: Vector-based semantic search through documents
- 🤖 **RAG Integration**: Uses Ollama for LLM responses with retrieved context
- 📊 **Document Management**: Track and manage uploaded study materials
- 🌐 **RESTful API**: Clean endpoints with automatic documentation
- 🔄 **Auto-Service Management**: Automatic Ollama service startup

## Project Structure

```
CODE/
├── app/                    # Main application package
│   ├── main.py            # FastAPI application entry point
│   ├── api/               # API layer
│   │   ├── routes/        # API route modules
│   │   │   ├── files.py   # File upload/management endpoints
│   │   │   ├── llm.py     # LLM interaction endpoints
│   │   │   └── rag.py     # RAG query endpoints
│   │   └── __init__.py
│   ├── core/              # Core configuration and utilities
│   │   ├── config.py      # Application settings
│   │   ├── exceptions.py  # Custom exception classes
│   │   └── __init__.py
│   ├── models/            # Pydantic models
│   │   ├── requests.py    # Request models
│   │   ├── responses.py   # Response models
│   │   └── __init__.py
│   ├── services/          # Business logic layer
│   │   ├── file_service.py    # File handling service
│   │   ├── llm_service.py     # LLM interaction service
│   │   ├── rag_service.py     # RAG processing service
│   │   └── __init__.py
│   └── utils/             # Utility modules
│       └── __init__.py
├── data/                  # Data storage
│   ├── uploads/           # Uploaded files
│   └── chroma_db/         # Vector database
├── scripts/               # Utility scripts
│   ├── start_server.sh    # Server startup script
│   └── manage_ollama.sh   # Ollama management script
├── tests/                 # Test files
│   ├── test_direct.py     # Direct functionality tests
│   ├── test_rag.py        # API endpoint tests
│   └── demo_rag.py        # Full system demonstration
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Make script executable
chmod +x scripts/start_server.sh

# Start the API server (includes automatic Ollama setup)
./scripts/start_server.sh
```

The script will:
- Activate the virtual environment
- Check and install dependencies
- Create necessary directories
- Start Ollama service automatically
- Launch the FastAPI server at http://localhost:8000

### 3. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health/

## API Endpoints

### File Management
- `POST /files/upload/` - Upload study documents
- `GET /files/` - List uploaded files
- `GET /files/{filename}/info/` - Get file metadata
- `DELETE /files/{filename}/` - Delete a file

### RAG Operations
- `POST /rag/query/` - Query documents with RAG
- `GET /rag/stats/` - Get collection statistics

### LLM Integration
- `POST /llm/chat/` - Direct LLM interaction
- `GET /llm/models/` - List available models

## Usage Examples

### Upload a Document
```bash
curl -X POST "http://localhost:8000/files/upload/" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your-study-notes.pdf"
```

### Query with RAG
```bash
curl -X POST "http://localhost:8000/rag/query/" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What are the main topics in machine learning?",
       "max_results": 5
     }'
```

## Testing

### Run Direct Tests (No Server Required)
```bash
python tests/test_direct.py
```

### Run API Tests (Server Must Be Running)
```bash
python tests/test_rag.py
```

### Full System Demo
```bash
python tests/demo_rag.py
```

## Configuration

Key settings in `app/core/config.py`:

- **UPLOAD_DIR**: Directory for uploaded files
- **CHROMADB_PATH**: Vector database storage location
- **COLLECTION_NAME**: ChromaDB collection name
- **EMBEDDING_MODEL**: Sentence transformer model
- **CHUNK_SIZE**: Text splitting chunk size
- **OLLAMA_BASE_URL**: Ollama service URL

## Supported File Types

- **PDF**: `.pdf`
- **Word Documents**: `.doc`, `.docx`
- **Excel Files**: `.xls`, `.xlsx`
- **Text Files**: `.txt`
- **Markdown**: `.md`

## Requirements

- Python 3.8+
- Ollama (automatically managed)
- 4GB+ RAM recommended
- 2GB+ disk space for models

## Development

The application follows a clean architecture pattern:

- **API Layer** (`app/api/`): HTTP endpoints and request handling
- **Service Layer** (`app/services/`): Business logic and external integrations
- **Core Layer** (`app/core/`): Configuration and shared utilities
- **Models Layer** (`app/models/`): Data validation and serialization

## Troubleshooting

### Ollama Issues
```bash
# Check Ollama status
./scripts/manage_ollama.sh status

# Manually start Ollama
./scripts/manage_ollama.sh start
```

### Port Already in Use
```bash
# Change port in start_server.sh or use:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### Missing Dependencies
```bash
pip install -r requirements.txt
```

## Default .env
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:latest
UPLOAD_DIR=data/uploads
```