"""API dependencies and dependency injection."""

import logging
from typing import Optional
from fastapi import Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.file_service import FileService, get_file_service_instance
from app.services.llm_service import LLMService, llm_service
from app.services.rag_service import RAGService, get_rag_service_instance
from app.services.auth_service import AuthService, get_auth_service
from app.services.user_service import UserService, get_user_service
from app.services.conversation_service import ConversationService, get_conversation_service
from app.services.routing_service import RoutingService, routing_service
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    UnauthorizedHTTPException,
    ForbiddenHTTPException,
    TokenExpiredHTTPException,
    AuthenticationException,
    AuthorizationException,
    TokenExpiredException
)
from app.db.database import get_database
from app.db.models import UserInDB

logger = logging.getLogger(__name__)

# Security scheme for Swagger UI (auto_error=False makes it optional)
security = HTTPBearer(auto_error=False)


async def get_file_service(
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> FileService:
    """Get file service dependency with database support."""
    return get_file_service_instance(database)

# Alias for consistency with other dependencies
get_file_service_dep = get_file_service


def get_llm_service() -> LLMService:
    """Get LLM service dependency."""
    return llm_service


def get_rag_service() -> Optional[RAGService]:
    """Get RAG service dependency."""
    return get_rag_service_instance()


def get_app_settings() -> Settings:
    """Get application settings dependency."""
    return get_settings()


async def get_auth_service_dep(
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> AuthService:
    """Get auth service dependency."""
    return get_auth_service(database)


async def get_user_service_dep(
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> UserService:
    """Get user service dependency."""
    return get_user_service(database)


async def get_conversation_service_dep(
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> ConversationService:
    """Get conversation service dependency."""
    return get_conversation_service()


def get_routing_service() -> RoutingService:
    """Get routing service dependency."""
    return routing_service


async def get_current_user_from_service(
    request: Request,
    settings: Settings = Depends(get_app_settings),
    auth_service: AuthService = Depends(get_auth_service_dep)
) -> Optional[UserInDB]:
    """
    Check if request is from internal service (agent-api).

    Returns UserInDB if valid service-to-service call, None otherwise.
    """
    try:
        # Directly access headers from request object (case-insensitive)
        x_service_key = request.headers.get("x-service-key")
        x_user_auth0_id = request.headers.get("x-user-auth0-id")
        x_user_role = request.headers.get("x-user-role")

        if x_service_key and x_user_auth0_id and x_user_role:
            # Check if service key matches
            expected_key = getattr(settings, 'internal_service_key', None)
            if expected_key and x_service_key == expected_key:
                logger.debug(f"Internal service call authenticated for user: {x_user_auth0_id}")
                # Get or create user from headers
                user = await auth_service.get_user_by_auth0_id(x_user_auth0_id)
                if user:
                    return user
                # If user doesn't exist, create a minimal user object for the request
                from bson import ObjectId
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                minimal_user = UserInDB(
                    id=ObjectId(),
                    auth0_id=x_user_auth0_id,
                    email=f"{x_user_auth0_id}@internal.service",
                    role=x_user_role,
                    created_at=now,
                    last_login=now
                )
                return minimal_user
            else:
                logger.warning(f"Service key mismatch for service auth attempt")
        return None
    except Exception as e:
        logger.error(f"❌ Error in get_current_user_from_service: {e}", exc_info=True)
        return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service_dep),
    service_user: Optional[UserInDB] = Depends(get_current_user_from_service)
) -> UserInDB:
    """
    Dependency to get current authenticated user from JWT token or service headers.

    Args:
        credentials: HTTP Bearer credentials from Swagger/API
        auth_service: Auth service instance
        service_user: User from internal service call (if applicable)

    Returns:
        UserInDB: Current authenticated user

    Raises:
        UnauthorizedHTTPException: If token is missing or invalid
        TokenExpiredHTTPException: If token has expired
    """
    # If this is an internal service call, return service user
    if service_user:
        logger.debug(f"Service-to-service auth: {service_user.auth0_id}")
        return service_user

    if not credentials:
        logger.warning("Missing Authorization credentials")
        raise UnauthorizedHTTPException("Missing Authorization header")

    token = credentials.credentials

    try:
        # Authenticate token
        token_payload = await auth_service.authenticate_token(token)

        # Get or create user
        user = await auth_service.get_or_create_user_from_token(token_payload)

        logger.debug(f"Authenticated user: {user.email} ({user.role})")
        return user

    except TokenExpiredException:
        logger.warning("Token has expired")
        raise TokenExpiredHTTPException()

    except (AuthenticationException, AuthorizationException) as e:
        logger.warning(f"Authentication failed: {e}")
        raise UnauthorizedHTTPException(str(e))

    except Exception as e:
        logger.error(f"Unexpected error during authentication: {e}")
        raise UnauthorizedHTTPException("Authentication failed")


async def get_current_admin(
    current_user: UserInDB = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings)
) -> UserInDB:
    """
    Dependency to ensure current user is an admin.

    Args:
        current_user: Current authenticated user
        settings: Application settings

    Returns:
        UserInDB: Current admin user

    Raises:
        ForbiddenHTTPException: If user is not an admin
    """
    if current_user.role != settings.admin_role:
        logger.warning(f"User {current_user.email} attempted admin action with role {current_user.role}")
        raise ForbiddenHTTPException("Admin privileges required")

    return current_user


async def get_current_student(
    current_user: UserInDB = Depends(get_current_user),
    settings: Settings = Depends(get_app_settings)
) -> UserInDB:
    """
    Dependency to ensure current user is a student.

    Args:
        current_user: Current authenticated user
        settings: Application settings

    Returns:
        UserInDB: Current student user

    Raises:
        ForbiddenHTTPException: If user is not a student
    """
    if current_user.role != settings.student_role:
        logger.warning(f"User {current_user.email} attempted student-only action with role {current_user.role}")
        raise ForbiddenHTTPException("Student privileges required")

    return current_user
