# Docker Quick Start Guide

## Important: Use `docker compose` not `docker-compose`

Your system has Docker Compose v2 installed as a plugin. Use the command **`docker compose`** (with a space) instead of `docker-compose` (with a hyphen).

## Quick Start (From Repository Root)

```bash
# Navigate to repository root
cd /home/mgauthier/Documents/GitHub/Conversational-interface-for-study-planning

# Start development environment (with hot-reload)
docker compose up

# Or run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop containers
docker compose down
```

## First Time Setup

When you run `docker compose up` for the first time:

1. Docker will build the FastAPI application image (~5-10 minutes)
2. Download the Ollama image (~1GB)
3. Start both services
4. Ollama will automatically pull the `llama2:latest` model (~4GB, can take 10-20 minutes)

**Note**: The first startup will be slow due to model download. Subsequent startups will be much faster.

## Development Workflow

### Making Code Changes

1. Edit any file in the `CODE/` directory
2. **Changes are reflected immediately** - no rebuild needed!
3. The FastAPI server will automatically reload

### When to Rebuild

Only rebuild when you modify dependencies:

```bash
# After changing CODE/requirements.txt
docker compose up --build
```

## Accessing the Application

Once running:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Common Commands

```bash
# View running containers
docker compose ps

# View logs
docker compose logs -f fastapi-app
docker compose logs -f ollama

# Access container shell
docker exec -it study-planning-api bash
docker exec -it study-planning-ollama bash

# Pull a different Ollama model
docker exec study-planning-ollama ollama pull llama3
docker exec study-planning-ollama ollama pull mistral

# List available models
docker exec study-planning-ollama ollama list

# Restart services
docker compose restart

# Stop and remove everything (keeps volumes/data)
docker compose down

# Stop and remove everything INCLUDING data
docker compose down -v  # WARNING: Deletes uploads and database!
```

## Production Deployment

```bash
# Use production configuration
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml down
```

## Troubleshooting

### Ollama Not Starting

```bash
# Check Ollama logs
docker compose logs ollama

# Restart Ollama service
docker compose restart ollama
```

### API Not Connecting to Ollama

```bash
# Check if both containers are on same network
docker network inspect conversational-interface-for-study-planning_study-planning-network

# Verify Ollama is accessible from API container
docker exec study-planning-api curl http://ollama:11434/api/tags
```

### Rebuild from Scratch

```bash
# Remove everything
docker compose down -v

# Remove images
docker rmi study-planning-api:latest

# Rebuild and start
docker compose up --build
```

### Check Disk Space

Docker images and volumes can use significant space:

```bash
# Check Docker disk usage
docker system df

# Clean up unused images/containers
docker system prune -a
```

## Data Persistence

Your data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep study-planning

# Backup uploads volume
docker run --rm -v conversational-interface-for-study-planning_uploads:/data -v $(pwd):/backup ubuntu tar czf /backup/uploads-backup.tar.gz -C /data .

# Backup ChromaDB
docker run --rm -v conversational-interface-for-study-planning_chroma_db:/data -v $(pwd):/backup ubuntu tar czf /backup/chroma-backup.tar.gz -C /data .

# Restore uploads
docker run --rm -v conversational-interface-for-study-planning_uploads:/data -v $(pwd):/backup ubuntu tar xzf /backup/uploads-backup.tar.gz -C /data

# Restore ChromaDB
docker run --rm -v conversational-interface-for-study-planning_chroma_db:/data -v $(pwd):/backup ubuntu tar xzf /backup/chroma-backup.tar.gz -C /data
```

## GPU Support (Optional)

If you have an NVIDIA GPU and want faster LLM inference:

1. Install [nvidia-docker](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
2. Uncomment the GPU section in `docker-compose.yml`:

```yaml
# In the ollama service section, uncomment:
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

3. Restart: `docker compose up -d`
