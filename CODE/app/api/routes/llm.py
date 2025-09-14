"""LLM API routes."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.api.dependencies import get_llm_service
from app.services.llm_service import LLMService
from app.models.requests import LLMRequest
from app.models.responses import LLMResponse, BaseResponse
from app.core.exceptions import LLMException, LLMNotAvailableHTTPException

router = APIRouter(prefix="/llm", tags=["llm"])


@router.post("/query", response_model=LLMResponse)
async def llm_query(
    request: LLMRequest,
    llm_service: LLMService = Depends(get_llm_service)
):
    """Direct LLM query without RAG."""
    try:
        response = llm_service.generate_response(request.prompt, request.model)
        return LLMResponse(
            message="LLM query successful",
            response=response["response"],
            model_used=response.get("model_used")
        )
    except LLMNotAvailableHTTPException:
        raise
    except LLMException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM query failed: {str(e)}")


@router.get("/status")
async def llm_status(
    llm_service: LLMService = Depends(get_llm_service)
):
    """Get LLM service status and information."""
    try:
        service_info = llm_service.get_service_info()
        return service_info
    except Exception as e:
        return {
            "service": "Ollama",
            "is_available": False,
            "error": str(e)
        }


@router.get("/models")
async def list_models(
    llm_service: LLMService = Depends(get_llm_service)
):
    """Get list of available LLM models."""
    try:
        models = llm_service.get_available_models()
        return {
            "models": models,
            "total_models": len(models)
        }
    except LLMNotAvailableHTTPException:
        raise
    except LLMException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting models: {str(e)}")


@router.post("/models/{model_name}/ensure")
async def ensure_model(
    model_name: str,
    llm_service: LLMService = Depends(get_llm_service)
):
    """Ensure a specific model is available (pull if necessary)."""
    try:
        success = llm_service.ensure_model(model_name)
        if success:
            return BaseResponse(
                message=f"Model '{model_name}' is available"
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to ensure model '{model_name}' is available"
            )
    except LLMNotAvailableHTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ensuring model: {str(e)}")


@router.get("/health")
async def llm_health_check(
    llm_service: LLMService = Depends(get_llm_service)
):
    """Health check for LLM service."""
    is_available = llm_service.is_available()
    return {
        "service": "LLM",
        "status": "healthy" if is_available else "unavailable",
        "is_available": is_available
    }
