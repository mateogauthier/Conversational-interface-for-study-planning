"""Main FastAPI application with Auth0 authentication."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.models import SecuritySchemeType, HTTPBearer
import logging

from app.core.config import get_settings
from app.api.routes import files, llm, rag, users, admin, conversations, feedback, agent
from app.models.responses import APIInfoResponse, HealthResponse
from app.db.database import mongodb
from app.services import conversation_service as conv_service_module
from app.services import feedback_service as feedback_service_module
from app.services import rag_service as rag_service_module
from app.services.file_service import get_file_service_instance
from app.services.llm_service import llm_service
from app.services.user_service import get_user_service
from app.agents.api_provider import create_agent_provider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Create FastAPI app with security scheme
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug,
    swagger_ui_parameters={
        "persistAuthorization": True,  # Keep authorization between page refreshes
    }
)

# Add security scheme to OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your Auth0 JWT token"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Connect to MongoDB
        await mongodb.connect()
        logger.info("MongoDB connected successfully")

        # Initialize conversation service with database
        db = mongodb.get_database()
        conv_service_module.conversation_service = conv_service_module.ConversationService(db)
        logger.info("Conversation service initialized")

        # Initialize feedback service with database
        feedback_service_module.feedback_service = feedback_service_module.FeedbackService(db)
        logger.info("Feedback service initialized")

        # Initialize RAG service with file_service
        file_service = get_file_service_instance(db)
        rag_service_module.rag_service = rag_service_module.RAGService(file_service=file_service)
        logger.info("RAG service initialized with file_service")

        # Auto-reindex all files on startup to ensure ChromaDB is in sync with GridFS
        try:
            logger.info("🔄 Starting automatic file reindexing...")
            all_files = await file_service.list_all_files()

            if not all_files:
                logger.info("No files found to index")
            else:
                total_files = len(all_files)
                indexed_count = 0
                skipped_count = 0
                failed_count = 0

                for file_meta in all_files:
                    filename = file_meta.get("filename")
                    try:
                        # Process document from GridFS
                        chunk_count = await rag_service_module.rag_service.process_document_from_gridfs(
                            filename=filename,
                            user_id=file_meta.get("user_id", "system"),
                            is_public=file_meta.get("is_public", False)
                        )

                        if chunk_count > 0:
                            # Update file metadata with processing status
                            await file_service.update_file_processed_status(
                                filename=filename,
                                processed=True,
                                chunk_count=chunk_count
                            )
                            indexed_count += 1
                            logger.info(f"✓ Indexed {filename}: {chunk_count} chunks")
                        else:
                            skipped_count += 1
                            logger.warning(f"⊘ Skipped {filename}: 0 chunks generated")

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"✗ Failed to index {filename}: {e}")

                logger.info(
                    f"📊 Reindexing complete: {indexed_count}/{total_files} files indexed, "
                    f"{skipped_count} skipped, {failed_count} failed"
                )

        except Exception as e:
            logger.error(f"Auto-reindex failed: {e}")
            # Don't crash the app if reindexing fails

        # Initialize agent provider
        if settings.enable_agent_tools:
            agent_provider = create_agent_provider(
                provider_type=settings.agent_provider,
                llm_service=llm_service,
                rag_service=rag_service_module.rag_service,
                conversation_service=conv_service_module.conversation_service,
                file_service=file_service,
                user_service=get_user_service(db),
                api_url=settings.agent_api_url,
                api_key=settings.agent_api_key,
                fallback_to_local=settings.agent_fallback_to_local,
                max_iterations=settings.agent_max_iterations,
                auto_approve_reads=settings.agent_auto_approve_reads
            )
            agent.set_agent_provider(agent_provider)
            logger.info(f"Agent provider initialized: {settings.agent_provider}")
        else:
            logger.info("Agent tools disabled in configuration")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Don't raise - allow app to start but services may not work


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        # Disconnect from MongoDB
        await mongodb.disconnect()
        logger.info("MongoDB disconnected successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Include routers
app.include_router(files.router)
app.include_router(llm.router)
app.include_router(rag.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
app.include_router(agent.router)


@app.get("/", response_model=APIInfoResponse)
async def root():
    """Root endpoint with API information."""
    return APIInfoResponse(
        message="Study Planning Conversational Interface API - with Authentication",
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        endpoints={
            "authentication": {
                "info": "All endpoints require Bearer token authentication (Auth0)"
            },
            "files": {
                "upload": "POST /files/upload - Upload documents (students: private, admins: public)",
                "list": "GET /files/ - List accessible files",
                "details": "GET /files/{filename} - Get file details",
                "delete": "DELETE /files/{filename} - Delete file (with permission check)",
                "extensions": "GET /files/supported/extensions - Get supported file types"
            },
            "rag": {
                "search": "POST /rag/search - Search documents (user-filtered)",
                "query": "POST /rag/query - RAG query with LLM (user-filtered)",
                "stats": "GET /rag/stats - User-specific RAG statistics",
                "reset": "POST /rag/reset - Reset public documents (admin only)",
                "health": "GET /rag/health - RAG service health check"
            },
            "llm": {
                "query": "POST /llm/query - Direct LLM query",
                "status": "GET /llm/status - LLM service status",
                "models": "GET /llm/models - List available models",
                "ensure": "POST /llm/models/{model}/ensure - Ensure model (admin only)",
                "health": "GET /llm/health - LLM service health check"
            },
            "users": {
                "profile": "GET /users/me - Current user profile",
                "stats": "GET /users/me/stats - Current user statistics",
                "update": "PATCH /users/me - Update profile"
            },
            "conversations": {
                "list": "GET /conversations/ - List user's conversations",
                "get": "GET /conversations/{id} - Get conversation with messages",
                "delete": "DELETE /conversations/{id} - Delete conversation"
            },
            "agent": {
                "query": "POST /agent/query - Agent-powered query with tool execution",
                "confirm": "POST /agent/confirm - Confirm pending agent action",
                "tools": "GET /agent/tools - List available tools for user",
                "health": "GET /agent/health - Agent service health check"
            },
            "admin": {
                "list_users": "GET /admin/users - List all users (admin only)",
                "user_details": "GET /admin/users/{id} - User details (admin only)",
                "user_stats": "GET /admin/users/{id}/stats - User statistics (admin only)",
                "system_stats": "GET /admin/stats - System-wide statistics (admin only)"
            },
            "system": {
                "health": "GET /health - Overall system health check",
                "docs": "GET /docs - API documentation"
            }
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Overall system health check."""
    # Check MongoDB connection
    try:
        db = mongodb.get_database()
        mongo_healthy = True
    except:
        mongo_healthy = False

    return HealthResponse(
        message="API is running" + (" (MongoDB connected)" if mongo_healthy else " (MongoDB disconnected)"),
        status="healthy" if mongo_healthy else "degraded"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
