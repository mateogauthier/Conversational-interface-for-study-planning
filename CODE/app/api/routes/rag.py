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
    get_file_service_dep,
    get_routing_service,
    get_app_settings
)
from app.services.rag_service import RAGService
from app.services.llm_service import LLMService
from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.services.file_service import FileService
from app.services.routing_service import RoutingService, RoutingStrategy
from app.core.config import Settings
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
        search_results = await rag_service.search_documents_async(
            query=request.prompt,
            user=current_user,
            n_results=request.n_results
        )

        # Increment user query count
        await user_service.increment_query_count(str(current_user.id))

        # If LLM completion is requested and context is available
        if request.use_llm and search_results.get("context") and await llm_service.is_available():
            try:
                llm_response = await llm_service.generate_with_context(
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
                    context=search_results["context"],  # For compatibility with RAGResponse
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
    file_service: FileService = Depends(get_file_service_dep),
    routing_service: RoutingService = Depends(get_routing_service),
    settings: Settings = Depends(get_app_settings)
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
        if not await llm_service.is_available():
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

        # ADAPTIVE ROUTING: Classify query to determine if retrieval is needed
        routing_result = None
        chromadb_queried = True  # Default to True for backward compatibility

        if settings.enable_adaptive_routing:
            routing_result = await routing_service.classify_query(
                query=request.prompt,
                mode=settings.routing_mode,
                confidence_threshold=settings.routing_confidence_threshold
            )
            logger.info(f"Routing decision: {routing_result['strategy']} "
                       f"(confidence: {routing_result['confidence']}, "
                       f"method: {routing_result['method']})")

        # Determine if we need to query ChromaDB based on routing
        skip_retrieval = (routing_result and
                         routing_result['strategy'] == RoutingStrategy.NO_RETRIEVAL)

        if skip_retrieval:
            # Skip document retrieval for simple queries
            logger.info(f"Skipping ChromaDB retrieval: {routing_result['reasoning']}")
            chromadb_queried = False
            search_results = {
                "context": "",
                "n_chunks_found": 0,
                "relevant_chunks": []
            }
        else:
            # Search documents with user permissions
            search_results = await rag_service.search_documents_async(
                query=request.prompt,
                user=current_user,
                n_results=request.n_results
            )

        # Increment user query count
        await user_service.increment_query_count(str(current_user.id))

        # Generate answer with LLM (including conversation history)
        llm_response = await llm_service.generate_with_context(
            prompt=request.prompt,
            context=search_results["context"],
            model=request.model,
            language=request.language,
            instructions=request.instructions,
            conversation_history=conversation_history,
            enable_artifacts=request.enable_artifacts
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

        # Extract artifacts from LLM response
        artifacts = llm_response.get("artifacts", [])

        # Save assistant message to conversation with source files and artifacts
        assistant_message_id = await conversation_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=llm_response["response"],
            model_used=llm_response.get("model_used"),
            source_files=source_files,
            metadata={
                "sources": source_files,
                "n_chunks": search_results["n_chunks_found"],
                "artifacts": artifacts
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
            message_id=assistant_message_id,
            artifacts=artifacts,
            # Adaptive RAG routing metadata
            routing_strategy=routing_result['strategy'] if routing_result else None,
            routing_confidence=routing_result['confidence'] if routing_result else None,
            chromadb_queried=chromadb_queried
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
        stats = await rag_service.get_user_stats_async(current_user)
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
        success = await rag_service.reset_public_documents_async()

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
