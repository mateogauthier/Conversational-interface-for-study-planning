"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import get_settings
from app.api.routes import files, llm, rag
from app.models.responses import APIInfoResponse, HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    debug=settings.debug
)

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


@app.get("/", response_model=APIInfoResponse)
async def root():
    """Root endpoint with API information."""
    return APIInfoResponse(
        message="Study Planning Conversational Interface API",
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        endpoints={
            "files": {
                "upload": "POST /files/upload - Upload documents for RAG",
                "list": "GET /files/ - List uploaded files",
                "details": "GET /files/{filename} - Get file details",
                "delete": "DELETE /files/{filename} - Delete file",
                "extensions": "GET /files/supported/extensions - Get supported file types"
            },
            "rag": {
                "search": "POST /rag/search - Search documents using RAG",
                "query": "POST /rag/query - RAG query with LLM completion",
                "stats": "GET /rag/stats - RAG system statistics",
                "reset": "POST /rag/reset - Reset document collection",
                "health": "GET /rag/health - RAG service health check"
            },
            "llm": {
                "query": "POST /llm/query - Direct LLM query",
                "status": "GET /llm/status - LLM service status",
                "models": "GET /llm/models - List available models",
                "ensure": "POST /llm/models/{model}/ensure - Ensure model availability",
                "health": "GET /llm/health - LLM service health check"
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
    return HealthResponse(
        message="API is running",
        status="healthy"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
