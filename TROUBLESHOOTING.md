# Troubleshooting Guide

This guide covers common issues and their solutions when using the RAG-powered Study Planning API.

## Table of Contents
- [Windows-Specific Issues](#windows-specific-issues)
- [Docker Build Issues](#docker-build-issues)
- [Runtime Issues](#runtime-issues)
- [LLM/Ollama Issues](#llmollama-issues)
- [RAG/ChromaDB Issues](#ragchromadb-issues)

---

## Windows-Specific Issues

### Docker Build Error: "No such file or directory: /usr/local/bin/docker-entrypoint.sh"

**Symptoms:**
```
ERROR [runtime 5/9] COPY --chown=appuser:appuser CODE/scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
```
or
```
exec /usr/local/bin/docker-entrypoint.sh: no such file or directory
```

**Root Cause:**
Git on Windows may checkout shell scripts with Windows line endings (CRLF - `\r\n`) instead of Unix line endings (LF - `\n`). When Docker copies these files into a Linux container, bash cannot execute them.

**Solutions:**

#### Solution 1: Re-clone with correct Git configuration (Recommended)
```bash
# Configure Git to not convert line endings
git config --global core.autocrlf false

# Re-clone the repository
cd ..
rm -rf Conversational-interface-for-study-planning
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning

# Build should now work
docker compose build
```

#### Solution 2: Fix line endings in existing repository
```bash
# Install dos2unix
# Download from: https://sourceforge.net/projects/dos2unix/
# Or via Chocolatey: choco install dos2unix
# Or via WSL: wsl sudo apt-get install dos2unix

# Convert the script
dos2unix CODE/scripts/docker-entrypoint.sh

# Or if using WSL:
wsl dos2unix CODE/scripts/docker-entrypoint.sh

# Rebuild
docker compose build
```

#### Solution 3: Reset Git line endings
```bash
# This forces Git to re-checkout files with correct line endings
git rm --cached -r .
git reset --hard

# Rebuild
docker compose build
```

#### Prevention:
The repository now includes a `.gitattributes` file that forces shell scripts to always use LF line endings, regardless of your OS. If you still encounter this issue:

1. Make sure you're using Git 2.10+ (supports `.gitattributes` eol directive)
2. Verify `.gitattributes` exists in the repository root
3. Check your global Git config: `git config --global core.autocrlf`
   - Should be `false` or `input` (not `true`)

---

### WSL2 Docker Integration Issues

**Symptoms:**
- Slow file access in containers
- High CPU usage
- Build failures

**Solutions:**

1. **Use WSL2 file system:**
   ```bash
   # Clone inside WSL, not Windows
   cd /home/yourusername
   git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
   ```

2. **Enable WSL2 backend in Docker Desktop:**
   - Settings → General → Use WSL2 based engine
   - Settings → Resources → WSL Integration → Enable for your distro

3. **Increase WSL2 memory limit:**
   Create/edit `C:\Users\YourUsername\.wslconfig`:
   ```ini
   [wsl2]
   memory=8GB
   processors=4
   ```

---

## Docker Build Issues

### "No space left on device"

**Solution:**
```bash
# Clean up Docker
docker system prune -a --volumes
docker builder prune -a

# Check available space
docker system df
```

### Build hangs at "Pulling model..."

**Problem:** First-time model download (4GB+ for llama2) takes 10-20 minutes.

**Solution:**
- Be patient! Watch the logs: `docker compose logs -f ollama`
- Or pull manually:
  ```bash
  docker compose up -d ollama
  docker exec study-planning-ollama ollama pull llama2:latest
  ```

### "Cannot connect to Docker daemon"

**Windows:**
1. Start Docker Desktop
2. Wait for it to fully start (green icon in system tray)
3. Retry

**Linux:**
```bash
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER  # Re-login after this
```

---

## Runtime Issues

### 503 Error: "LLM service not available"

**Symptoms:**
```json
{"detail": "LLM service not available: 503 Service Unavailable"}
```

**Root Cause:** Ollama doesn't have enough memory to load the model.

**Solution:**

1. **Increase Docker Desktop memory:**
   - Settings → Resources → Memory → 8GB minimum (10GB+ recommended)
   - Apply & Restart
   - `docker compose down && docker compose up -d`

2. **Use a smaller model:**
   ```bash
   # Stop containers
   docker compose down
   
   # Edit docker-compose.yml - change OLLAMA_MODEL
   OLLAMA_MODEL: "llama2:7b"  # or "mistral:7b" (smaller)
   
   # Restart
   docker compose up -d
   ```

3. **Check Ollama logs:**
   ```bash
   docker compose logs ollama | grep -i "error\|out of memory"
   ```

### FastAPI container keeps restarting

**Check logs:**
```bash
docker compose logs fastapi-app
```

**Common causes:**

1. **Port 8000 already in use:**
   ```bash
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   
   # Linux/Mac
   lsof -ti:8000 | xargs kill -9
   ```

2. **Ollama not ready:**
   - Wait 1-2 minutes for Ollama to fully start
   - Check: `curl http://localhost:11434/api/tags`

3. **Missing dependencies:**
   ```bash
   docker compose build --no-cache
   docker compose up -d
   ```

### "Connection refused" when calling API

**Solutions:**
```bash
# Check containers are running
docker compose ps

# Check health
curl http://localhost:8000/health
curl http://localhost:11434/api/tags

# Restart
docker compose restart
```

---

## LLM/Ollama Issues

### Ollama model download fails

**Solutions:**

1. **Manual download:**
   ```bash
   docker exec study-planning-ollama ollama pull llama2:latest
   ```

2. **Use different model:**
   ```bash
   docker exec study-planning-ollama ollama pull mistral:latest
   docker exec study-planning-ollama ollama pull llama2:7b
   ```

3. **Check internet connection:**
   ```bash
   docker exec study-planning-ollama curl -I https://ollama.ai
   ```

### Slow LLM responses (30+ seconds)

**Causes & Solutions:**

1. **Insufficient memory:**
   - Increase Docker Desktop memory to 10GB+
   - Or use a smaller model (llama2:7b instead of llama2:13b)

2. **No GPU acceleration:**
   - Install NVIDIA Container Toolkit (Linux only)
   - Uncomment GPU section in docker-compose.yml
   - Restart: `docker compose down && docker compose up -d`

3. **Model not loaded:**
   ```bash
   # Pre-warm the model
   curl http://localhost:11434/api/generate \
     -d '{"model":"llama2","prompt":"test"}'
   ```

### "Model not found" error

**Solution:**
```bash
# List available models
docker exec study-planning-ollama ollama list

# Pull the missing model
docker exec study-planning-ollama ollama pull llama2:latest

# Or specify a different model in .env
echo "OLLAMA_MODEL=mistral:latest" >> CODE/.env
docker compose restart
```

---

## RAG/ChromaDB Issues

### "No documents found in collection"

**Symptoms:**
- Queries return "No relevant information found"
- RAG stats show 0 documents

**Solutions:**

1. **Upload documents:**
   - Go to http://localhost:3000 → Files tab
   - Upload PDF, DOCX, or TXT files

2. **Check if files were processed:**
   ```bash
   curl http://localhost:8000/rag/stats
   # Should show documents > 0 and total_chunks > 0
   ```

3. **Reset and re-upload:**
   ```bash
   # Via API
   curl -X POST http://localhost:8000/rag/reset
   
   # Or delete volume
   docker compose down -v
   docker compose up -d
   ```

### "Failed to process document for RAG"

**Check logs:**
```bash
docker compose logs fastapi-app | grep -i "error\|failed"
```

**Common causes:**

1. **Unsupported file format:**
   - Only PDF, DOCX, XLSX, TXT, MD are supported
   - Check: `curl http://localhost:8000/files/supported/extensions`

2. **Corrupted file:**
   - Try opening the file locally first
   - Re-save as PDF if possible

3. **File too large:**
   - Default limit is 10MB
   - Change in CODE/.env: `MAX_FILE_SIZE_MB=20`

### Vector search returns irrelevant results

**Solutions:**

1. **Adjust chunk settings:**
   ```python
   # Edit CODE/app/core/config.py
   chunk_size: int = 500  # Smaller chunks = more precise
   chunk_overlap: int = 100
   ```

2. **Increase number of chunks retrieved:**
   - Settings page → Context Chunks → 10 or 15

3. **Use better embedding model:**
   ```python
   # Edit CODE/app/core/config.py
   embedding_model: str = "all-mpnet-base-v2"  # More accurate but slower
   ```

---

## General Debugging

### Enable debug logging

**For FastAPI:**
```bash
# Edit docker-compose.yml
environment:
  LOG_LEVEL: DEBUG

# Restart
docker compose restart fastapi-app
```

**For Ollama:**
```bash
docker compose logs -f ollama
```

### Access container shell

```bash
# FastAPI container
docker exec -it study-planning-api bash

# Check environment
env | grep -i ollama

# Test ChromaDB
python -c "import chromadb; print(chromadb.__version__)"

# Ollama container
docker exec -it study-planning-ollama bash
ollama list
```

### Reset everything (nuclear option)

```bash
# Stop and remove all containers, networks, volumes
docker compose down -v

# Remove images (optional, forces rebuild)
docker compose down --rmi all

# Clean Docker cache
docker builder prune -a

# Start fresh
docker compose up --build -d
```

### Performance monitoring

```bash
# Container resource usage
docker stats

# FastAPI metrics
curl http://localhost:8000/health

# Ollama status
curl http://localhost:11434/api/tags

# ChromaDB stats
curl http://localhost:8000/rag/stats
```

---

## Still Having Issues?

1. **Check the main README:** [README.md](README.md)
2. **Review Docker logs:** `docker compose logs -f`
3. **Open an issue:** [GitHub Issues](https://github.com/yourusername/Conversational-interface-for-study-planning/issues)
4. **Include in your report:**
   - Operating system and version
   - Docker version: `docker --version`
   - Docker Compose version: `docker compose version`
   - Full error message and logs
   - Steps to reproduce

---

**Last updated:** 2024-11-10
