"""RAG API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_rag_service, get_llm_service
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.models.requests import RAGRequest, RAGLLMRequest
from app.models.responses import (
    RAGResponse, 
    RAGLLMResponse, 
    RAGStatsResponse,
    BaseResponse
)
from app.core.exceptions import (
    RAGException, 
    LLMException, 
    LLMNotAvailableHTTPException
)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RAGResponse)
async def rag_search(
    request: RAGRequest,
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Query documents using RAG (Retrieval-Augmented Generation)."""
    try:
        # Search documents
        search_results = rag_service.search_documents(request.prompt, request.n_results)
        
        # If LLM completion is requested and context is available
        if request.use_llm and search_results.get("context") and llm_service.is_available():
            try:
                llm_response = llm_service.generate_with_context(
                    request.prompt, 
                    search_results["context"],
                    model=request.model,
                    language=request.language,
                    instructions=request.instructions
                )
                
                return RAGLLMResponse(
                    message="RAG search with LLM completion successful",
                    query=request.prompt,
                    answer=llm_response["response"],
                    context_used=search_results["context"],
                    n_chunks_found=search_results["n_chunks_found"],
                    sources=list(set([chunk.metadata.get('file_name', 'Unknown') 
                                    for chunk in search_results["relevant_chunks"]])),
                    relevant_chunks=search_results["relevant_chunks"],
                    model_used=llm_response.get("model_used")
                )
            except (LLMException, LLMNotAvailableHTTPException):
                # Fall back to RAG-only response if LLM fails
                pass
        
        # Return RAG-only response
        return RAGResponse(
            message="RAG search successful",
            query=search_results["query"],
            context=search_results["context"],
            n_chunks_found=search_results["n_chunks_found"],
            relevant_chunks=search_results["relevant_chunks"]
        )
        
    except RAGException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG search failed: {str(e)}")


@router.post("/query", response_model=RAGLLMResponse)
async def rag_llm_query(
    request: RAGLLMRequest,
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service)
):
    """Query documents using RAG with LLM completion."""
    try:
        # Search documents
        search_results = rag_service.search_documents(request.prompt, request.n_results)
        
        if not search_results.get("context") or search_results.get("n_chunks_found", 0) == 0:
            return RAGLLMResponse(
                message="No relevant context found",
                query=request.prompt,
                answer="I couldn't find relevant information in the uploaded documents to answer your question.",
                context_used="",
                n_chunks_found=0,
                sources=[],
                relevant_chunks=[]
            )
        
        # Generate LLM response with context
        llm_response = llm_service.generate_with_context(
            request.prompt, 
            search_results["context"],
            model=request.model,
            language=request.language,
            instructions=request.instructions
        )
        
        sources = list(set([chunk.metadata.get('file_name', 'Unknown') 
                          for chunk in search_results["relevant_chunks"]]))
        
        return RAGLLMResponse(
            message="RAG query with LLM completion successful",
            query=request.prompt,
            answer=llm_response["response"],
            context_used=search_results["context"],
            n_chunks_found=search_results["n_chunks_found"],
            sources=sources,
            relevant_chunks=search_results["relevant_chunks"],
            model_used=llm_response.get("model_used")
        )
        
    except LLMNotAvailableHTTPException:
        raise
    except (RAGException, LLMException) as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@router.get("/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    rag_service: RAGService = Depends(get_rag_service)
):
    """Get RAG system statistics."""
    try:
        stats = rag_service.get_collection_stats()
        return stats
    except RAGException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting RAG stats: {str(e)}")


@router.post("/reset", response_model=BaseResponse)
async def reset_rag_collection(
    rag_service: RAGService = Depends(get_rag_service)
):
    """Reset the RAG collection (delete all documents)."""
    try:
        success = rag_service.reset_collection()
        if success:
            return BaseResponse(
                message="RAG collection reset successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to reset RAG collection")
    except RAGException as e:
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting RAG collection: {str(e)}")


@router.get("/health")
async def rag_health_check(
    rag_service: RAGService = Depends(get_rag_service)
):
    """Health check for RAG service."""
    is_available = rag_service.is_available()
    return {
        "service": "RAG",
        "status": "healthy" if is_available else "unavailable",
        "is_available": is_available
    }
