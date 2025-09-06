# RAG-Enhanced Study Planning API

This API provides a Retrieval-Augmented Generation (RAG) system for study planning with document upload and intelligent querying capabilities.

## Features

- **Document Upload**: Support for PDF, Word, Excel, Text, and Markdown files
- **RAG Processing**: Automatic document chunking and vector embedding
- **Intelligent Search**: Semantic search across uploaded documents
- **LLM Integration**: Combines retrieved context with Ollama LLM responses
- **File Management**: Upload, list, and delete files with metadata

## API Endpoints

### Core Functionality

#### `POST /upload/`
Upload documents for RAG processing.
- **Body**: Multipart form data with file
- **Supported formats**: PDF, DOC/DOCX, XLS/XLSX, TXT, MD
- **Response**: Upload status and processing result

#### `POST /rag-llm/`
Query documents with RAG + LLM completion.
- **Body**: 
  ```json
  {
    "prompt": "Your question here",
    "n_results": 5,
    "model": "llama2"
  }
  ```
- **Response**: Answer with context and sources

#### `POST /rag/`
Query documents using RAG only (no LLM).
- **Body**:
  ```json
  {
    "prompt": "Your question here",
    "n_results": 5,
    "use_llm": false
  }
  ```
- **Response**: Relevant document chunks and context

#### `POST /llm-request/`
Direct LLM query without RAG.
- **Body**:
  ```json
  {
    "prompt": "Your question here",
    "model": "llama2"
  }
  ```
- **Response**: Direct LLM response

### File Management

#### `GET /files/`
List all uploaded files with metadata.
- **Response**: Array of file information including size, type, dates

#### `GET /files/{filename}`
Get detailed information about a specific file.
- **Response**: File metadata and statistics

#### `DELETE /files/{filename}`
Delete a specific file.
- **Response**: Deletion confirmation

### System Information

#### `GET /rag-stats/`
Get RAG system statistics.
- **Response**: Collection info, document count, embedding model

#### `GET /health/`
Health check endpoint.
- **Response**: API status

## Setup and Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file:
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```

3. **Start the Server**:
   ```bash
   python main.py
   ```
   Or with uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Usage Examples

### Upload a Document
```bash
curl -X POST "http://localhost:8000/upload/" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_document.pdf"
```

### Query with RAG + LLM
```bash
curl -X POST "http://localhost:8000/rag-llm/" \
     -H "accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "What are the main concepts in machine learning?",
       "n_results": 5
     }'
```

### List Files
```bash
curl -X GET "http://localhost:8000/files/" \
     -H "accept: application/json"
```

## Testing

Run the test script to verify functionality:
```bash
python test_rag.py
```

## Architecture

### Components

1. **RAG Engine** (`rag/rag_engine.py`):
   - Document loading and processing
   - Text chunking and embedding
   - Vector storage with ChromaDB
   - Semantic search and retrieval

2. **File Utilities** (`file_utils.py`):
   - File upload and validation
   - File type detection
   - Metadata extraction

3. **Ollama Client** (`ollama_client.py`):
   - LLM integration
   - Model management
   - Response generation

4. **Main API** (`main.py`):
   - FastAPI endpoints
   - Request/response handling
   - Error management

### Vector Storage

- **Database**: ChromaDB (persistent storage)
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Chunking**: Recursive character splitter (1000 chars, 200 overlap)
- **Search**: Cosine similarity

## Configuration

### Supported File Types
- PDF documents
- Microsoft Word (DOC, DOCX)
- Microsoft Excel (XLS, XLSX)
- Text files (TXT)
- Markdown files (MD)

### Environment Variables
- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Default model name (default: llama2)

## Error Handling

The API provides comprehensive error handling with appropriate HTTP status codes:
- 400: Bad request (unsupported file type, validation errors)
- 404: Resource not found
- 500: Internal server error

## Performance Considerations

- Documents are processed asynchronously during upload
- Vector embeddings are cached in ChromaDB
- Large documents are automatically chunked for optimal retrieval
- File type validation prevents processing of unsupported formats

## Security Notes

- File uploads are validated for supported types
- CORS is configured (adjust for production)
- No authentication implemented (add as needed)
- Files are stored locally in `uploads/` directory
