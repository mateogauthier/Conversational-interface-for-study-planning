"""Authentication service for Auth0 integration and JWT handling."""

import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import verify_token, extract_user_role
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    UserNotFoundException
)
from app.db.models import UserInDB
from app.db.collections import USERS_COLLECTION

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.users_collection = database[USERS_COLLECTION]

    async def authenticate_token(self, token: str) -> dict:
        """
        Authenticate user from JWT token.

        Args:
            token: JWT Bearer token

        Returns:
            dict: Token payload with user claims

        Raises:
            AuthenticationException: If token is invalid
            TokenExpiredException: If token is expired
        """
        # Verify token with Auth0
        payload = verify_token(token)

        # Extract essential claims
        auth0_id = payload.get("sub")
        if not auth0_id:
            raise AuthenticationException("Token missing 'sub' claim (Auth0 user ID)")

        # Extract role
        try:
            role = extract_user_role(payload)
        except AuthorizationException as e:
            logger.error(f"Failed to extract role from token for user {auth0_id}: {e}")
            raise

        # Add extracted data to payload
        payload["role"] = role

        return payload

    async def get_or_create_user_from_token(self, token_payload: dict) -> UserInDB:
        """
        Get existing user or create new user from token payload.

        This method syncs user data from Auth0 to local MongoDB on first login.

        Args:
            token_payload: Decoded JWT payload from Auth0

        Returns:
            UserInDB: User document

        Raises:
            AuthenticationException: If user data is invalid
        """
        auth0_id = token_payload.get("sub")
        email = token_payload.get("email")
        name = token_payload.get("name")
        role = token_payload.get("role")

        if not auth0_id:
            raise AuthenticationException("Token missing 'sub' claim")

        # For machine-to-machine tokens (client credentials), generate a synthetic email
        if not email:
            if auth0_id.endswith("@clients"):
                # Extract client ID from subject (format: CLIENT_ID@clients)
                client_id = auth0_id.replace("@clients", "")
                email = f"{client_id}@m2m.example.com"
                name = name or f"M2M Client {client_id[:8]}"
                logger.info(f"Machine-to-machine token detected. Using synthetic email: {email}")
            else:
                raise AuthenticationException("Token missing 'email' claim")

        if not role:
            raise AuthenticationException("User role not determined")

        # Check if user exists
        existing_user = await self.users_collection.find_one({"auth0_id": auth0_id})

        if existing_user:
            # User exists, return as UserInDB
            logger.debug(f"User found: {auth0_id}")
            return UserInDB(**existing_user)

        # Create new user
        logger.info(f"Creating new user: {auth0_id} with role {role}")

        new_user = UserInDB(
            auth0_id=auth0_id,
            email=email,
            name=name,
            role=role
        )

        # Insert into MongoDB
        result = await self.users_collection.insert_one(
            new_user.model_dump(by_alias=True, exclude={"id"})
        )

        # Fetch the created user to get the MongoDB ID
        created_user = await self.users_collection.find_one({"_id": result.inserted_id})

        if not created_user:
            raise AuthenticationException("Failed to create user")

        logger.info(f"Successfully created user {auth0_id} with MongoDB ID {result.inserted_id}")

        return UserInDB(**created_user)

    async def get_user_by_auth0_id(self, auth0_id: str) -> Optional[UserInDB]:
        """
        Get user by Auth0 ID.

        Args:
            auth0_id: Auth0 user ID (sub claim)

        Returns:
            UserInDB or None if not found
        """
        user_doc = await self.users_collection.find_one({"auth0_id": auth0_id})

        if not user_doc:
            return None

        return UserInDB(**user_doc)

    def check_role(self, user: UserInDB, required_role: str) -> bool:
        """
        Check if user has required role.

        Args:
            user: User document
            required_role: Required role string

        Returns:
            bool: True if user has required role
        """
        from app.core.config import get_settings
        settings = get_settings()

        # Admins have all permissions
        if user.role == settings.admin_role:
            return True

        # Check exact role match
        return user.role == required_role


# Singleton instance will be created at app startup with database injection
_auth_service_instance: Optional[AuthService] = None


def get_auth_service(database: AsyncIOMotorDatabase) -> AuthService:
    """
    Get or create auth service instance.

    Args:
        database: MongoDB database instance

    Returns:
        AuthService instance
    """
    global _auth_service_instance

    if _auth_service_instance is None:
        _auth_service_instance = AuthService(database)

    return _auth_service_instance
