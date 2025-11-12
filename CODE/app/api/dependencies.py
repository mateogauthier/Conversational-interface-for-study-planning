"""API dependencies and dependency injection."""

import logging
from typing import Optional
from fastapi import Depends, Header
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.file_service import FileService, get_file_service_instance
from app.services.llm_service import LLMService, llm_service
from app.services.rag_service import RAGService, rag_service
from app.services.auth_service import AuthService, get_auth_service
from app.services.user_service import UserService, get_user_service
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


async def get_file_service(
    database: AsyncIOMotorDatabase = Depends(get_database)
) -> FileService:
    """Get file service dependency with database support."""
    return get_file_service_instance(database)


def get_llm_service() -> LLMService:
    """Get LLM service dependency."""
    return llm_service


def get_rag_service() -> RAGService:
    """Get RAG service dependency."""
    return rag_service


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


async def get_current_user(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service_dep)
) -> UserInDB:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        authorization: Authorization header with Bearer token
        auth_service: Auth service instance

    Returns:
        UserInDB: Current authenticated user

    Raises:
        UnauthorizedHTTPException: If token is missing or invalid
        TokenExpiredHTTPException: If token has expired
    """
    if not authorization:
        logger.warning("Missing Authorization header")
        raise UnauthorizedHTTPException("Missing Authorization header")

    # Extract Bearer token
    parts = authorization.split()

    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization header format: {authorization[:20]}...")
        raise UnauthorizedHTTPException("Invalid Authorization header format. Expected: Bearer <token>")

    token = parts[1]

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
