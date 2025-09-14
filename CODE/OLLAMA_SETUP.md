# Ollama Service Management

The RAG system requires Ollama to be running for LLM functionality. The startup script now includes automatic Ollama service management.

## Automatic Startup

The enhanced `start_server.sh` script will automatically:

1. **Check if Ollama is running**
2. **Attempt to start Ollama** using multiple methods:
   - systemctl (if installed as system service)
   - Direct execution in background
   - Docker container (if available)
3. **Verify connectivity** and model availability
4. **Handle graceful shutdown** when the script exits

## Usage

### Start Everything (API + Ollama)
```bash
./start_server.sh
```

This will:
- ✅ Check and start Ollama automatically
- ✅ Start the FastAPI server
- ✅ Handle cleanup on exit

### Manual Ollama Management

Use the helper script for manual control:

```bash
# Check Ollama status
./manage_ollama.sh status

# Start Ollama manually
./manage_ollama.sh start

# Stop Ollama
./manage_ollama.sh stop

# Restart Ollama
./manage_ollama.sh restart

# Install a model
./manage_ollama.sh install llama2
./manage_ollama.sh install codellama:7b
```

## Installation Methods

### Method 1: Direct Installation
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2
```

### Method 2: System Service
```bash
# Install as systemd service
sudo systemctl enable ollama
sudo systemctl start ollama
```

### Method 3: Docker
```bash
# Run Ollama in Docker
docker run -d --name ollama -p 11434:11434 ollama/ollama

# Pull a model in Docker
docker exec ollama ollama pull llama2
```

## Popular Models

| Model | Size | Description |
|-------|------|-------------|
| `llama2` | 3.8GB | General purpose, good balance |
| `llama2:7b` | 3.8GB | 7 billion parameters |
| `llama2:13b` | 7.3GB | 13 billion parameters |
| `codellama` | 3.8GB | Specialized for code |
| `mistral` | 4.1GB | Fast and efficient |
| `phi3` | 2.3GB | Smaller, faster model |

## Troubleshooting

### Ollama Won't Start
1. Check if port 11434 is available:
   ```bash
   sudo netstat -tlnp | grep 11434
   ```

2. Check Ollama installation:
   ```bash
   which ollama
   ollama --version
   ```

3. Manual start with logs:
   ```bash
   ollama serve
   ```

### Permission Issues
```bash
# Fix permissions for systemctl
sudo chown $USER:$USER ~/.ollama

# Or run with sudo
sudo ./start_server.sh
```

### Docker Issues
```bash
# Remove and recreate container
docker rm -f ollama
docker run -d --name ollama -p 11434:11434 ollama/ollama
```

### Model Issues
```bash
# List available models
curl http://localhost:11434/api/tags

# Pull missing model
ollama pull llama2

# Check model status
./manage_ollama.sh status
```

## Environment Variables

Set these in your `.env` file:

```bash
# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Alternative host/port
OLLAMA_HOST=0.0.0.0
OLLAMA_PORT=11434
```

## Advanced Configuration

### Custom Model Location
```bash
export OLLAMA_MODELS=/path/to/models
ollama serve
```

### GPU Support
```bash
# NVIDIA GPU
docker run -d --gpus all --name ollama -p 11434:11434 ollama/ollama

# Check GPU usage
nvidia-smi
```

### Multiple Models
```bash
# Install multiple models for different tasks
./manage_ollama.sh install llama2        # General purpose
./manage_ollama.sh install codellama     # Code generation
./manage_ollama.sh install mistral       # Fast responses
```

## Integration Notes

- The RAG system will work without Ollama (RAG-only mode)
- LLM features require Ollama to be running
- Models are downloaded automatically when first used
- The startup script handles most common scenarios automatically
