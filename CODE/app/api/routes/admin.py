"""Admin API routes."""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional

from app.api.dependencies import get_current_admin, get_user_service_dep, get_database, get_file_service_dep, get_rag_service
from app.services.user_service import UserService
from app.services.feedback_service import FeedbackService
from app.services.file_service import FileService
from app.services.rag_service import RAGService
from app.db.models import UserInDB
from app.models.user import UserResponse, UserListResponse, UserStatisticsResponse
from app.models.responses import (
    FeedbackListResponse,
    FeedbackStatsResponse,
    FeedbackSummaryResponse,
    FeedbackItem
)
from app.core.exceptions import UserNotFoundException
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    admin: UserInDB = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service_dep)
):
    """List all users (admin only)."""
    try:
        users = await user_service.list_all_users(skip=skip, limit=limit)
        total = await user_service.get_total_user_count()

        user_responses = []
        for user in users:
            user_responses.append(UserResponse(
                id=str(user.id),
                auth0_id=user.auth0_id,
                email=user.email,
                name=user.name,
                role=user.role,
                created_at=user.created_at,
                updated_at=user.updated_at,
                statistics=UserStatisticsResponse(
                    total_uploads=user.statistics.total_uploads,
                    total_queries=user.statistics.total_queries,
                    total_storage_bytes=user.statistics.total_storage_bytes,
                    last_activity=user.statistics.last_activity
                )
            ))

        return UserListResponse(
            users=user_responses,
            total=total
        )
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing users: {str(e)}")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: str,
    admin: UserInDB = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service_dep)
):
    """Get user details by ID (admin only)."""
    try:
        user = await user_service.get_user_by_id(user_id)

        return UserResponse(
            id=str(user.id),
            auth0_id=user.auth0_id,
            email=user.email,
            name=user.name,
            role=user.role,
            created_at=user.created_at,
            updated_at=user.updated_at,
            statistics=UserStatisticsResponse(
                total_uploads=user.statistics.total_uploads,
                total_queries=user.statistics.total_queries,
                total_storage_bytes=user.statistics.total_storage_bytes,
                last_activity=user.statistics.last_activity
            )
        )
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error getting user details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting user details: {str(e)}")


@router.get("/users/{user_id}/stats", response_model=UserStatisticsResponse)
async def get_user_stats(
    user_id: str,
    admin: UserInDB = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service_dep)
):
    """Get user statistics (admin only)."""
    try:
        stats = await user_service.get_user_statistics(user_id)

        return UserStatisticsResponse(
            total_uploads=stats.total_uploads,
            total_queries=stats.total_queries,
            total_storage_bytes=stats.total_storage_bytes,
            last_activity=stats.last_activity
        )
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting user statistics: {str(e)}")


@router.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(
    admin: UserInDB = Depends(get_current_admin),
    user_service: UserService = Depends(get_user_service_dep)
):
    """Get system-wide statistics (admin only)."""
    try:
        stats = await user_service.get_system_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting system statistics: {str(e)}")


@router.get("/feedback", response_model=FeedbackListResponse)
async def get_all_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    rating: Optional[str] = Query(None, description="Filter by rating: like or dislike"),
    user_id: Optional[str] = Query(None, description="Filter by user auth0_id"),
    filename: Optional[str] = Query(None, description="Filter by file name"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    admin: UserInDB = Depends(get_current_admin),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get paginated list of all feedback (admin only).

    Supports filtering by:
    - Rating (like/dislike)
    - User (auth0_id)
    - File (filename)
    - Date range (start_date, end_date)
    """
    try:
        feedback_service = FeedbackService(database)

        # Parse dates if provided
        start_date_obj = datetime.fromisoformat(start_date) if start_date else None
        end_date_obj = datetime.fromisoformat(end_date) if end_date else None

        result = await feedback_service.get_all_feedback(
            skip=skip,
            limit=limit,
            rating_filter=rating,
            user_filter=user_id,
            file_filter=filename,
            start_date=start_date_obj,
            end_date=end_date_obj
        )

        # Convert to response model
        feedback_items = [FeedbackItem(**item) for item in result["items"]]

        return FeedbackListResponse(
            success=True,
            items=feedback_items,
            total=result["total"],
            skip=result["skip"],
            limit=result["limit"],
            page=result["page"],
            pages=result["pages"]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting feedback list: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feedback: {str(e)}")


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def get_feedback_statistics(
    admin: UserInDB = Depends(get_current_admin),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get aggregated feedback statistics (admin only)."""
    try:
        feedback_service = FeedbackService(database)
        stats = await feedback_service.get_feedback_stats()

        # Convert recent feedback to FeedbackItem objects
        recent_items = [FeedbackItem(**item) for item in stats["recent_feedback"]]

        return FeedbackStatsResponse(
            success=True,
            total_feedback=stats["total_feedback"],
            total_likes=stats["total_likes"],
            total_dislikes=stats["total_dislikes"],
            total_neutral=stats["total_neutral"],
            total_with_comments=stats["total_with_comments"],
            top_users=stats["top_users"],
            top_files=stats["top_files"],
            recent_feedback=recent_items
        )

    except Exception as e:
        logger.error(f"Error getting feedback stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feedback statistics: {str(e)}")


@router.post("/feedback/summary", response_model=FeedbackSummaryResponse)
async def generate_feedback_summary(
    rating: Optional[str] = Query(None, description="Filter by rating"),
    user_id: Optional[str] = Query(None, description="Filter by user"),
    filename: Optional[str] = Query(None, description="Filter by file"),
    start_date: Optional[str] = Query(None, description="Filter by start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (ISO format)"),
    max_items: int = Query(100, ge=1, le=500, description="Max feedback items to summarize"),
    language: Optional[str] = Query("en", description="Language for summary (en/es)"),
    admin: UserInDB = Depends(get_current_admin),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Generate LLM-based summary of feedback (admin only).

    Uses Ollama to analyze and summarize student feedback,
    providing insights on sentiment, key themes, and actionable suggestions.
    """
    try:
        feedback_service = FeedbackService(database)

        # Parse dates if provided
        start_date_obj = datetime.fromisoformat(start_date) if start_date else None
        end_date_obj = datetime.fromisoformat(end_date) if end_date else None

        summary = await feedback_service.generate_feedback_summary(
            rating_filter=rating,
            user_filter=user_id,
            file_filter=filename,
            start_date=start_date_obj,
            end_date=end_date_obj,
            max_items=max_items,
            language=language
        )

        return FeedbackSummaryResponse(
            success=True,
            summary=summary["summary"],
            item_count=summary["item_count"],
            generated_at=summary["generated_at"],
            filters_applied=summary["filters_applied"]
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating feedback summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@router.get("/feedback/file/{filename}")
async def get_feedback_by_file(
    filename: str,
    admin: UserInDB = Depends(get_current_admin),
    database: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get all feedback for a specific file (admin only)."""
    try:
        feedback_service = FeedbackService(database)
        feedback_items = await feedback_service.get_feedback_by_file(filename)

        items = [FeedbackItem(**item) for item in feedback_items]

        return {
            "success": True,
            "filename": filename,
            "feedback_count": len(items),
            "feedback": items
        }

    except Exception as e:
        logger.error(f"Error getting feedback for file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feedback: {str(e)}")


@router.post("/reindex-all-files")
async def reindex_all_files(
    admin: UserInDB = Depends(get_current_admin),
    file_service: FileService = Depends(get_file_service_dep),
    rag_service: RAGService = Depends(get_rag_service)
):
    """Reprocess all files into ChromaDB (admin only).

    This endpoint reprocesses all files from disk and re-indexes them into ChromaDB.
    Useful when ChromaDB data is lost or corrupted.
    """
    try:
        logger.info(f"Admin {admin.email} initiated full reindex")

        if not rag_service:
            raise HTTPException(status_code=500, detail="RAG service not available")

        # Get all files from MongoDB
        all_files = await file_service.list_all_files()

        results = {
            "total_files": len(all_files),
            "processed": 0,
            "failed": 0,
            "errors": []
        }

        for file_meta in all_files:
            filename = file_meta.get("filename")
            try:
                logger.info(f"Reprocessing file: {filename}")

                # Process document from GridFS (current storage method)
                owner_id = file_meta.get("user_id")

                chunk_count = await rag_service.process_document_from_gridfs(
                    filename=filename,
                    user_id=str(owner_id) if owner_id else "system",
                    is_public=file_meta.get("is_public", False)
                )

                # Update file metadata with processing status
                await file_service.update_file_processed_status(
                    filename=filename,
                    processed=True,
                    chunk_count=chunk_count
                )

                logger.info(f"✓ Reprocessed {filename}: {chunk_count} chunks")
                results["processed"] += 1

            except Exception as file_error:
                error_msg = f"{filename}: {str(file_error)}"
                logger.error(f"✗ Failed to reprocess {filename}: {file_error}")
                results["failed"] += 1
                results["errors"].append(error_msg)

        logger.info(f"Reindex complete: {results['processed']} succeeded, {results['failed']} failed")

        return {
            "success": True,
            "message": f"Reindex complete: {results['processed']}/{results['total_files']} files processed successfully",
            "results": results
        }

    except Exception as e:
        logger.error(f"Error during reindex: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")
