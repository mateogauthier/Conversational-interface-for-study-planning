# Study Planning Conversational Interface

A complete study planning system powered by Retrieval-Augmented Generation (RAG) that helps students interact intelligently with their study materials. Upload documents, ask questions in natural language, and receive AI-generated answers backed by your own content—all secured with authentication and user management.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19+-61dafb.svg)](https://reactjs.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-LLM-FF6B6B.svg)](https://ollama.ai)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com)
[![Auth0](https://img.shields.io/badge/Auth0-Secured-EB5424.svg)](https://auth0.com)

## Features

### Core Functionality
- 🤖 **RAG-Powered Q&A**: Ask questions and get intelligent answers based on your uploaded documents
- 📁 **Multi-format Support**: PDF, Word, Excel, text, and Markdown files
- 🔍 **Semantic Search**: Vector-based search using ChromaDB and sentence transformers
- 🌍 **Multi-language**: Auto-detect or specify response language (English/Spanish)
- 💬 **Conversation History**: Track and manage all your queries and responses

### User Management & Security
- 🔐 **Auth0 Authentication**: Secure user authentication with JWT tokens
- 👤 **User Profiles**: Personal profiles with statistics and preferences
- 🔒 **Role-Based Access**: Student and admin roles with different permissions
- 📊 **Usage Analytics**: Track queries, feedback, and usage patterns

### Advanced Features
- 📝 **Enhanced Feedback System**:
  - Like/dislike ratings on assistant responses
  - Written comments for detailed feedback
  - Admin dashboard with pagination and filtering
  - LLM-powered feedback summarization
  - File-level statistics (views, usage, likes/dislikes)
- 🗂️ **File Management**: User-specific private files and admin-managed public files
- 👥 **Admin Dashboard**: Comprehensive admin tools for user and system management
- 🤖 **AI-Powered Insights**: Automated analysis of student feedback with actionable recommendations
- 🐳 **Production-Ready**: Docker deployment with MongoDB persistence and GPU support

### Technical Stack
- **Backend**: FastAPI with async operations
- **Database**: MongoDB for user data, conversations, and feedback
- **Vector Store**: ChromaDB for document embeddings
- **LLM**: Ollama (llama2, mistral, etc.) with GPU acceleration
- **Frontend**: React 19 with Auth0 integration
- **Deployment**: Docker Compose with hot-reload development

## Quick Start

### Prerequisites

- **Docker Desktop** with 10GB+ memory allocated
- **Auth0 Account** (free tier works perfectly)
- **10GB+ disk space** for Docker images and LLM models

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning
```

### 2. Configure Auth0

**Create Auth0 Application:**
1. Go to [Auth0 Dashboard](https://manage.auth0.com)
2. Create a new **Single Page Application** (for frontend)
3. Create a new **API** (for backend)
4. Create a new **Machine to Machine Application** (for backend client)
5. Note down the credentials

**Configure Application Settings:**
- **Allowed Callback URLs**: `http://localhost:3000`
- **Allowed Logout URLs**: `http://localhost:3000`
- **Allowed Web Origins**: `http://localhost:3000`

### 3. Setup Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your Auth0 credentials
nano .env  # or use any text editor
```

**Required Auth0 Variables in `.env`:**
```bash
# Frontend Auth0 Configuration (Public - embedded in JavaScript)
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your_frontend_client_id
VITE_AUTH0_AUDIENCE=https://your-api-audience
VITE_AUTH0_REDIRECT_URI=http://localhost:3000

# Backend Auth0 Configuration (SENSITIVE - Never commit!)
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_API_AUDIENCE=https://your-api-audience
AUTH0_CLIENT_ID=your_backend_client_id
AUTH0_CLIENT_SECRET=your_backend_client_secret  # KEEP SECRET!

# MongoDB Configuration
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=change_this_password  # Change in production!
MONGO_DATABASE_NAME=study_planning

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama2:latest
DEFAULT_LANGUAGE=spanish
```

### 4. Start the Application

```bash
# Start all services (first time will take 10-20 minutes)
docker compose up

# Or run in background
docker compose up -d

# View logs
docker compose logs -f
```

**First Startup Process:**
1. Docker builds containers (~5-10 minutes)
2. Ollama downloads llama2 model (~4GB, 10-20 minutes)
3. MongoDB initializes database
4. Services become available

### 5. Access the Application

Once all services are running:

- 🎨 **Frontend (Web UI)**: http://localhost:3000
- 🌐 **Backend API**: http://localhost:8000
- 📚 **API Documentation**: http://localhost:8000/docs
- 📖 **Alternative Docs**: http://localhost:8000/redoc
- 🗄️ **MongoDB**: mongodb://localhost:27017 (credentials from `.env`)

## Usage Guide

### Getting Started as a User

1. **Login**: Visit http://localhost:3000 and click "Login"
2. **Auth0 Authentication**: Sign up or log in through Auth0
3. **Upload Documents**: Navigate to "Upload" and drag & drop your study materials
4. **Ask Questions**: Go to "Query" and ask questions about your documents
5. **View History**: Check "Conversations" to see past queries and responses
6. **Manage Files**: View and delete your uploaded files in "Files"

### Admin Features

Admins have additional capabilities:

- **User Management**: View all users and their statistics
- **Public Files**: Upload files accessible to all students
- **System Statistics**: Monitor overall system usage
- **Model Management**: Download and manage LLM models

**Setting Admin Role:**
```bash
# Access the MongoDB container
docker exec -it study-planning-mongodb mongosh -u admin -p password

# Switch to database
use study_planning

# Make user admin (replace with actual Auth0 sub)
db.users.updateOne(
  { auth0_sub: "auth0|123456789" },
  { $set: { role: "admin" } }
)
```

## API Endpoints

### Authentication
All endpoints require Bearer token authentication (Auth0 JWT).

**Headers:**
```
Authorization: Bearer <your-auth0-jwt-token>
```

### File Management
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/files/upload` | Upload documents (private or public) | All/Admin |
| `GET` | `/files/` | List accessible files | All |
| `GET` | `/files/{filename}` | Get file metadata | All |
| `DELETE` | `/files/{filename}` | Delete file (with permission check) | All/Admin |
| `GET` | `/files/supported/extensions` | List supported file types | All |

### RAG Operations
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/rag/query` | Query with RAG + LLM (full answer) | All |
| `POST` | `/rag/search` | Search documents (retrieval only) | All |
| `GET` | `/rag/stats` | Get user-specific statistics | All |
| `POST` | `/rag/reset` | Reset public documents | Admin |
| `GET` | `/rag/health` | Check RAG service status | All |

### LLM Integration
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/llm/query` | Direct LLM query (no RAG) | All |
| `GET` | `/llm/status` | Check LLM service status | All |
| `GET` | `/llm/models` | List available models | All |
| `POST` | `/llm/models/{model}/ensure` | Download/verify model | Admin |
| `GET` | `/llm/health` | Check LLM connectivity | All |

### User Management
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/users/me` | Get current user profile | All |
| `GET` | `/users/me/stats` | Get current user statistics | All |
| `PATCH` | `/users/me` | Update user profile | All |

### Conversations
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/conversations/` | List user's conversations | All |
| `GET` | `/conversations/{id}` | Get conversation with messages | All |
| `DELETE` | `/conversations/{id}` | Delete conversation | All |

### Feedback
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `POST` | `/feedback/message` | Submit like/dislike with optional comment | All |
| `POST` | `/feedback/` | Submit general feedback | All |

### Admin Endpoints
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/admin/feedback` | List all feedback (paginated, filtered) | Admin |
| `GET` | `/admin/feedback/stats` | Get aggregated feedback statistics | Admin |
| `POST` | `/admin/feedback/summary` | Generate LLM summary of feedback | Admin |
| `GET` | `/admin/feedback/file/{filename}` | Get feedback for specific file | Admin |
| `GET` | `/admin/users` | List all users | Admin |
| `GET` | `/admin/users/{id}` | Get user details | Admin |
| `GET` | `/admin/users/{id}/stats` | Get user statistics | Admin |
| `GET` | `/admin/stats` | System-wide statistics | Admin |

### System
| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| `GET` | `/` | API information | All |
| `GET` | `/health` | System health check | All |

## API Usage Examples

### Upload a Document

```bash
# Get Auth0 token first (use your frontend or get from /docs)
TOKEN="your-auth0-jwt-token"

# Upload a private file (student)
curl -X POST "http://localhost:8000/files/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@study-notes.pdf"

# Upload a public file (admin only)
curl -X POST "http://localhost:8000/files/upload?is_public=true" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@shared-textbook.pdf"
```

### Query with RAG + LLM

```bash
curl -X POST "http://localhost:8000/rag/query" \
  -H "Authorization: Bearer $TOKEN" \
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
  "query": "What are the main topics in machine learning?",
  "answer": "Based on your documents, the main topics include...",
  "context_used": "Retrieved context from your documents...",
  "n_chunks_found": 5,
  "sources": ["study-notes.pdf"],
  "model_used": "llama2:latest",
  "conversation_id": "507f1f77bcf86cd799439011"
}
```

### Get User Profile

```bash
curl -X GET "http://localhost:8000/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

### Submit Feedback on Message

```bash
# Submit like/dislike with optional comment
curl -X POST "http://localhost:8000/feedback/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "507f1f77bcf86cd799439012",
    "feedback": "like",
    "comment": "Very helpful answer! This addressed my question perfectly."
  }'
```

### Submit General Feedback

```bash
# Submit standalone feedback
curl -X POST "http://localhost:8000/feedback/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "comment": "The system is great but could use better error messages",
    "rating": "dislike"
  }'
```

### Get Admin Feedback Statistics

```bash
curl -X GET "http://localhost:8000/admin/feedback/stats" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "success": true,
  "total_feedback": 127,
  "total_likes": 98,
  "total_dislikes": 29,
  "total_with_comments": 45,
  "top_users": [...],
  "top_files": [...],
  "recent_feedback": [...]
}
```

### Generate Feedback Summary

```bash
# Generate AI summary of feedback (filtered by rating)
curl -X POST "http://localhost:8000/admin/feedback/summary?rating=dislike&max_items=50" \
  -H "Authorization: Bearer $TOKEN"
```

**Response:**
```json
{
  "success": true,
  "summary": "**Overall Sentiment**: Mixed with concerns...\n\n**Key Themes**:\n1. Response accuracy...\n2. Speed of responses...\n\n**Actionable Suggestions**:\n- Improve context retrieval...",
  "item_count": 29,
  "generated_at": "2025-01-15T10:30:00Z",
  "filters_applied": {
    "rating": "dislike",
    "max_items": 50
  }
}
```

## Docker Architecture

### Services

The application runs as four interconnected Docker containers:

1. **frontend** (React + Nginx)
   - Port: 3000 → 80
   - Serves the React web interface
   - Built with Vite, served by Nginx

2. **fastapi-app** (FastAPI + ChromaDB)
   - Port: 8000
   - Main application backend
   - Handles RAG, file management, and API endpoints

3. **mongodb** (MongoDB 7.0)
   - Port: 27017
   - Stores users, conversations, feedback, and metadata
   - Persistent storage via `mongo-data` volume

4. **ollama** (Ollama LLM)
   - Port: 11434
   - Runs LLM models (llama2, mistral, etc.)
   - GPU-accelerated (with NVIDIA Container Toolkit)
   - Persistent models via `ollama-models` volume

### Volumes (Persistent Data)

- **`uploads`**: User-uploaded documents
- **`chroma_db`**: Vector embeddings database
- **`ollama-models`**: Downloaded LLM models (~2-4GB each)
- **`mongo-data`**: MongoDB database files

### Development Features

- **Hot-reload**: Code changes reflect instantly without rebuild
- **Bind mount**: `./CODE:/app` maps source code into container
- **Debug mode**: API runs with `--reload` flag

## Docker Commands

### Basic Operations

```bash
# Start all services
docker compose up

# Start in background
docker compose up -d

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f fastapi-app
docker compose logs -f frontend
docker compose logs -f mongodb

# Check status
docker compose ps

# Stop containers (keeps data)
docker compose down

# Stop and remove all data (WARNING: deletes everything)
docker compose down -v
```

### Development Workflow

```bash
# Code changes auto-reload - no rebuild needed!
# Just edit files in CODE/ or FRONTEND/

# Only rebuild when dependencies change:
docker compose up --build

# Restart a single service
docker compose restart fastapi-app

# Access container shell
docker exec -it study-planning-api bash
docker exec -it study-planning-mongodb mongosh -u admin -p password
```

### Managing Ollama Models

```bash
# List downloaded models
docker exec study-planning-ollama ollama list

# Pull a new model
docker exec study-planning-ollama ollama pull mistral
docker exec study-planning-ollama ollama pull phi

# Remove a model
docker exec study-planning-ollama ollama rm tinyllama
```

### Database Operations

```bash
# Access MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p password

# Backup database
docker exec study-planning-mongodb mongodump \
  --username admin --password password \
  --authenticationDatabase admin \
  --out /dump

# Backup to host
docker cp study-planning-mongodb:/dump ./mongodb-backup

# View logs
docker compose logs -f mongodb
```

## GPU Support (Optional)

The Ollama container supports NVIDIA GPU acceleration for faster inference.

### Prerequisites

1. **NVIDIA GPU** with CUDA support (GTX/RTX 10-series or newer)
2. **NVIDIA drivers** (version 450.80.02+)
3. **NVIDIA Container Toolkit**

### Install NVIDIA Container Toolkit (Fedora/RHEL)

```bash
# Add repository
sudo dnf config-manager --add-repo https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo

# Install toolkit
sudo dnf install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker
sudo systemctl restart docker
```

### Verify GPU Access

```bash
# Check NVIDIA drivers
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all ubuntu nvidia-smi

# Check Ollama container can see GPU
docker exec study-planning-ollama nvidia-smi
```

### Monitor GPU Usage

```bash
# Watch GPU utilization during inference
watch -n 1 nvidia-smi
```

**Note:** If GPU is not available, Ollama automatically falls back to CPU mode (slower but functional).

## Project Structure

```
Conversational-interface-for-study-planning/
├── .env                            # Your secrets (gitignored)
├── .env.example                    # Environment template
├── docker-compose.yml              # Development setup (4 services)
├── docker-compose.prod.yml         # Production setup
├── CODE/                           # Backend source code
│   ├── app/
│   │   ├── main.py                # FastAPI application entry point
│   │   ├── api/
│   │   │   ├── dependencies.py    # Auth & dependency injection
│   │   │   └── routes/
│   │   │       ├── files.py       # File upload/management
│   │   │       ├── llm.py         # LLM endpoints
│   │   │       ├── rag.py         # RAG query endpoints
│   │   │       ├── users.py       # User profile management
│   │   │       ├── admin.py       # Admin endpoints
│   │   │       ├── conversations.py # Conversation history
│   │   │       └── feedback.py    # Feedback submission
│   │   ├── core/
│   │   │   ├── config.py          # Settings & environment
│   │   │   ├── exceptions.py      # Custom exceptions
│   │   │   └── security.py        # Auth0 JWT verification
│   │   ├── db/
│   │   │   ├── database.py        # MongoDB connection
│   │   │   ├── models.py          # Database models
│   │   │   └── collections.py     # Collection schemas
│   │   ├── models/
│   │   │   ├── requests.py        # Request schemas
│   │   │   ├── responses.py       # Response schemas
│   │   │   └── user.py            # User models
│   │   ├── services/
│   │   │   ├── auth_service.py    # Auth0 integration
│   │   │   ├── user_service.py    # User management
│   │   │   ├── file_service.py    # File handling
│   │   │   ├── llm_service.py     # Ollama integration
│   │   │   ├── rag_service.py     # RAG & ChromaDB
│   │   │   └── conversation_service.py # Conversation tracking
│   │   └── utils/                 # Utility functions
│   ├── data/
│   │   ├── uploads/               # User files (volume)
│   │   └── chroma_db/             # Vector DB (volume)
│   ├── scripts/
│   │   ├── docker-entrypoint.sh   # Container startup
│   │   └── start_server.sh        # Native startup
│   ├── tests/
│   │   ├── test_direct.py         # Unit tests
│   │   └── test_rag.py            # API tests
│   ├── requirements.txt           # Python dependencies
│   └── Dockerfile                 # Backend Docker build
├── FRONTEND/                       # Frontend source code
│   ├── src/
│   │   ├── App.jsx                # Main React app
│   │   ├── components/            # React components
│   │   ├── pages/                 # Page components
│   │   ├── services/              # API client
│   │   └── auth/                  # Auth0 integration
│   ├── package.json               # Node dependencies
│   ├── vite.config.js             # Vite configuration
│   ├── Dockerfile                 # Frontend Docker build
│   └── nginx.conf                 # Nginx configuration
├── CLAUDE.md                       # Claude Code guidance
└── README.md                       # This file
```

## Configuration

### Environment Variables

All configuration is managed through `.env` file at the project root.

**Key Variables:**

```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your_frontend_client_id
VITE_AUTH0_AUDIENCE=https://your-api-audience
AUTH0_CLIENT_SECRET=your_backend_client_secret

# MongoDB Configuration
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=secure_password
MONGO_DATABASE_NAME=study_planning

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama2:latest
DEFAULT_LANGUAGE=spanish  # auto/english/spanish
MAX_CONTEXT_LENGTH=1500

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Supported LLM Models

| Model | Size | Speed | Quality | Recommended For |
|-------|------|-------|---------|-----------------|
| `llama2:latest` | 3.8GB | Medium | Good | Default, balanced |
| `mistral` | 4.1GB | Medium | Better | Higher quality |
| `phi` | 1.6GB | Fast | Good | Limited resources |
| `tinyllama` | 600MB | Very Fast | Basic | Testing only |

**Change model:**
```bash
# Edit docker-compose.yml
OLLAMA_MODEL=mistral

# Or pull and use on-demand
docker exec study-planning-ollama ollama pull mistral
```

### Supported File Types

| Type | Extensions | Supported |
|------|------------|-----------|
| **PDF** | `.pdf` | ✅ |
| **Word** | `.doc`, `.docx` | ✅ |
| **Excel** | `.xls`, `.xlsx` | ✅ |
| **Text** | `.txt` | ✅ |
| **Markdown** | `.md` | ✅ |

## Production Deployment

### Using Production Compose File

```bash
# Start production environment
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

### Production Differences

- ✅ **No source bind mount** - uses baked-in code
- ✅ **4 Uvicorn workers** - for concurrent requests
- ✅ **Resource limits** - CPU and memory constraints
- ✅ **Ollama port internal** - not exposed to host
- ✅ **Stronger passwords** - update `.env` file
- ✅ **HTTPS recommended** - use reverse proxy (Nginx/Traefik)

### Security Checklist

- [ ] Change MongoDB credentials in `.env`
- [ ] Use strong Auth0 client secrets
- [ ] Enable HTTPS with SSL certificates
- [ ] Configure proper CORS origins
- [ ] Set up firewall rules
- [ ] Enable MongoDB authentication
- [ ] Regular backups of MongoDB and volumes
- [ ] Monitor logs for suspicious activity

## Troubleshooting

### 503 Error: "LLM service not available"

**Problem**: Ollama can't load model due to insufficient memory.

**Solution**:
1. Open Docker Desktop → Settings → Resources
2. Increase Memory slider to **10GB minimum**
3. Click "Apply & Restart"
4. Restart containers: `docker compose down && docker compose up -d`

### Auth0 Login Fails

**Problem**: "Invalid redirect URI" or "Application not found"

**Solution**:
1. Check Auth0 application settings:
   - Allowed Callback URLs: `http://localhost:3000`
   - Allowed Logout URLs: `http://localhost:3000`
   - Allowed Web Origins: `http://localhost:3000`
2. Verify `.env` has correct Auth0 credentials
3. Rebuild frontend: `docker compose up --build frontend`

### MongoDB Connection Errors

**Problem**: "Authentication failed" or "Cannot connect to MongoDB"

**Solution**:
```bash
# Check MongoDB is running
docker compose ps mongodb

# View MongoDB logs
docker compose logs -f mongodb

# Verify credentials in .env
cat .env | grep MONGO

# Restart MongoDB
docker compose restart mongodb
```

### GPU Not Detected

**Problem**: Ollama not using GPU, slow inference.

**Solution**:
```bash
# Check NVIDIA drivers
nvidia-smi

# Install NVIDIA Container Toolkit (see GPU Support section)

# Verify Docker can access GPU
docker run --rm --gpus all ubuntu nvidia-smi

# Restart Docker daemon
sudo systemctl restart docker

# Restart containers
docker compose down && docker compose up -d
```

### Windows Line Ending Issues

**Problem**: `docker-entrypoint.sh: no such file or directory`

**Solution**:
The Dockerfile automatically fixes line endings using `dos2unix`. Simply run:
```bash
docker compose up --build
```

For manual fix:
```bash
git config core.autocrlf false
git rm --cached -r .
git reset --hard
```

### Common Commands

```bash
# Check all container status
docker compose ps

# View all logs
docker compose logs -f

# Check API health
curl http://localhost:8000/health

# Check if Ollama is working
curl http://localhost:11434/api/tags

# Reset everything (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

## Development Workflow

### Making Code Changes

1. **Backend** (`CODE/` directory):
   - Edit Python files
   - Changes auto-reload (hot-reload enabled)
   - View logs: `docker compose logs -f fastapi-app`

2. **Frontend** (`FRONTEND/` directory):
   - Edit React/JSX files
   - Rebuild: `docker compose up --build frontend`
   - Or use native dev: `cd FRONTEND && npm run dev`

### Adding Dependencies

**Backend**:
```bash
# Add to CODE/requirements.txt
echo "pandas==2.0.0" >> CODE/requirements.txt

# Rebuild
docker compose up --build fastapi-app
```

**Frontend**:
```bash
# Add to FRONTEND/package.json
cd FRONTEND
npm install axios

# Update package.json in git
git add FRONTEND/package.json FRONTEND/package-lock.json

# Rebuild
docker compose up --build frontend
```

### Database Migrations

This project uses MongoDB (schemaless), so formal migrations aren't required. However:

```bash
# Access MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p password

# Switch to database
use study_planning

# View collections
show collections

# Query users
db.users.find().pretty()

# Add index
db.users.createIndex({ "auth0_sub": 1 }, { unique: true })
```

## Testing

```bash
# Backend unit tests
docker exec study-planning-api python tests/test_direct.py

# API endpoint tests (server must be running)
docker exec study-planning-api python tests/test_rag.py
```

## Requirements

### Docker Setup
- **Docker Desktop** with 10GB+ memory allocated
- **10GB+ disk space** for images and models
- **Auth0 account** (free tier)

### Native Setup (Without Docker)
- Python 3.11+
- Node.js 18+
- MongoDB 7.0+
- Ollama installed locally
- 8GB+ RAM

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Ensure no secrets in commits
5. Commit: `git commit -m "Add feature"`
6. Push: `git push origin feature-name`
7. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Auth0](https://auth0.com/) - Authentication platform
- [MongoDB](https://www.mongodb.com/) - NoSQL database
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - LLM application framework
- [React](https://react.dev/) - Frontend framework
- [Vite](https://vitejs.dev/) - Frontend build tool

## Support

- **Documentation**: See [CLAUDE.md](CLAUDE.md) for detailed technical guidance
- **API Docs**: http://localhost:8000/docs (when running)
- **Issues**: Report bugs and request features via GitHub Issues

---

**Built for students, powered by AI** 🎓🤖
