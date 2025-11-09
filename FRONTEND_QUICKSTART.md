# Frontend Quick Start Guide

This guide will help you get the React frontend up and running quickly.

## Quick Start with Docker (Recommended)

The easiest way to run the complete application (frontend + backend + LLM):

```bash
# From project root directory
docker compose up --build

# Access the application:
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

That's it! The frontend will automatically connect to the backend API.

## Development Mode (Without Docker)

If you want to develop the frontend with hot-reload:

### Step 1: Start the Backend

First, ensure the backend API is running:

```bash
# Option A: With Docker (just backend services)
docker compose up ollama fastapi-app

# Option B: Native (from CODE directory)
cd CODE
./scripts/start_server.sh
```

### Step 2: Start the Frontend Dev Server

```bash
# In a new terminal, from FRONTEND directory
cd FRONTEND
npm install
npm run dev
```

Access the frontend at http://localhost:3000

Changes to React code will automatically hot-reload.

## What You Can Do

### 1. Upload Documents
- Navigate to "Upload" page
- Drag-and-drop or click to select files
- Supports: PDF, Word, Excel, Text, Markdown
- Files are automatically processed for RAG

### 2. Query Your Documents
- Navigate to "Query" page
- Ask questions about your uploaded materials
- Adjust number of chunks for more context
- Choose response language (auto-detect, English, Spanish)
- View sources for each answer

### 3. Manage Files
- Navigate to "Files" page
- View all uploaded documents
- See file metadata (size, type, upload date)
- Delete files when no longer needed

### 4. Monitor System
- Home page shows system statistics
- View number of documents and chunks
- Check LLM service status
- See system configuration

## Architecture

```
┌─────────────┐
│   Browser   │
│  (Port 3000)│
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Nginx     │────→│  FastAPI     │────→│   Ollama    │
│  (Frontend) │     │  (Backend)   │     │    (LLM)    │
└─────────────┘     └──────────────┘     └─────────────┘
                           │
                           ↓
                    ┌──────────────┐
                    │  ChromaDB    │
                    │ (Vector DB)  │
                    └──────────────┘
```

## Troubleshooting

### Frontend won't start
```bash
# Clean install
cd FRONTEND
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Can't connect to backend
- Verify backend is running at http://localhost:8000
- Check `.env.development` has `VITE_API_URL=http://localhost:8000`
- Try accessing http://localhost:8000/docs directly

### Build fails
```bash
# Check Node version (need 18+)
node --version

# Reinstall dependencies
npm clean-install
```

### Docker issues
```bash
# Rebuild containers
docker compose down
docker compose up --build

# Check logs
docker compose logs -f frontend
docker compose logs -f fastapi-app
```

## Environment Variables

### Development (.env.development)
```bash
VITE_API_URL=http://localhost:8000
```

### Production (.env.production)
```bash
VITE_API_URL=/api
```

In production, nginx proxies `/api/*` to the backend service.

## File Structure

```
FRONTEND/
├── src/
│   ├── pages/              # Main page components
│   │   ├── HomePage.jsx    # Dashboard with stats
│   │   ├── UploadPage.jsx  # File upload interface
│   │   ├── QueryPage.jsx   # RAG query chat
│   │   └── FilesPage.jsx   # File management
│   ├── services/
│   │   └── api.js          # Backend API client
│   ├── App.jsx             # Root component with routing
│   ├── App.css             # Global styles
│   └── main.jsx            # Entry point
├── public/                 # Static assets
├── .env.development        # Dev environment config
├── .env.production         # Prod environment config
├── vite.config.js          # Vite configuration
├── nginx.conf              # Nginx config (Docker)
└── Dockerfile              # Multi-stage build
```

## Available Scripts

```bash
npm run dev       # Start dev server (http://localhost:3000)
npm run build     # Build for production
npm run preview   # Preview production build
npm run lint      # Run ESLint
```

## Next Steps

1. Upload some study materials (PDF, Word, etc.)
2. Go to Query page and ask questions
3. Experiment with different chunk sizes
4. Try both English and Spanish queries

## Need Help?

- Frontend README: [FRONTEND/README.md](FRONTEND/README.md)
- Backend README: [README.md](README.md)
- CLAUDE.md: [CLAUDE.md](CLAUDE.md) (detailed architecture guide)
