# Environment Variables Structure

This document explains how environment variables are organized in this project.

## Structure Overview

```
Conversational-interface-for-study-planning/
├── CODE/.env                 # Backend configuration (FastAPI + Auth0)
├── FRONTEND/.env            # Frontend configuration (Vite + Auth0)
└── docker-compose.yml       # Only overrides container-specific settings
```

## Why This Structure?

### ✅ Clean Separation
- Each application manages its own configuration
- No confusion about which `.env` file to edit
- Easy to understand what each file controls

### ✅ Native Development
- `CODE/.env` is read by FastAPI when running natively (`python -m uvicorn`)
- `FRONTEND/.env` is read by Vite when running natively (`npm run dev`)

### ✅ Docker Development
- Docker mounts `CODE/` directory, so container reads `CODE/.env` automatically
- Frontend is built with `FRONTEND/.env` variables baked in
- `docker-compose.yml` only overrides container-specific settings (MongoDB URL, Ollama URL)

---

## Configuration Files

### 1. Backend Configuration (`CODE/.env`)

**Used by**: FastAPI backend (both native and Docker)

**Contains**:
- Auth0 credentials (domain, audience, client ID/secret)
- Ollama configuration (URL, model, timeout)
- MongoDB configuration (URI, database name)
- File upload settings (directory, max size, allowed extensions)
- RAG settings (ChromaDB path, embedding model, chunk size)
- LLM response settings (language, instructions, context length)
- CORS settings (allowed origins)
- Logging configuration

**Example**:
```env
# Auth0 Configuration
AUTH0_DOMAIN=dev-abc123.us.auth0.com
AUTH0_API_AUDIENCE=https://study-planning-api
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2:latest
OLLAMA_TIMEOUT=180

# MongoDB Configuration
MONGO_URI=mongodb://admin:password@localhost:27017/?authSource=admin
MONGO_DATABASE_NAME=study_planning

# File Storage
UPLOAD_DIR=data/uploads
MAX_FILE_SIZE=52428800  # 50MB

# RAG Configuration
CHROMADB_PATH=data/chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CHUNKS_FOR_CONTEXT=5

# LLM Response
DEFAULT_LANGUAGE=auto
RESPONSE_INSTRUCTIONS=
MAX_CONTEXT_LENGTH=1500

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 2. Frontend Configuration (`FRONTEND/.env`)

**Used by**: Vite development server and build process

**Contains**:
- API URL (where backend is running)
- Auth0 configuration (domain, client ID, audience, redirect URI)

**Important**: All Vite environment variables **must** be prefixed with `VITE_`

**Example**:
```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Auth0 Configuration
VITE_AUTH0_DOMAIN=dev-abc123.us.auth0.com
VITE_AUTH0_CLIENT_ID=your_client_id
VITE_AUTH0_AUDIENCE=https://study-planning-api
VITE_AUTH0_REDIRECT_URI=http://localhost:3000
```

### 3. Docker Compose (`docker-compose.yml`)

**Purpose**: Override settings for containerized environment

**Only overrides**:
- MongoDB URI (uses service name `mongodb` instead of `localhost`)
- Ollama URL (uses service name `ollama` instead of `localhost`)
- CORS origins (includes container network addresses)

**Does NOT contain**:
- Auth0 credentials (read from `CODE/.env`)
- Most app settings (read from `CODE/.env`)

---

## How It Works

### Native Development (No Docker)

1. **Backend**:
   ```bash
   cd CODE
   python -m uvicorn app.main:app --reload
   ```
   - Reads `CODE/.env`
   - Connects to Ollama at `http://localhost:11434`
   - Connects to MongoDB at `localhost:27017`

2. **Frontend**:
   ```bash
   cd FRONTEND
   npm run dev
   ```
   - Reads `FRONTEND/.env`
   - Makes API calls to `http://localhost:8000`
   - Redirects to Auth0 login

### Docker Development

1. **Start containers**:
   ```bash
   docker compose up
   ```

2. **Backend container**:
   - Mounts `CODE/` directory (hot-reload enabled)
   - Reads `CODE/.env` from mounted directory
   - `docker-compose.yml` overrides:
     - `MONGO_URI=mongodb://admin:password@mongodb:27017/...` (uses Docker network)
     - `OLLAMA_BASE_URL=http://ollama:11434` (uses Docker network)

3. **Frontend container**:
   - Built with `FRONTEND/.env` variables
   - Variables are baked into the static build at build time
   - Served by Nginx on port 3000

---

## Environment Variables Reference

### Backend Variables (CODE/.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH0_DOMAIN` | ✅ | - | Your Auth0 tenant domain |
| `AUTH0_API_AUDIENCE` | ✅ | - | API identifier in Auth0 |
| `AUTH0_CLIENT_ID` | ⚠️ | - | Client ID (for M2M token generation) |
| `AUTH0_CLIENT_SECRET` | ⚠️ | - | Client secret (for M2M token generation) |
| `AUTH0_ALGORITHMS` | ❌ | `["RS256"]` | JWT signing algorithms |
| `MONGO_URI` | ❌ | `mongodb://admin:password@mongodb:27017/...` | MongoDB connection string |
| `MONGO_DATABASE_NAME` | ❌ | `study_planning` | MongoDB database name |
| `OLLAMA_BASE_URL` | ❌ | `http://localhost:11434` | Ollama service URL |
| `OLLAMA_MODEL` | ❌ | `llama2` | Default LLM model |
| `OLLAMA_TIMEOUT` | ❌ | `180` | LLM query timeout (seconds) |
| `UPLOAD_DIR` | ❌ | `data/uploads` | File upload directory |
| `CHROMADB_PATH` | ❌ | `data/chroma_db` | ChromaDB storage path |
| `DEFAULT_LANGUAGE` | ❌ | `auto` | Response language (auto/spanish/english) |
| `MAX_CONTEXT_LENGTH` | ❌ | `1500` | Max context chars for LLM |
| `CORS_ORIGINS` | ❌ | `http://localhost:3000,http://localhost:8000` | Allowed CORS origins |

### Frontend Variables (FRONTEND/.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_URL` | ❌ | `http://localhost:8000` | Backend API URL |
| `VITE_AUTH0_DOMAIN` | ✅ | - | Auth0 tenant domain |
| `VITE_AUTH0_CLIENT_ID` | ✅ | - | Auth0 application client ID |
| `VITE_AUTH0_AUDIENCE` | ✅ | - | Auth0 API audience |
| `VITE_AUTH0_REDIRECT_URI` | ❌ | `window.location.origin` | Auth0 callback URL |

**Legend**:
- ✅ Required
- ⚠️ Required for certain features
- ❌ Optional (has default)

---

## Setup Instructions

### For New Developers

1. **Clone the repository**

2. **Create backend `.env`**:
   ```bash
   cp CODE/.env.example CODE/.env
   # Edit CODE/.env with your values
   ```

3. **Create frontend `.env`**:
   ```bash
   cp FRONTEND/.env.example FRONTEND/.env
   # Edit FRONTEND/.env with your values
   ```

4. **Start services**:
   ```bash
   # Option A: Docker (recommended)
   docker compose up

   # Option B: Native
   # Terminal 1: Backend
   cd CODE && python -m uvicorn app.main:app --reload

   # Terminal 2: Frontend
   cd FRONTEND && npm run dev
   ```

### For Production Deployment

1. **Update `CODE/.env` for production**:
   - Set production Auth0 credentials
   - Set production MongoDB URI
   - Set production Ollama URL (if external)
   - Update CORS origins to include production domain

2. **Update `FRONTEND/.env` for production**:
   - Set production API URL
   - Set production Auth0 redirect URI
   - Update other URLs as needed

3. **Use production Docker Compose**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

---

## Security Notes

⚠️ **IMPORTANT**: Never commit `.env` files to version control!

1. **All `.env` files are gitignored**
2. **Use `.env.example` files** as templates (without real credentials)
3. **Store production secrets** in secure secret management (AWS Secrets Manager, Azure Key Vault, etc.)
4. **Rotate credentials regularly**
5. **Use different Auth0 applications** for dev/staging/production

---

## Troubleshooting

### "Environment variable not found"

**Problem**: Application can't read environment variable.

**Solutions**:
- **Backend**: Check `CODE/.env` exists and variable is set
- **Frontend**: Check `FRONTEND/.env` exists, variable is prefixed with `VITE_`, and dev server was restarted
- **Docker**: Check if variable needs to be overridden in `docker-compose.yml`

### "Frontend shows undefined for Auth0 domain"

**Problem**: Vite didn't load `.env` file.

**Solution**:
1. Verify `FRONTEND/.env` exists
2. Verify variables are prefixed with `VITE_`
3. **Restart Vite dev server** (Ctrl+C, then `npm run dev`)
4. Hard refresh browser (Ctrl+Shift+R)

### "Backend can't connect to MongoDB/Ollama in Docker"

**Problem**: Using localhost URLs in Docker container.

**Solution**:
- Docker overrides these in `docker-compose.yml`
- Verify `docker-compose.yml` sets:
  - `MONGO_URI=mongodb://admin:password@mongodb:27017/...`
  - `OLLAMA_BASE_URL=http://ollama:11434`

### "CORS errors when calling API"

**Problem**: Frontend origin not in CORS whitelist.

**Solution**:
- Update `CORS_ORIGINS` in `CODE/.env`
- Restart backend
- Example: `CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://your-domain.com`

---

## Migration Notes

### Previous Structure (Deprecated)

Before this cleanup, there were three `.env` files:
- ❌ Root `.env` (deleted - was redundant)
- ✅ `CODE/.env` (kept)
- ✅ `FRONTEND/.env` (kept)

### What Changed

- **Deleted**: Root `.env` file
- **Updated**: `docker-compose.yml` to only override Docker-specific settings
- **Result**: Cleaner, more maintainable structure

### No Breaking Changes

If you have the old structure:
1. Delete root `.env`
2. Ensure `CODE/.env` has all backend settings
3. Ensure `FRONTEND/.env` has all frontend settings
4. Pull latest `docker-compose.yml`
5. Everything will work exactly the same
