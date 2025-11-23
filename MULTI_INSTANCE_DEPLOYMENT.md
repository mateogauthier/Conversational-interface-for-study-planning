# Multi-Instance Deployment Guide

This guide explains how to deploy multiple API instances for horizontal scaling.

## Architecture Overview

The system has been updated to support multiple API instances sharing common backend services:

```
┌─────────────────────────────────────┐
│       Load Balancer (NGINX)         │
└────────┬────────────────────────────┘
         │
         ├──> API Instance 1 ──┐
         ├──> API Instance 2 ──┤
         └──> API Instance 3 ──┤
                                │
         ┌──────────────────────┴──────────┐
         │                                  │
         ▼                                  ▼
┌──────────────────┐          ┌──────────────────┐
│ ChromaDB Server  │          │ MongoDB Database │
│ (Vector Search)  │          │ (Files + Meta)   │
└──────────────────┘          └──────────────────┘
         │
         └────────────┐
                      ▼
              ┌──────────────────┐
              │ Ollama (LLM)     │
              └──────────────────┘
```

## Key Changes

### 1. File Storage: GridFS

**Previous**: Files stored in local Docker volume (`uploads:/app/data/uploads`)
- ❌ Each API instance had its own filesystem
- ❌ Files uploaded to instance A not visible to instance B

**Now**: Files stored in MongoDB GridFS
- ✅ All API instances access same MongoDB
- ✅ Files uploaded to any instance visible to all instances
- ✅ Automatic replication with MongoDB replica sets

### 2. Vector Database: ChromaDB Client-Server

**Previous**: ChromaDB PersistentClient with local SQLite
- ❌ Each API instance had its own vector database
- ❌ SQLite file-level locking prevented multi-writer access
- ❌ Inconsistent search results across instances

**Now**: ChromaDB HttpClient connecting to shared ChromaDB server
- ✅ Single ChromaDB server serves all API instances
- ✅ Consistent vector search results
- ✅ No SQLite locking issues

### 3. MongoDB Connection Pooling

- Configured connection pool per API instance (default: 10-50 connections)
- Prevents connection exhaustion when running multiple instances

## Prerequisites

- Docker and Docker Compose
- Existing data migrated to GridFS (see Migration section)
- Environment variables configured (see `.env` file)

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# MongoDB Connection Pooling
MONGO_MAX_POOL_SIZE=50  # Max connections per API instance
MONGO_MIN_POOL_SIZE=10  # Min connections to maintain

# ChromaDB Configuration
CHROMADB_MODE=client  # Use "client" for multi-instance, "persistent" for single-instance
CHROMADB_HOST=chromadb-server  # Hostname of ChromaDB server
CHROMADB_PORT=8000  # ChromaDB server port
```

### Default Configuration

The `docker-compose.yml` already includes:
- ChromaDB server service (`chromadb-server`)
- Proper environment variables
- Connection pooling configuration

## Deployment Options

### Option 1: Docker Compose with Replicas (Simple)

For quick testing or small deployments, use Docker Compose replicas:

```bash
# Scale API to 3 instances
docker compose up --scale fastapi-app=3 -d
```

**Note**: This exposes all 3 instances on different ports (8000, 8001, 8002). You'll need a load balancer.

### Option 2: Docker Compose + NGINX Load Balancer (Recommended)

Create an NGINX load balancer service:

**1. Create `nginx-lb.conf`:**

```nginx
upstream api_backend {
    least_conn;  # Use least connections algorithm
    server study-planning-api-1:8000;
    server study-planning-api-2:8000;
    server study-planning-api-3:8000;
}

server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running LLM requests
        proxy_read_timeout 300s;
        proxy_connect_timeout 10s;
    }
}
```

**2. Create `docker-compose.multi-instance.yml`:**

```yaml
services:
  # Load Balancer
  nginx-lb:
    image: nginx:alpine
    container_name: study-planning-lb
    ports:
      - "8000:80"
    volumes:
      - ./nginx-lb.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - fastapi-app-1
      - fastapi-app-2
      - fastapi-app-3
    networks:
      - study-planning-network
    restart: unless-stopped

  # API Instance 1
  fastapi-app-1:
    extends:
      file: docker-compose.yml
      service: fastapi-app
    container_name: study-planning-api-1
    ports: []  # Don't expose directly

  # API Instance 2
  fastapi-app-2:
    extends:
      file: docker-compose.yml
      service: fastapi-app
    container_name: study-planning-api-2
    ports: []  # Don't expose directly

  # API Instance 3
  fastapi-app-3:
    extends:
      file: docker-compose.yml
      service: fastapi-app
    container_name: study-planning-api-3
    ports: []  # Don't expose directly
```

**3. Deploy:**

```bash
docker compose -f docker-compose.yml -f docker-compose.multi-instance.yml up -d
```

### Option 3: Kubernetes (Production)

For production deployments, use Kubernetes:

**1. Create `kubernetes/api-deployment.yaml`:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: study-planning-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: study-planning-api
  template:
    metadata:
      labels:
        app: study-planning-api
    spec:
      containers:
      - name: api
        image: your-registry/study-planning-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGO_URI
          valueFrom:
            secretKeyRef:
              name: mongo-secrets
              key: uri
        - name: CHROMADB_MODE
          value: "client"
        - name: CHROMADB_HOST
          value: "chromadb-server"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 40
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: study-planning-api
spec:
  selector:
    app: study-planning-api
  ports:
  - port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## Migration from Single-Instance

### Step 1: Migrate Files to GridFS

Before deploying multiple instances, migrate existing files:

```bash
# From CODE directory
cd CODE

# Dry run (verify what will be migrated)
python scripts/migrate_files_to_gridfs.py --verify

# Migrate files (keep local copies)
python scripts/migrate_files_to_gridfs.py

# Migrate files (delete local copies after migration)
python scripts/migrate_files_to_gridfs.py --delete-local
```

### Step 2: Update Configuration

Ensure these environment variables are set:

```bash
CHROMADB_MODE=client
CHROMADB_HOST=chromadb-server
CHROMADB_PORT=8000
```

### Step 3: Restart Services

```bash
# Stop existing services
docker compose down

# Start with new configuration
docker compose up -d
```

### Step 4: Verify Migration

```bash
# Check API logs
docker logs study-planning-api

# Should see:
# "Connected to ChromaDB server at chromadb-server:8000"
# "Successfully connected to MongoDB database: study_planning (pool size: 10-50)"

# Verify ChromaDB server
curl http://localhost:8001/api/v1/heartbeat

# Should return: {"nanosecond heartbeat": ...}
```

### Step 5: Scale Up (if using replicas)

```bash
# Scale to 3 instances
docker compose up --scale fastapi-app=3 -d
```

## Monitoring and Troubleshooting

### Check Instance Health

```bash
# Check all running containers
docker ps

# Check API instance logs
docker logs study-planning-api-1
docker logs study-planning-api-2
docker logs study-planning-api-3

# Check ChromaDB server
docker logs study-planning-chroma

# Check MongoDB
docker logs study-planning-mongodb
```

### Verify Load Balancing

```bash
# Make multiple requests and check which instance handles them
for i in {1..10}; do
  curl http://localhost:8000/health
done

# Check NGINX logs
docker logs study-planning-lb
```

### Common Issues

#### Issue 1: "FileService not initialized"

**Cause**: RAG service doesn't have access to file_service

**Solution**: Ensure services are properly initialized in `main.py`:

```python
# In app/main.py startup event
from app.services.file_service import get_file_service_instance
from app.services.rag_service import RAGService

@app.on_event("startup")
async def startup_event():
    await database.mongodb.connect()
    db = database.mongodb.get_database()

    # Initialize file service
    file_service = get_file_service_instance(db)

    # Initialize RAG service with file_service
    global rag_service
    rag_service = RAGService(file_service=file_service)
```

#### Issue 2: "Connection refused to chromadb-server"

**Cause**: ChromaDB server not running or CHROMADB_MODE still set to "persistent"

**Solution**:
```bash
# Check if ChromaDB server is running
docker ps | grep chroma

# Check environment variable
docker exec study-planning-api printenv | grep CHROMADB_MODE

# Should output: CHROMADB_MODE=client
```

#### Issue 3: MongoDB connection pool exhaustion

**Symptoms**: "MongoServerSelectionTimeoutError" or "Too many connections"

**Solution**:
```bash
# Check MongoDB connection count
docker exec study-planning-mongodb mongosh -u admin -p password --eval "db.serverStatus().connections"

# Reduce MONGO_MAX_POOL_SIZE per instance
# Example: 3 instances × 50 connections = 150 total
# MongoDB default limit: 1024
```

## Performance Considerations

### Connection Pool Sizing

**Formula**: `(Number of API instances) × (MONGO_MAX_POOL_SIZE) < MongoDB max connections`

**Example**:
- 3 API instances
- MONGO_MAX_POOL_SIZE=50
- Total: 3 × 50 = 150 connections
- MongoDB default limit: 1024 ✅

### ChromaDB Performance

- ChromaDB server adds ~5-10ms latency vs local PersistentClient
- Acceptable trade-off for multi-instance consistency

### LLM Bottleneck

If Ollama becomes the bottleneck, consider:

**Option A**: Multiple Ollama instances with load balancer (see Architecture Analysis document)

**Option B**: External LLM service (OpenAI, Anthropic) for auto-scaling

## Scaling Guidelines

| Concurrent Users | Recommended API Instances | MONGO_MAX_POOL_SIZE |
|-----------------|---------------------------|---------------------|
| < 50            | 1                         | 50                  |
| 50-150          | 2-3                       | 50                  |
| 150-500         | 3-5                       | 30                  |
| 500+            | 5+                        | 20                  |

## Security Considerations

### Production Checklist

- [ ] Change default MongoDB passwords
- [ ] Use TLS for MongoDB connections
- [ ] Add authentication to ChromaDB server
- [ ] Use HTTPS for API (configure in NGINX)
- [ ] Set up firewall rules (only allow API → MongoDB, API → ChromaDB)
- [ ] Implement rate limiting in NGINX
- [ ] Enable MongoDB audit logging
- [ ] Regular backups of MongoDB data

### ChromaDB Authentication (Optional)

```yaml
# In docker-compose.yml
chromadb-server:
  environment:
    - CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER=chromadb.auth.token.TokenAuthCredentialsProvider
    - CHROMA_SERVER_AUTH_TOKEN_TRANSPORT_HEADER=X-Chroma-Token
    - CHROMA_SERVER_AUTH_CREDENTIALS=your-secret-token
```

Then update RAG service:

```python
# In rag_service.py
self.client = chromadb.HttpClient(
    host=settings.chromadb_host,
    port=settings.chromadb_port,
    headers={"X-Chroma-Token": settings.chromadb_token}
)
```

## Rollback Procedure

If you need to rollback to single-instance:

```bash
# 1. Stop all services
docker compose down

# 2. Update environment variables
export CHROMADB_MODE=persistent

# 3. Restore uploads volume (if you kept backups)
docker volume create uploads
# Copy files back from backup

# 4. Start services
docker compose up -d
```

**Note**: Files in GridFS will remain accessible even in single-instance mode.

## Summary

✅ **What's Now Possible:**
- Run 2-5 API instances for load distribution
- Files accessible from all instances (GridFS)
- Consistent vector search (ChromaDB server)
- Horizontal scaling without data conflicts

⚠️ **Known Limitations:**
- Single ChromaDB server (not horizontally scalable itself)
- Single Ollama instance (potential bottleneck)
- GridFS slightly slower than local filesystem (~10-20% for small files)

🚀 **Next Steps for Production Scale:**
- Replace ChromaDB with Qdrant (supports clustering)
- Multiple Ollama instances with load balancer
- MongoDB replica set for high availability
- Kubernetes for auto-scaling and orchestration
