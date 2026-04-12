# Study Planning Conversational Interface

> **Final Degree Project — ORT University**
>
> An AI-powered study advisor that lets students ask questions in plain language and receive intelligent, personalized answers about their academic progress, available courses, degree curriculum, and uploaded documents.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![React](https://img.shields.io/badge/React-19+-61dafb.svg)](https://reactjs.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-ReAct_Agent-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-FF6B6B.svg)](https://ollama.ai)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.0-47A248.svg)](https://www.mongodb.com)
[![Auth0](https://img.shields.io/badge/Auth0-Secured-EB5424.svg)](https://auth0.com)

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [How It Works](#2-how-it-works)
3. [Features](#3-features)
4. [System Architecture](#4-system-architecture)
5. [Deployment Guide](#5-deployment-guide)
   - [5.1 Prerequisites](#51-prerequisites)
   - [5.2 Setting Up Auth0](#52-setting-up-auth0)
   - [5.3 Configuring the Environment](#53-configuring-the-environment)
   - [5.4 Starting the Application](#54-starting-the-application)
   - [5.5 First-Time Setup](#55-first-time-setup)
   - [5.6 Production Deployment](#56-production-deployment)
6. [User Guide](#6-user-guide)
   - [6.1 Logging In](#61-logging-in)
   - [6.2 Uploading Documents](#62-uploading-documents)
   - [6.3 Asking Questions](#63-asking-questions)
   - [6.4 Managing Files](#64-managing-files)
   - [6.5 Admin Features](#65-admin-features)
7. [Configuration Reference](#7-configuration-reference)
8. [API Reference](#8-api-reference)
9. [Development Guide](#9-development-guide)
10. [Troubleshooting](#10-troubleshooting)
11. [Project Structure](#11-project-structure)
12. [Technology Stack](#12-technology-stack)
13. [License](#13-license)

---

## 1. What Is This?

This application is an **AI-powered academic advisor** built as a final degree project for ORT University. It combines a conversational chat interface with an intelligent AI agent that has access to:

- **Your uploaded documents** — transcripts, syllabi, course guides, or any study material
- **Your academic record** — completed courses, grades, and GPA
- **Your degree curriculum** — the full list of courses required for your degree
- **Available courses** — which courses you can enroll in right now, based on prerequisites you've already met
- **Your personalized study plan** — recommended courses for upcoming semesters
- **The web** — for any information not found locally

Instead of navigating multiple systems and spreadsheets, students can simply ask questions like:

> *"What courses can I take next semester?"*
> *"What are my grades from last year?"*
> *"How many credits do I have left to graduate?"*
> *"Summarize the syllabus for my algorithms course."*

The system answers in the **same language as the question** (Spanish or English), making it accessible to the full student body.

---

## 2. How It Works

The application uses a technique called **ReAct** (Reasoning + Acting), where an AI agent reads your question, reasons about what information it needs, calls the appropriate tools to gather that information, and then formulates a natural language answer.

```
You ask a question
        │
        ▼
   AI Agent reads your question and decides what to do
        │
        ├──► Search your uploaded documents
        ├──► Look up your academic record
        ├──► Check what courses are available to you
        ├──► Read the full degree curriculum
        ├──► Retrieve your study plan
        └──► Search the web
        │
        ▼
   Agent combines the results
        │
        ▼
   AI writes a clear, personalized answer
        │
        ▼
   Answer is shown in the chat and saved to your history
```

All AI processing runs **locally on your server** using [Ollama](https://ollama.ai) — no data is sent to external AI providers. The system is private by design.

---

## 3. Features

### For Students

- **Conversational AI** — Ask questions in plain language, get clear answers
- **Document Q&A** — Upload any study material and ask questions about it
- **Academic Advisor** — Know exactly which courses you can take next, with prerequisite checking
- **Degree Progress** — Understand how far along you are in your degree
- **Study Plans** — Get personalized course recommendations
- **Conversation History** — All your chats are saved and searchable
- **Bilingual** — Answers in Spanish or English, automatically matching your question
- **Feedback System** — Rate responses and leave comments to help improve the system

### For Administrators

- **Document Library** — Upload public documents visible to all students
- **User Management** — View all users and promote them to admin
- **System Statistics** — See usage, query counts, and activity
- **Feedback Dashboard** — Review all student feedback with filtering and AI-powered summaries
- **Per-file Analytics** — See how often each document is used

### Technical Highlights

- **Runs entirely locally** — LLM runs on your hardware via Ollama, no external AI calls
- **Secure authentication** — Auth0 JWT-based login with role-based access control
- **Multi-format document support** — PDF, Word (.docx), Excel (.xlsx), plain text, Markdown
- **Semantic search** — Finds relevant content even when the exact words don't match
- **Persistent storage** — All data, files, and conversation history survive restarts
- **GPU acceleration** — Optional NVIDIA GPU support for faster AI responses

---

## 4. System Architecture

The application is composed of **six Docker services** that work together:

```
┌───────────────────────────────────────────────────────────────────┐
│                        Docker Network                              │
│                                                                    │
│  ┌─────────────┐     ┌──────────────────┐     ┌───────────────┐  │
│  │  Frontend   │────▶│   Backend API    │────▶│   MongoDB     │  │
│  │ React + Vite│     │ FastAPI + Python  │     │  (Database)   │  │
│  │  Port 3000  │     │    Port 8000     │     │  Port 27017   │  │
│  └─────────────┘     └────────┬─────────┘     └───────────────┘  │
│                               │                                    │
│              ┌────────────────┼────────────────┐                  │
│              ▼                ▼                ▼                  │
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐      │
│  │   Agent API     │  │  ChromaDB   │  │     Ollama      │      │
│  │ (Tool Execution)│  │  (Vectors)  │  │   (Local LLM)   │      │
│  │   Port 8002     │  │  Port 8001  │  │   Port 11434    │      │
│  └─────────────────┘  └─────────────┘  └─────────────────┘      │
└───────────────────────────────────────────────────────────────────┘
```

| Service | Purpose |
|---|---|
| **Frontend** | The web interface students and admins use |
| **Backend API** | Handles requests, runs the AI agent, validates authentication |
| **Agent API** | Microservice that executes agent tools (search, academic data, etc.) |
| **MongoDB** | Stores users, conversations, feedback, and uploaded files |
| **ChromaDB** | Vector database for semantic document search |
| **Ollama** | Runs the large language model locally on your hardware |

---

## 5. Deployment Guide

This section covers everything you need to go from zero to a running application.

### 5.1 Prerequisites

Before you start, make sure you have the following installed and ready:

#### Required Software

| Tool | Minimum Version | Download |
|---|---|---|
| **Docker Desktop** | Latest | [docker.com/get-started](https://www.docker.com/get-started/) |
| **Git** | Any recent version | [git-scm.com](https://git-scm.com/) |

> **Docker Desktop memory:** After installing Docker Desktop, go to **Settings → Resources** and set Memory to at least **10 GB**. The AI model needs significant memory to run. Without this, the application will fail to start.

#### Required Accounts

- **Auth0 account** (free tier is sufficient) — [auth0.com](https://auth0.com)

#### Hardware Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| RAM | 10 GB available to Docker | 16 GB |
| Disk space | 15 GB free | 20 GB |
| CPU | Any modern 64-bit | 8+ cores |
| GPU | Not required | NVIDIA GPU (for speed) |

> **First-time startup note:** The first time you start the application, it will automatically download the AI language model (~4–5 GB). This can take 10–20 minutes depending on your internet speed. Subsequent startups are fast (under a minute).

---

### 5.2 Setting Up Auth0

Auth0 handles user login and authentication. You need to create a few resources in your Auth0 account before the application can run.

#### Step 1 — Create an Auth0 Account

Go to [auth0.com](https://auth0.com) and sign up for a free account. After signing in, you will be in the **Auth0 Dashboard**.

#### Step 2 — Note Your Domain

In the top-left of the Auth0 Dashboard, you will see your **tenant domain**. It looks like:

```
your-name.us.auth0.com
```

Write this down — you will need it in the next section.

#### Step 3 — Create the Frontend Application

This is the Auth0 application that your web browser will use to log in.

1. In the left sidebar, go to **Applications → Applications**
2. Click **+ Create Application**
3. Name it `Study Planning Frontend` (or anything you like)
4. Select **Single Page Web Applications**
5. Click **Create**

You are now on the settings page for this application. Configure the following fields:

| Field | Value |
|---|---|
| **Allowed Callback URLs** | `http://localhost:3000` |
| **Allowed Logout URLs** | `http://localhost:3000` |
| **Allowed Web Origins** | `http://localhost:3000` |

Scroll down and click **Save Changes**.

On the same page, find and copy:
- **Domain** (e.g., `your-name.us.auth0.com`)
- **Client ID** (a long string of letters and numbers)

#### Step 4 — Create the API

This represents your backend server in Auth0.

1. In the left sidebar, go to **Applications → APIs**
2. Click **+ Create API**
3. Fill in:
   - **Name**: `Study Planning API`
   - **Identifier**: `https://study-planning-api` (this is just a unique name — it doesn't need to be a real URL)
   - **Signing Algorithm**: RS256 (leave default)
4. Click **Create**

Write down the **Identifier** you chose — this is your `AUTH0_API_AUDIENCE`.

#### Step 5 — Create the Backend Machine-to-Machine Application

This allows your backend server to authenticate with Auth0 programmatically.

1. In the left sidebar, go to **Applications → Applications**
2. Click **+ Create Application**
3. Name it `Study Planning Backend`
4. Select **Machine to Machine Applications**
5. Click **Create**
6. On the next screen, select the **Study Planning API** you just created
7. Under **Permissions**, select **All** (or leave it as the default)
8. Click **Authorize**

You are now on the settings page for this application. Copy:
- **Client ID**
- **Client Secret** (click the eye icon to reveal it)

> **Security note:** The Backend Client Secret must be kept private. Never share it or commit it to version control.

#### Summary: What You Should Have Collected

| Variable | Where to find it |
|---|---|
| `VITE_AUTH0_DOMAIN` | Auth0 Dashboard → top-left tenant domain |
| `VITE_AUTH0_CLIENT_ID` | Frontend Application → Client ID |
| `VITE_AUTH0_AUDIENCE` | The API identifier you chose |
| `AUTH0_DOMAIN` | Same as `VITE_AUTH0_DOMAIN` |
| `AUTH0_API_AUDIENCE` | Same as `VITE_AUTH0_AUDIENCE` |
| `AUTH0_CLIENT_ID` | Backend Application → Client ID |
| `AUTH0_CLIENT_SECRET` | Backend Application → Client Secret |

---

### 5.3 Configuring the Environment

The application reads all its settings from a file called `.env` in the root of the project. This file is never committed to version control — it lives only on your machine.

#### Step 1 — Clone the Repository

```bash
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning
```

#### Step 2 — Create the `.env` File

```bash
cp .env.example .env
```

#### Step 3 — Edit the `.env` File

Open `.env` in any text editor and fill in your values:

```bash
# ============================================
# DATABASE
# ============================================
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=change_this_to_a_secure_password
MONGO_DATABASE_NAME=study_planning

# ============================================
# AUTH0 — FRONTEND (these are embedded in the browser bundle, not secret)
# ============================================
VITE_AUTH0_DOMAIN=your-name.us.auth0.com
VITE_AUTH0_CLIENT_ID=your_frontend_client_id
VITE_AUTH0_AUDIENCE=https://study-planning-api
VITE_AUTH0_REDIRECT_URI=http://localhost:3000

# ============================================
# AUTH0 — BACKEND (keep these secret!)
# ============================================
AUTH0_DOMAIN=your-name.us.auth0.com
AUTH0_API_AUDIENCE=https://study-planning-api
AUTH0_CLIENT_ID=your_backend_client_id
AUTH0_CLIENT_SECRET=your_backend_client_secret

# ============================================
# API SETTINGS
# ============================================
VITE_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# ============================================
# AI MODEL (Ollama)
# ============================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.1:8b

# ============================================
# AGENT & RESPONSE SETTINGS
# ============================================
AGENT_PROVIDER=react
DEFAULT_LANGUAGE=auto
MAX_CONTEXT_LENGTH=1500
UPLOAD_DIR=data/uploads
```

**Important notes:**
- Replace every `your_...` placeholder with the actual values from Auth0
- Change `MONGO_ROOT_PASSWORD` to a strong, unique password
- `OLLAMA_MODEL` must be a model that supports tool/function calling. `llama3.1:8b` is the recommended choice. **Do not use Gemma or Llama 2** — they do not support function calling and the agent will not work.

#### Choosing an AI Model

The model you choose affects speed and quality:

| Model | Download Size | RAM Needed | Quality | Notes |
|---|---|---|---|---|
| `llama3.1:8b` | ~4.7 GB | 8 GB | Very Good | **Recommended** — fast and capable |
| `qwen2.5:7b` | ~4.4 GB | 8 GB | Very Good | Good alternative |
| `llama3.1:70b` | ~40 GB | 40+ GB | Excellent | Requires very powerful hardware |

---

### 5.4 Starting the Application

Once your `.env` file is configured, start everything with a single command:

```bash
docker compose up
```

You will see logs from all services printing to your terminal. The first time, Docker will:

1. Build the container images (~5–10 minutes)
2. Download the Ollama AI model (~4–5 GB, 10–20 minutes depending on internet speed)
3. Initialize the MongoDB database

Once you see output like this in the logs, everything is ready:

```
fastapi-app  | INFO:     Application startup complete.
frontend     | /docker-entrypoint.sh: Configuration complete
```

To run in the background (without seeing logs):

```bash
docker compose up -d
```

To view logs when running in the background:

```bash
# All services
docker compose logs -f

# Just the backend
docker compose logs -f fastapi-app

# Just the AI model service
docker compose logs -f ollama
```

To stop the application:

```bash
docker compose down
```

#### Access the Application

Once running, open your browser and go to:

| URL | What it is |
|---|---|
| **http://localhost:3000** | The main web interface |
| **http://localhost:8000/docs** | Interactive API documentation |

---

### 5.5 First-Time Setup

#### Create the First Admin User

By default, every user who signs up gets the `student` role. You need to manually promote the first admin user.

1. Start the application and log in at http://localhost:3000 with the account you want to make admin
2. Open a terminal and run:

```bash
# Connect to the MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p your_mongo_password
```

3. Inside the MongoDB shell, run:

```javascript
use study_planning

// Find your user by email to get their auth0_id
db.users.find({ email: "your-email@example.com" }).pretty()

// Then promote them to admin using the auth0_id from the output above
db.users.updateOne(
  { auth0_id: "auth0|the-id-you-found-above" },
  { $set: { role: "admin" } }
)

exit
```

4. Log out and back in — you now have admin access.

#### Loading Academic Data

If you have academic data to seed (degree curriculum, student records), the seed scripts are located in `CODE/seed_data/`. See [CODE/scripts/populate_academic_data.py](CODE/scripts/populate_academic_data.py) for the data import script.

---

### 5.6 Production Deployment

For production use (on a server rather than your local machine), use the production Docker Compose configuration:

```bash
# Start in production mode
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

**Differences in production mode:**

| Feature | Development | Production |
|---|---|---|
| Code hot-reload | Yes (instant updates) | No (code is baked in) |
| Uvicorn workers | 1 | 4 (handles more concurrent users) |
| Database ports | Exposed locally | Internal only (more secure) |
| Restart on crash | No | Yes (automatic restart) |

#### Pre-Production Security Checklist

Before going live, review the following:

- [ ] **Change MongoDB password** — Use a strong, unique password in `.env`
- [ ] **Use strong Auth0 secrets** — Make sure Auth0 Client Secret is long and random
- [ ] **Enable HTTPS** — Set up a reverse proxy (e.g., Nginx or Caddy) with a valid SSL certificate
- [ ] **Update Auth0 callback URLs** — Replace `localhost:3000` with your actual domain
- [ ] **Update CORS settings** — Set `CORS_ORIGINS` to your actual domain in `.env`
- [ ] **Set up MongoDB backups** — The `mongo-data` Docker volume contains all user data
- [ ] **Monitor logs** — Regularly check logs for errors or suspicious activity
- [ ] **Keep dependencies updated** — Rebuild images periodically to get security patches

#### Updating Auth0 URLs for a Custom Domain

If you're deploying to `https://myapp.example.com`, update these in your Auth0 dashboard:

| Auth0 Setting | Value |
|---|---|
| Allowed Callback URLs | `https://myapp.example.com` |
| Allowed Logout URLs | `https://myapp.example.com` |
| Allowed Web Origins | `https://myapp.example.com` |

And update these in your `.env`:

```bash
VITE_AUTH0_REDIRECT_URI=https://myapp.example.com
CORS_ORIGINS=https://myapp.example.com
```

Then rebuild the frontend:

```bash
docker compose -f docker-compose.prod.yml up --build frontend
```

#### GPU Acceleration (Optional)

If your server has an NVIDIA GPU, you can significantly speed up AI responses. The GPU support is already configured in `docker-compose.yml` — you just need to install the NVIDIA Container Toolkit:

```bash
# Fedora / RHEL / Rocky Linux
sudo dnf install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Ubuntu / Debian
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify GPU is accessible to Docker
docker run --rm --gpus all ubuntu nvidia-smi

# Then start the application normally
docker compose up -d
```

---

## 6. User Guide

### 6.1 Logging In

1. Open the application at http://localhost:3000 (or your deployed URL)
2. Click **Log In** on the home screen
3. You will be redirected to an Auth0 login page where you can sign in with email/password or social login (if configured in Auth0)
4. After logging in, you are redirected back to the application

The first time you log in, your account is created automatically with the `student` role.

### 6.2 Uploading Documents

Navigate to the **Upload** page from the main menu.

**Supported file types:**

| Type | Extensions |
|---|---|
| PDF documents | `.pdf` |
| Word documents | `.doc`, `.docx` |
| Excel spreadsheets | `.xls`, `.xlsx` |
| Plain text | `.txt` |
| Markdown | `.md` |

**Upload options:**
- **Private** (default) — Only you can see and search this file
- **Public** (admin only) — All users can see and search this file

Once uploaded, the file is processed automatically: its text is extracted and indexed so the AI can search it. This usually takes a few seconds.

### 6.3 Asking Questions

Navigate to the **Query** page from the main menu.

Type your question in the text box and press Enter or click Send. You can ask in Spanish or English — the AI will respond in the same language.

**Example questions you can ask:**

| Type | Example |
|---|---|
| Academic record | *"¿Cuáles son mis notas del año pasado?"* |
| Available courses | *"What courses can I enroll in next semester?"* |
| Prerequisites | *"Can I take Operating Systems? What do I need first?"* |
| Degree progress | *"How many credits do I have left to graduate?"* |
| Study plan | *"What would you recommend I take next semester?"* |
| Document content | *"Summarize the algorithms course syllabus"* |
| General question | *"What is the difference between a stack and a queue?"* |

**Conversation context:** The AI remembers earlier messages within the same conversation. You can ask follow-up questions without repeating context:

> *You: "What courses can I take next?"*
> *AI: [lists courses]*
> *You: "Tell me more about the first one."*

**Starting a new conversation:** Click **New Conversation** to start fresh.

**Feedback:** After each response, you can click the thumbs-up or thumbs-down icon and optionally leave a comment.

### 6.4 Managing Files

Navigate to the **Files** page from the main menu.

Here you can see all files you have access to (your private files + all public files uploaded by admins). You can:
- See when a file was uploaded and its size
- Delete your own files (admins can delete any file)

### 6.5 Admin Features

Users with the `admin` role have access to additional capabilities:

**Admin Dashboard:**
- View all users and their activity
- See system-wide statistics (total queries, uploads, active users)
- Upload public documents visible to all students

**Feedback Management:**
- View all feedback left by students with full filtering (by rating, user, file, date range)
- Request an AI-powered summary of feedback patterns

To access admin features, log in with an account that has been promoted to admin (see [First-Time Setup](#55-first-time-setup)).

---

## 7. Configuration Reference

All configuration is done via the `.env` file in the root of the project.

### Database

| Variable | Default | Description |
|---|---|---|
| `MONGO_ROOT_USERNAME` | `admin` | MongoDB root username |
| `MONGO_ROOT_PASSWORD` | `password` | MongoDB root password — **change this!** |
| `MONGO_DATABASE_NAME` | `study_planning` | Database name |

### Auth0

| Variable | Description |
|---|---|
| `VITE_AUTH0_DOMAIN` | Your Auth0 tenant domain (frontend) |
| `VITE_AUTH0_CLIENT_ID` | Auth0 SPA Client ID (frontend) |
| `VITE_AUTH0_AUDIENCE` | Your API identifier in Auth0 (frontend) |
| `VITE_AUTH0_REDIRECT_URI` | URL to redirect to after login |
| `AUTH0_DOMAIN` | Your Auth0 tenant domain (backend) |
| `AUTH0_API_AUDIENCE` | Your API identifier in Auth0 (backend) |
| `AUTH0_CLIENT_ID` | M2M Application Client ID (backend) |
| `AUTH0_CLIENT_SECRET` | M2M Application Client Secret (backend — keep secret!) |

### AI Model

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Internal URL to the Ollama service |
| `OLLAMA_MODEL` | `llama3.1:8b` | Model to use. Must support function calling. |
| `OLLAMA_TIMEOUT` | `180` | Seconds to wait for a model response before timing out |

**Compatible models** (must support tool/function calling):

| Model | Description |
|---|---|
| `llama3.1:8b` | Recommended — fast and capable |
| `llama3.1:70b` | Higher quality, requires much more RAM |
| `qwen2.5:7b` | Good alternative |
| `mistral:7b` | Solid general-purpose option |

> **Incompatible models:** `gemma3`, `llama2`, and most models without explicit tool-calling support will cause `status code 400` errors. Stick to the list above.

### Agent & Response

| Variable | Default | Description |
|---|---|---|
| `AGENT_PROVIDER` | `react` | Agent type: `react` (recommended) or `instructor` (advanced) |
| `DEFAULT_LANGUAGE` | `auto` | Response language: `auto`, `english`, or `spanish` |
| `MAX_CONTEXT_LENGTH` | `1500` | Maximum characters of document context sent to the LLM |
| `UPLOAD_DIR` | `data/uploads` | Directory for uploaded files |

**Agent providers:**

| Provider | Speed | Use Case |
|---|---|---|
| `react` | Fast | Production use — recommended for all use cases |
| `instructor` | Slower | Complex queries requiring explicit step-by-step reasoning, confidence scoring, and clarifying questions |

### Changing the AI Model

```bash
# 1. Edit .env
OLLAMA_MODEL=qwen2.5:7b

# 2. Pull the new model
docker exec study-planning-ollama ollama pull qwen2.5:7b

# 3. Restart the backend
docker compose restart fastapi-app
```

---

## 8. API Reference

The backend exposes a REST API. When the application is running, interactive documentation is available at **http://localhost:8000/docs**.

All endpoints (except `/health`) require a valid Auth0 JWT in the `Authorization: Bearer <token>` header.

### Core Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/rag/query` | Send a question to the AI agent |
| `POST` | `/rag/search` | Search documents without AI (returns raw chunks) |
| `GET` | `/rag/stats` | Get usage statistics for the current user |

**Query example:**
```bash
curl -X POST "http://localhost:8000/rag/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What courses can I enroll in next semester?",
    "language": "auto",
    "conversation_id": "optional-existing-conversation-id"
  }'
```

### File Management

| Method | Path | Description | Who |
|---|---|---|---|
| `POST` | `/files/upload` | Upload a file | All users |
| `GET` | `/files/` | List accessible files | All users |
| `GET` | `/files/{filename}` | Get file metadata | All users |
| `DELETE` | `/files/{filename}` | Delete a file | Owner or admin |
| `GET` | `/files/supported/extensions` | List supported file types | All users |

### User Profiles

| Method | Path | Description |
|---|---|---|
| `GET` | `/users/me` | Get your profile |
| `GET` | `/users/me/stats` | Get your usage statistics |
| `PATCH` | `/users/me` | Update your profile |

### Conversations

| Method | Path | Description |
|---|---|---|
| `GET` | `/conversations/` | List all your conversations |
| `GET` | `/conversations/{id}` | Get a full conversation with all messages |
| `DELETE` | `/conversations/{id}` | Delete a conversation |

### Feedback

| Method | Path | Description |
|---|---|---|
| `POST` | `/feedback/message` | Submit a like/dislike on a specific message |
| `POST` | `/feedback/` | Submit general feedback |

### Admin (admin role required)

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/users` | List all users |
| `GET` | `/admin/users/{id}` | Get a specific user's details |
| `GET` | `/admin/stats` | System-wide statistics |
| `GET` | `/admin/feedback` | List all feedback (paginated, filterable) |
| `GET` | `/admin/feedback/stats` | Feedback statistics |
| `POST` | `/admin/feedback/summary` | Generate an AI summary of feedback |
| `GET` | `/admin/feedback/file/{filename}` | Feedback for a specific file |

---

## 9. Development Guide

### Making Code Changes

The development setup uses **hot-reload** — most code changes take effect immediately without rebuilding.

**Backend changes** (Python code in `CODE/`):

```bash
# Just edit the files — changes reload automatically
# Watch the logs for reload confirmation:
docker compose logs -f fastapi-app
```

**Frontend changes** (React code in `FRONTEND/`):

Option 1 — Rebuild the Docker container (slower, but matches production):
```bash
docker compose up --build frontend
```

Option 2 — Run the native dev server (faster, recommended for active development):
```bash
cd FRONTEND
npm install
npm run dev
# Available at http://localhost:5173
```

### Adding a New AI Tool

The AI agent's capabilities are defined as tools. To add a new tool:

1. Define the tool function in [CODE/app/agents/react_langgraph_provider.py](CODE/app/agents/react_langgraph_provider.py) using the `@tool` decorator:

```python
@tool
async def my_new_tool(param: str) -> dict:
    """Describe what this tool does.

    Use this when the user asks about X.

    Args:
        param: Description of the parameter

    Returns:
        Dict with results
    """
    result = await self.tool_executor.execute(
        tool_name="my_tool_endpoint",
        parameters={"param": param},
        user=self._current_user
    )
    if result.error:
        return {"error": result.error}
    return result.result
```

2. Add it to the list returned by `_create_tools()`.
3. Implement the corresponding endpoint in `AGENT_API/`.

See [DOCUMENTATION/ADDING_AGENT_TOOLS.md](DOCUMENTATION/ADDING_AGENT_TOOLS.md) for a complete step-by-step guide with examples.

### Database Operations

```bash
# Open the MongoDB shell
docker exec -it study-planning-mongodb mongosh -u admin -p your_password

# Inside the shell:
use study_planning
show collections

# View users
db.users.find().pretty()

# Promote a user to admin
db.users.updateOne(
  { auth0_id: "auth0|..." },
  { $set: { role: "admin" } }
)

# View recent conversations
db.conversations.find().sort({ created_at: -1 }).limit(5).pretty()

# View feedback
db.feedback.find().sort({ created_at: -1 }).limit(10).pretty()

exit
```

### Running Tests

```bash
# Backend unit tests
docker exec study-planning-api python tests/test_direct.py

# RAG integration tests (application must be running)
docker exec study-planning-api python tests/test_rag.py
```

### Managing AI Models

```bash
# List downloaded models
docker exec study-planning-ollama ollama list

# Download a new model
docker exec study-planning-ollama ollama pull llama3.1:8b

# Remove a model (frees disk space)
docker exec study-planning-ollama ollama rm old-model-name
```

---

## 10. Troubleshooting

### "LLM service not available" (503 Error)

**Cause:** Docker doesn't have enough memory to run the AI model.

**Fix:**
1. Open Docker Desktop
2. Go to **Settings → Resources**
3. Increase **Memory** to at least **10 GB**
4. Click **Apply & Restart**
5. Then restart the application:
```bash
docker compose down
docker compose up -d
```

### Login Fails / Redirects to Blank Page

**Cause:** Auth0 is not configured to allow your application's URL.

**Fix:**
1. Go to [manage.auth0.com](https://manage.auth0.com)
2. Open **Applications → Applications → Study Planning Frontend**
3. Verify these are set correctly:
   - **Allowed Callback URLs:** `http://localhost:3000`
   - **Allowed Logout URLs:** `http://localhost:3000`
   - **Allowed Web Origins:** `http://localhost:3000`
4. Click **Save Changes**
5. Verify the same values in your `.env` file
6. Rebuild the frontend:
```bash
docker compose up --build frontend
```

### "Tool calling not supported" / Agent Returns Errors

**Cause:** The configured model does not support function/tool calling.

**Fix:**
1. Check your `.env` file — make sure `OLLAMA_MODEL` is not set to `gemma3`, `llama2`, or another incompatible model
2. Change it to a compatible model:
```bash
# In .env:
OLLAMA_MODEL=llama3.1:8b

# Then pull and restart:
docker exec study-planning-ollama ollama pull llama3.1:8b
docker compose restart fastapi-app
```

### MongoDB Connection Error

```bash
# Check if MongoDB is running
docker compose ps mongodb

# View MongoDB logs
docker compose logs -f mongodb

# Verify your credentials match
# .env file MONGO_ROOT_USERNAME and MONGO_ROOT_PASSWORD must match
# the values that were used when MongoDB was first started

# If credentials are mismatched, you may need to reset the database:
docker compose down
docker volume rm conversational-interface-for-study-planning_mongo-data
docker compose up -d
```

> **Warning:** Deleting the `mongo-data` volume erases all stored users, conversations, and feedback. Only do this if you are okay losing that data.

### ChromaDB / Search Not Working

Documents are automatically re-indexed when the backend starts. If search is returning no results after uploading a file:

```bash
# Restart the backend to trigger re-indexing
docker compose restart fastapi-app

# Watch the logs for indexing confirmation
docker compose logs -f fastapi-app | grep -i "index"
```

### Agent Gives Incomplete or Incorrect Answers

1. Verify `AGENT_PROVIDER=react` is set in your `.env`
2. Check the agent logs for errors:
```bash
docker compose logs -f fastapi-app | grep -E "(ERROR|tool|agent)"
```
3. Make sure the correct academic data has been loaded into MongoDB
4. Try being more specific in your question

### First Startup Is Taking Very Long

This is normal — the AI model download is ~4–5 GB. You can check the progress:

```bash
docker compose logs -f ollama
```

You will see progress output as the model downloads.

### GPU Not Being Used

```bash
# Verify your GPU is visible to Docker
docker run --rm --gpus all ubuntu nvidia-smi

# If that fails, install NVIDIA Container Toolkit (see Production Deployment section)

# Once installed, verify the running container has GPU access
docker exec study-planning-ollama nvidia-smi
```

---

## 11. Project Structure

```
Conversational-interface-for-study-planning/
│
├── .env.example                    # Template for environment variables
├── docker-compose.yml              # Development setup (all 6 services)
├── docker-compose.prod.yml         # Production setup
│
├── FRONTEND/                       # Web interface (React + Vite)
│   ├── src/
│   │   ├── App.jsx                 # Root component and routing
│   │   ├── pages/                  # Home, Upload, Query, Files pages
│   │   ├── components/             # Reusable UI components
│   │   ├── services/api.js         # Backend API client
│   │   ├── context/                # Auth context
│   │   └── i18n.js                 # Internationalization (ES/EN)
│   ├── public/                     # Static assets
│   ├── Dockerfile                  # Multi-stage build (Vite → Nginx)
│   ├── nginx.conf                  # Nginx configuration
│   └── package.json
│
├── CODE/                           # Backend API (FastAPI + Python)
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry, startup events
│   │   ├── agents/
│   │   │   ├── react_langgraph_provider.py  # ReAct AI agent (recommended)
│   │   │   └── base.py             # Agent interface
│   │   ├── api/routes/
│   │   │   ├── rag.py              # /rag/* endpoints
│   │   │   ├── files.py            # /files/* endpoints
│   │   │   ├── users.py            # /users/* endpoints
│   │   │   ├── admin.py            # /admin/* endpoints
│   │   │   ├── conversations.py    # /conversations/* endpoints
│   │   │   └── feedback.py         # /feedback/* endpoints
│   │   ├── services/               # Business logic (RAG, files, users...)
│   │   ├── core/                   # Config, security, exceptions
│   │   ├── db/                     # MongoDB models and connection
│   │   └── tools/http_executor.py  # Tool execution bridge to Agent API
│   ├── seed_data/                  # Academic data for initial load
│   ├── scripts/                    # Utility scripts (init DB, etc.)
│   ├── tests/                      # Backend tests
│   ├── requirements.txt            # Python dependencies
│   └── Dockerfile
│
├── AGENT_API/                      # Agent Tools Microservice (FastAPI)
│   ├── app/
│   │   ├── main.py                 # FastAPI entry
│   │   ├── api/routes/tools.py     # Tool endpoints
│   │   └── services/tool_services.py  # Tool business logic
│   ├── requirements.txt
│   └── Dockerfile
│
└── DOCUMENTATION/
    └── ADDING_AGENT_TOOLS.md       # Developer guide for adding new tools
```

---

## 12. Technology Stack

### Backend

| Technology | Role |
|---|---|
| **Python 3.11** | Backend programming language |
| **FastAPI** | High-performance web framework |
| **LangGraph** | Agent workflow orchestration |
| **LangChain** | LLM application framework and tool calling |
| **Ollama** | Local LLM inference engine |
| **ChromaDB** | Vector database for semantic search |
| **SentenceTransformers** | Text embedding models |
| **MongoDB (Motor)** | Async document database |
| **Auth0 + python-jose** | Authentication and JWT validation |
| **PyPDF / python-docx / openpyxl** | Document parsing |
| **Instructor** | Structured LLM output (advanced agent) |

### Frontend

| Technology | Role |
|---|---|
| **React 19** | UI framework |
| **Vite 7** | Build tool |
| **React Router 7** | Client-side routing |
| **Axios** | HTTP client |
| **Auth0 React SDK** | Authentication |
| **React Markdown** | Markdown rendering in chat |
| **Mermaid** | Diagram rendering |
| **i18next** | Internationalization (ES/EN) |
| **Lucide React** | Icons |
| **Nginx** | Static file serving in production |

### Infrastructure

| Technology | Role |
|---|---|
| **Docker & Docker Compose** | Container orchestration |
| **MongoDB 7** | Persistent storage for all application data |
| **GridFS** | File storage within MongoDB |
| **ChromaDB** | Vector embeddings database |
| **Ollama** | Local LLM runtime (supports GPU acceleration) |

---

## 13. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

*Built as a Final Degree Project at ORT University.*
*Powered by LangGraph, Ollama, and React.*
