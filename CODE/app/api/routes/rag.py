"""RAG API routes with authentication."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import (
    get_rag_service,
    get_llm_service,
    get_current_user,
    get_current_admin,
    get_user_service_dep,
    get_conversation_service_dep,
    get_file_service_dep
)
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.services.file_service import FileService
from app.db.models import UserInDB
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/search", response_model=RAGResponse)
async def rag_search(
    request: RAGRequest,
    current_user: UserInDB = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service),
    user_service: UserService = Depends(get_user_service_dep)
):
    """
    Query documents using RAG with user-based filtering.

    - Students: Search their private files + all public files
    - Admins: Search only public files
    """
    try:
        # Search documents with user permissions
        search_results = rag_service.search_documents(
            query=request.prompt,
            user=current_user,
            n_results=request.n_results
        )

        # Increment user query count
        await user_service.increment_query_count(str(current_user.id))

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
            except (LLMException, LLMNotAvailableHTTPException) as e:
                logger.warning(f"LLM failed, falling back to RAG-only: {e}")
                # Fall back to RAG-only response if LLM fails

        # Return RAG-only response
        return RAGResponse(
            message="RAG search successful",
            query=search_results["query"],
            context=search_results["context"],
            n_chunks_found=search_results["n_chunks_found"],
            relevant_chunks=search_results["relevant_chunks"]
        )

    except RAGException as e:
        logger.error(f"RAG search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG search failed: {str(e.message)}")
    except Exception as e:
        logger.error(f"RAG search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG search failed: {str(e)}")


@router.post("/query", response_model=RAGLLMResponse)
async def rag_query(
    request: RAGLLMRequest,
    current_user: UserInDB = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service),
    llm_service: LLMService = Depends(get_llm_service),
    user_service: UserService = Depends(get_user_service_dep),
    conversation_service: ConversationService = Depends(get_conversation_service_dep),
    file_service: FileService = Depends(get_file_service_dep)
):
    """
    Query documents and get LLM-generated answer with user-based filtering and conversation support.

    - Students: Query their private files + all public files
    - Admins: Query only public files
    - Automatically creates conversations and maintains history
    - Tracks file usage for each conversation
    """
    try:
        # Check if LLM is available
        if not llm_service.is_available():
            raise LLMNotAvailableHTTPException("LLM service is not available")

        # Handle conversation flow
        conversation_id = request.conversation_id
        conversation_history = []

        if conversation_id:
            # Load existing conversation history
            conversation_history = await conversation_service.get_conversation_history(
                conversation_id=conversation_id
            )
        else:
            # Auto-create new conversation
            conversation_id = await conversation_service.create_conversation(
                user_id=str(current_user.id),
                auth0_id=current_user.auth0_id,
                first_message=request.prompt
            )

        # Save user message to conversation
        user_message_id = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.prompt
        )

        # Search documents with user permissions
        search_results = rag_service.search_documents(
            query=request.prompt,
            user=current_user,
            n_results=request.n_results
        )

        # Increment user query count
        await user_service.increment_query_count(str(current_user.id))

        # Generate answer with LLM (including conversation history)
        llm_response = llm_service.generate_with_context(
            prompt=request.prompt,
            context=search_results["context"],
            model=request.model,
            language=request.language,
            instructions=request.instructions,
            conversation_history=conversation_history
        )

        # Extract unique source files
        source_files = list(set([chunk.metadata.get('file_name', 'Unknown')
                               for chunk in search_results["relevant_chunks"]]))

        # Track file usage (once per file per conversation)
        # Get files already used in this conversation
        files_already_used = await conversation_service.get_files_used_in_conversation(conversation_id)

        # Track usage only for new files (not previously used in this conversation)
        for filename in source_files:
            if filename != 'Unknown' and filename not in files_already_used:
                await file_service.track_file_usage(filename)

        # Save assistant message to conversation with source files
        assistant_message_id = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=llm_response["response"],
            model_used=llm_response.get("model_used"),
            source_files=source_files,
            metadata={
                "sources": source_files,
                "n_chunks": search_results["n_chunks_found"]
            }
        )

        return RAGLLMResponse(
            message="RAG query successful",
            query=request.prompt,
            answer=llm_response["response"],
            context_used=search_results["context"],
            n_chunks_found=search_results["n_chunks_found"],
            sources=list(set([chunk.metadata.get('file_name', 'Unknown')
                            for chunk in search_results["relevant_chunks"]])),
            relevant_chunks=search_results["relevant_chunks"],
            model_used=llm_response.get("model_used"),
            conversation_id=conversation_id,
            message_id=assistant_message_id
        )

    except (LLMException, LLMNotAvailableHTTPException):
        raise
    except RAGException as e:
        logger.error(f"RAG query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e.message)}")
    except Exception as e:
        logger.error(f"RAG query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")


@router.get("/stats", response_model=RAGStatsResponse)
async def get_stats(
    current_user: UserInDB = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Get RAG statistics based on user permissions.

    - Students: Stats for their files + public files
    - Admins: Stats for public files only
    """
    try:
        stats = rag_service.get_user_stats(current_user)
        return stats
    except RAGException as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e.message)}")
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/reset", response_model=BaseResponse)
async def reset_collection(
    admin: UserInDB = Depends(get_current_admin),
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Reset public documents only (admin only).

    This deletes all public RAG data but preserves student private files.
    """
    try:
        success = rag_service.reset_public_documents()

        if success:
            return BaseResponse(
                message="Public RAG collection reset successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to reset collection")

    except RAGException as e:
        logger.error(f"Failed to reset collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset collection: {str(e.message)}")
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset collection: {str(e)}")


@router.get("/health")
async def health_check(
    current_user: UserInDB = Depends(get_current_user),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Check if RAG service is available (authenticated users only)."""
    is_available = rag_service.is_available()

    if is_available:
        return {
            "status": "healthy",
            "message": "RAG service is available"
        }
    else:
        raise HTTPException(
            status_code=503,
            detail="RAG service is not available"
        )
