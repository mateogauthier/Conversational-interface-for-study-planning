"""Admin API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.api.dependencies import get_current_admin, get_user_service_dep
from app.services.user_service import UserService
from app.db.models import UserInDB
from app.models.user import UserResponse, UserListResponse, UserStatisticsResponse
from app.core.exceptions import UserNotFoundException

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
