# Getting Started with Study Planning Assistant

Welcome! This guide will help you get up and running with the Study Planning Assistant in just a few minutes.

## What is This?

The Study Planning Assistant is a complete web application that helps you study by allowing you to:
1. **Upload** your study materials (PDFs, Word docs, etc.)
2. **Ask questions** about your materials in natural language
3. **Get intelligent answers** powered by AI (using RAG - Retrieval-Augmented Generation)

Think of it like having a personal tutor who has read all your study materials and can answer questions about them.

## The Fastest Way to Start

### Option 1: Docker (Recommended - One Command)

**Prerequisites**: Docker Desktop installed and running

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning

# 2. Start everything
docker compose up

# That's it! Wait for containers to build and start...
```

**What happens:**
- First time: Takes 10-20 minutes (downloads models, builds containers)
- Subsequent times: Starts in ~30 seconds

**Access the application:**
- 🎨 **Web Interface**: http://localhost:3000
- 🔧 **API Docs**: http://localhost:8000/docs

**Note**: Make sure Docker Desktop has at least 10GB of memory allocated (Settings → Resources).

### Option 2: Native Development

If you prefer running without Docker:

```bash
# 1. Start Backend (Terminal 1)
cd CODE
pip install -r requirements.txt
./scripts/start_server.sh

# 2. Start Frontend (Terminal 2)
cd FRONTEND
npm install
npm run dev
```

Access:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Your First Steps

### Step 1: Upload a Document

1. Navigate to http://localhost:3000
2. Click "Upload" in the navigation
3. Drag and drop a study document (PDF, Word, etc.)
4. Wait for the upload to complete

### Step 2: Ask Questions

1. Click "Query" in the navigation
2. Type a question about your uploaded document
3. Hit Send
4. Get an AI-generated answer with source citations!

### Step 3: Manage Files

1. Click "Files" in the navigation
2. View all your uploaded documents
3. Delete files you no longer need

## Example Workflow

Let's say you uploaded a PDF about "Machine Learning Basics":

```
You: What is supervised learning?

AI: Based on your documents, supervised learning is a type of
machine learning where the model learns from labeled training
data. The algorithm learns to map inputs to outputs based on
example input-output pairs.

Sources: machine-learning-basics.pdf
```

## Understanding the Interface

### Home Page
- See how many documents you've uploaded
- Check system status
- Quick links to main features

### Upload Page
- Drag-and-drop interface
- Progress tracking
- Supported formats: PDF, Word, Excel, Markdown, Text

### Query Page
- Chat interface (like ChatGPT)
- Adjustable settings:
  - **Number of chunks**: More = more context but slower
  - **Language**: Auto-detect, English, or Spanish
- See which documents were used to answer

### Files Page
- List all uploaded files
- See file size, type, and upload date
- Delete unwanted files

## Configuration

### Backend Settings

Edit `CODE/.env` to customize:

```bash
OLLAMA_MODEL=llama2:latest      # Which AI model to use
DEFAULT_LANGUAGE=auto           # Response language
MAX_CONTEXT_LENGTH=1500         # How much context to send to AI
```

### Frontend Settings

Edit `FRONTEND/.env.development`:

```bash
VITE_API_URL=http://localhost:8000  # Backend API location
```

## Common Tasks

### Change AI Model

```bash
# List available models
docker exec study-planning-ollama ollama list

# Pull a new model (e.g., mistral)
docker exec study-planning-ollama ollama pull mistral

# Update docker-compose.yml
# Change OLLAMA_MODEL=llama2:latest to OLLAMA_MODEL=mistral:latest

# Restart
docker compose restart
```

### Reset All Data

```bash
# Stop and remove all data
docker compose down -v

# Start fresh
docker compose up
```

### View Logs

```bash
# All services
docker compose logs -f

# Just frontend
docker compose logs -f frontend

# Just backend
docker compose logs -f fastapi-app
```

## Troubleshooting

### "Cannot connect to backend"
- Make sure backend is running: http://localhost:8000/docs
- Check Docker containers: `docker compose ps`
- View logs: `docker compose logs -f`

### "503 Service Unavailable" when querying
- Increase Docker Desktop memory to 10GB+
- Settings → Resources → Memory

### Frontend won't start
```bash
cd FRONTEND
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend won't start
```bash
docker compose down
docker compose up --build
```

### Ollama model download stuck
- Be patient, models are 2-4GB
- Check logs: `docker compose logs -f ollama`
- Try manual pull: `docker exec study-planning-ollama ollama pull llama2`

## System Requirements

### For Docker:
- **RAM**: 10GB+ allocated to Docker
- **Disk**: 15GB+ free space
- **OS**: Windows 10+, macOS 10.15+, or Linux
- **Docker**: Desktop 4.0+

### For Native:
- **Python**: 3.11+
- **Node.js**: 18+
- **RAM**: 8GB+ (16GB recommended)
- **Ollama**: Installed and running

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                     YOU                              │
│                   (Browser)                          │
└────────────────────┬─────────────────────────────────┘
                     │ HTTP (Port 3000)
                     ↓
┌──────────────────────────────────────────────────────┐
│              FRONTEND (React + Nginx)                │
│  - Upload Interface                                  │
│  - Query Chat                                        │
│  - File Management                                   │
└────────────────────┬─────────────────────────────────┘
                     │ /api/* → Port 8000
                     ↓
┌──────────────────────────────────────────────────────┐
│              BACKEND (FastAPI)                       │
│  - File Processing                                   │
│  - RAG Pipeline                                      │
│  - API Endpoints                                     │
└───────┬──────────────────────────┬───────────────────┘
        │                          │
        │ Embeddings              │ LLM Queries
        ↓                          ↓
┌──────────────┐          ┌──────────────────┐
│   ChromaDB   │          │     Ollama       │
│  (Vector DB) │          │   (AI Models)    │
└──────────────┘          └──────────────────┘
```

## What's Next?

### Learn More
- **Frontend Details**: [FRONTEND/README.md](FRONTEND/README.md)
- **Backend Details**: [CLAUDE.md](CLAUDE.md)
- **Quick Frontend Guide**: [FRONTEND_QUICKSTART.md](FRONTEND_QUICKSTART.md)
- **API Documentation**: http://localhost:8000/docs (when running)

### Try Advanced Features
- Use different AI models (mistral, tinyllama)
- Query in Spanish
- Upload multiple documents and ask questions across them
- Adjust chunk count for different context sizes

### Contribute
- Report issues on GitHub
- Submit pull requests
- Improve documentation

## Need Help?

1. Check logs: `docker compose logs -f`
2. Read troubleshooting section above
3. Check the documentation files
4. Review http://localhost:8000/docs for API details

## Success Checklist

- [ ] Docker containers running (`docker compose ps`)
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend accessible at http://localhost:8000
- [ ] Can upload a file
- [ ] Can ask a question and get a response
- [ ] Can view uploaded files
- [ ] Can delete files

If all checkboxes are checked, you're ready to go! Happy studying!
