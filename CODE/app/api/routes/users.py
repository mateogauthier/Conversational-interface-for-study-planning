"""User profile API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, get_user_service_dep
from app.services.user_service import UserService
from app.db.models import UserInDB
from app.models.user import UserResponse, UserStatisticsResponse, UserProfileUpdate
from app.core.exceptions import UserNotFoundException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: UserInDB = Depends(get_current_user)
):
    """Get current user's profile."""
    return UserResponse(
        id=str(current_user.id),
        auth0_id=current_user.auth0_id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        statistics=UserStatisticsResponse(
            total_uploads=current_user.statistics.total_uploads,
            total_queries=current_user.statistics.total_queries,
            total_storage_bytes=current_user.statistics.total_storage_bytes,
            last_activity=current_user.statistics.last_activity
        )
    )


@router.get("/me/stats", response_model=UserStatisticsResponse)
async def get_current_user_stats(
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep)
):
    """Get current user's statistics."""
    try:
        stats = await user_service.get_user_statistics(str(current_user.id))
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
        raise HTTPException(status_code=500, detail=f"Error getting statistics: {str(e)}")


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service_dep)
):
    """Update current user's profile."""
    try:
        updated_user = await user_service.update_user_profile(
            user_id=str(current_user.id),
            name=profile_update.name,
            metadata=profile_update.metadata
        )

        return UserResponse(
            id=str(updated_user.id),
            auth0_id=updated_user.auth0_id,
            email=updated_user.email,
            name=updated_user.name,
            role=updated_user.role,
            created_at=updated_user.created_at,
            updated_at=updated_user.updated_at,
            statistics=UserStatisticsResponse(
                total_uploads=updated_user.statistics.total_uploads,
                total_queries=updated_user.statistics.total_queries,
                total_storage_bytes=updated_user.statistics.total_storage_bytes,
                last_activity=updated_user.statistics.last_activity
            )
        )
    except UserNotFoundException:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating profile: {str(e)}")
