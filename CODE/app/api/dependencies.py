"""API dependencies and dependency injection."""

import logging
from typing import Optional
from fastapi import Depends, Header
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

# Security scheme for Swagger UI
security = HTTPBearer()


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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service_dep)
) -> UserInDB:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer credentials from Swagger/API
        auth_service: Auth service instance

    Returns:
        UserInDB: Current authenticated user

    Raises:
        UnauthorizedHTTPException: If token is missing or invalid
        TokenExpiredHTTPException: If token has expired
    """
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
