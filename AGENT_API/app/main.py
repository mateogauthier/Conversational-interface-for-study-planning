"""Agent API - Microservice for agent tool execution.

This API provides endpoints for agent tools to execute operations
by calling the main API via HTTP endpoints, ensuring complete independence.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import tools
from app.models.schemas import HealthResponse
from app.services.tool_services import agent_tool_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Agent Tools API - Independent microservice for agent tool execution"
)

# Configure CORS
origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        logger.info("Starting Agent API...")
        await agent_tool_service.initialize()
        logger.info("Agent API started successfully")
    except Exception as e:
        logger.error(f"Failed to start Agent API: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        logger.info("Shutting down Agent API...")
        await agent_tool_service.shutdown()
        logger.info("Agent API shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Include routers
app.include_router(tools.router)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint."""
    return HealthResponse(
        status="healthy",
        message="Agent Tools API is running",
        version=settings.api_version
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="Agent Tools API is healthy",
        version=settings.api_version
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
