# Agent Tools API

Separate microservice that provides tool execution endpoints for the agent system.

## Overview

This API serves as a dedicated service for agent tool execution, separating concerns from the main application API. It provides endpoints that agents can call to interact with:

- **File operations**: Search, list, get info, delete files
- **Conversation operations**: List conversations
- **User statistics**: Get usage stats
- **Document search**: Semantic search through RAG

## Architecture

The Agent API is designed to be:
- **Independent**: Runs as a separate service on port 8002
- **Scalable**: Can be scaled independently from the main API
- **Extensible**: Easy to add new tools by adding new endpoints
- **Secure**: Shared authentication with main API via Auth0

## Endpoints

### Tool Execution
- `POST /tools/search_documents` - Semantic document search
- `POST /tools/list_files` - List accessible files
- `POST /tools/get_file_info` - Get file details
- `POST /tools/list_conversations` - List user conversations
- `POST /tools/get_user_stats` - Get user statistics
- `POST /tools/delete_file` - Delete a file (with confirmation)

### System
- `GET /` - Root endpoint with API info
- `GET /health` - Health check
- `GET /tools/list` - List all available tools

## Running the Service

### With Docker Compose (Recommended)
```bash
# From repository root
docker compose up agent-api

# Or start all services
docker compose up
```

The service will be available at `http://localhost:8002`

### Native Development
```bash
cd AGENT_API
pip install -r requirements.txt
python -m app.main
```

## Adding New Tools

To add a new tool:

1. **Add the tool endpoint** in `app/api/routes/tools.py`
2. **Create request/response models** in `app/models/schemas.py`
3. **Implement the service logic** in `app/services/tool_services.py`
4. **Update the tool list** in `/tools/list` endpoint
5. **Document** the new tool in this README

Example:
```python
# In app/api/routes/tools.py
@router.post("/new_tool", response_model=NewToolResponse)
async def new_tool(request: NewToolRequest):
    result = await agent_tool_service.execute_new_tool(
        param1=request.param1,
        user_id=request.user_id
    )
    return NewToolResponse(success=True, **result)
```

## Environment Variables

The Agent API shares configuration with the main API:

- `MONGO_URI` - MongoDB connection string
- `MONGO_DATABASE_NAME` - Database name
- `AUTH0_DOMAIN` - Auth0 domain for JWT verification
- `AUTH0_API_AUDIENCE` - Auth0 API audience
- `CORS_ORIGINS` - Allowed CORS origins

## Dependencies

The Agent API imports services from the main API (`CODE/app/services/`) to avoid code duplication. This is achieved through volume mounts in Docker Compose.

## Security

- All endpoints require user authentication information (user_id, auth0_id, role)
- User permissions are enforced at the service layer
- Sensitive operations (delete) require confirmation in the agent flow

## Future Enhancements

Potential additions:
- Read specific file content tool
- Update file metadata tool
- Batch operations tool
- Export/import conversation tool
- Analytics and reporting tools
