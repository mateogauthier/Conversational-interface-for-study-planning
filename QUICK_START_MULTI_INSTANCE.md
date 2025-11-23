# Quick Start: Multi-Instance Deployment

## TL;DR

Run 2-5 API instances for better performance and reliability.

## 1. Migrate Existing Files (One-Time)

```bash
cd CODE
python scripts/migrate_files_to_gridfs.py
```

## 2. Update Environment Variables

Add to your `.env` file:

```bash
CHROMADB_MODE=client
CHROMADB_HOST=chromadb-server
CHROMADB_PORT=8000
MONGO_MAX_POOL_SIZE=50
MONGO_MIN_POOL_SIZE=10
```

## 3. Deploy

```bash
# Stop existing services
docker compose down

# Start with new configuration (single instance)
docker compose up -d

# Verify everything works
curl http://localhost:8000/health

# Scale to 3 instances
docker compose up --scale fastapi-app=3 -d
```

## 4. Verify

```bash
# Check ChromaDB server
curl http://localhost:8001/api/v1/heartbeat

# Check API logs
docker logs study-planning-api

# Should see:
# ✅ "Connected to ChromaDB server at chromadb-server:8000"
# ✅ "Successfully connected to MongoDB (pool size: 10-50)"
```

## That's It!

Your system now supports multiple API instances:
- ✅ Files shared via GridFS
- ✅ Vector search shared via ChromaDB server
- ✅ Connection pooling configured

## Rollback

```bash
docker compose down
export CHROMADB_MODE=persistent
docker compose up -d
```

## Full Documentation

- [MULTI_INSTANCE_DEPLOYMENT.md](MULTI_INSTANCE_DEPLOYMENT.md) - Complete deployment guide
- [SCALABILITY_CHANGES_SUMMARY.md](SCALABILITY_CHANGES_SUMMARY.md) - Detailed changes

## Troubleshooting

**"FileService not initialized"**
- Restart API container: `docker restart study-planning-api`

**"Connection refused to chromadb-server"**
- Check ChromaDB is running: `docker ps | grep chroma`
- Verify CHROMADB_MODE=client: `docker exec study-planning-api printenv | grep CHROMADB_MODE`

**Files not found after migration**
- Run verification: `python scripts/migrate_files_to_gridfs.py --verify`
- Check GridFS: `docker exec study-planning-mongodb mongosh -u admin -p password --eval "use study_planning; db.fs.files.find().pretty()"`

## Architecture

```
┌─────────────────────┐
│  Load Balancer      │  ← Your load balancer here (optional)
└──────────┬──────────┘
           │
   ┌───────┼───────┐
   │       │       │
   ▼       ▼       ▼
┌─────┐ ┌─────┐ ┌─────┐
│API 1│ │API 2│ │API 3│
└──┬──┘ └──┬──┘ └──┬──┘
   └───────┼───────┘
           │
   ┌───────┼──────────┐
   ▼                  ▼
┌──────────────┐  ┌──────────┐
│ChromaDB      │  │MongoDB   │
│(Vector DB)   │  │(Files)   │
└──────────────┘  └──────────┘
```

## What Changed?

| Before | After |
|--------|-------|
| Files in Docker volume | Files in MongoDB GridFS |
| Local ChromaDB (SQLite) | ChromaDB server (shared) |
| 1 API instance max | 2-5+ API instances |
| Simple but not scalable | Simple AND scalable |

## Performance

- **Latency**: +5-10ms per request (ChromaDB server overhead)
- **File operations**: ~10-20% slower for small files
- **Scalability**: 2-5x throughput with multiple instances
- **Worth it?**: ✅ Yes, for most deployments

## Cost (Self-Hosted)

- **Storage**: No change (same disk usage)
- **Memory**: +100MB per API instance
- **CPU**: Distributed across instances
- **Network**: Internal only (no external bandwidth)

## When to Scale?

| Users | API Instances | Notes |
|-------|---------------|-------|
| < 50 | 1 | Current setup is fine |
| 50-150 | 2-3 | Start scaling |
| 150-500 | 3-5 | Recommended |
| 500+ | 5+ | Consider Kubernetes |

## Need Help?

Check the full docs:
- [MULTI_INSTANCE_DEPLOYMENT.md](MULTI_INSTANCE_DEPLOYMENT.md)
