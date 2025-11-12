"""Security utilities for JWT verification and Auth0 integration."""

import json
import logging
from typing import Dict, Optional
from urllib.request import urlopen

from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationException,
    TokenExpiredException,
    AuthorizationException
)

logger = logging.getLogger(__name__)


class Auth0JWKSCache:
    """Cache for Auth0 JWKS (JSON Web Key Set)."""

    def __init__(self):
        self._jwks: Optional[Dict] = None

    def get_jwks(self, domain: str) -> Dict:
        """Get JWKS from Auth0, with caching."""
        if self._jwks is None:
            jwks_url = f"https://{domain}/.well-known/jwks.json"
            try:
                with urlopen(jwks_url) as response:
                    self._jwks = json.loads(response.read())
                logger.info(f"Successfully fetched JWKS from {jwks_url}")
            except Exception as e:
                logger.error(f"Failed to fetch JWKS from {jwks_url}: {e}")
                raise AuthenticationException(f"Failed to fetch Auth0 public keys: {e}")
        return self._jwks

    def clear(self):
        """Clear JWKS cache (useful for testing or key rotation)."""
        self._jwks = None


# Global JWKS cache
jwks_cache = Auth0JWKSCache()


def get_rsa_key(token: str, jwks: Dict) -> Optional[Dict]:
    """Extract RSA key from JWKS that matches the token's kid (key ID)."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        logger.error(f"Failed to decode JWT header: {e}")
        raise AuthenticationException("Invalid token header")

    rsa_key = {}
    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            break

    if not rsa_key:
        logger.error(f"No matching RSA key found for kid: {unverified_header.get('kid')}")
        raise AuthenticationException("Unable to find appropriate key")

    return rsa_key


def verify_token(token: str) -> Dict:
    """
    Verify JWT token with Auth0.

    Args:
        token: JWT token string

    Returns:
        Dict: Decoded token payload with claims

    Raises:
        AuthenticationException: If token is invalid
        TokenExpiredException: If token is expired
    """
    settings = get_settings()

    # Check if Auth0 is configured
    if not settings.auth0_domain or not settings.auth0_api_audience:
        logger.error("Auth0 is not configured. Set AUTH0_DOMAIN and AUTH0_API_AUDIENCE environment variables.")
        raise AuthenticationException(
            "Authentication is not configured. Please set AUTH0_DOMAIN and AUTH0_API_AUDIENCE environment variables."
        )

    # Get JWKS from Auth0
    jwks = jwks_cache.get_jwks(settings.auth0_domain)

    # Get RSA key matching token's kid
    rsa_key = get_rsa_key(token, jwks)

    # Construct issuer
    issuer = settings.auth0_issuer or f"https://{settings.auth0_domain}/"

    try:
        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=settings.auth0_algorithms,
            audience=settings.auth0_api_audience,
            issuer=issuer
        )
        logger.debug(f"Successfully verified token for subject: {payload.get('sub')}")
        return payload

    except ExpiredSignatureError:
        logger.warning("Token has expired")
        raise TokenExpiredException("Token has expired")

    except JWTClaimsError as e:
        logger.error(f"JWT claims error: {e}")
        raise AuthenticationException(f"Invalid token claims: {e}")

    except JWTError as e:
        logger.error(f"JWT verification failed: {e}")
        raise AuthenticationException(f"Invalid token: {e}")

    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise AuthenticationException(f"Token verification failed: {e}")


def decode_token(token: str) -> Dict:
    """
    Decode JWT token without verification (for extracting claims only).

    WARNING: Only use this for non-security-critical operations.
    Always use verify_token() for authentication.

    Args:
        token: JWT token string

    Returns:
        Dict: Decoded token payload
    """
    try:
        return jwt.get_unverified_claims(token)
    except JWTError as e:
        logger.error(f"Failed to decode token: {e}")
        raise AuthenticationException(f"Invalid token format: {e}")


def extract_user_role(payload: Dict) -> str:
    """
    Extract user role from JWT payload.

    Auth0 can include roles in different claim formats:
    - permissions: ["role:admin"]
    - roles: ["admin"]
    - custom namespace: ["https://your-app/roles": ["admin"]]

    Args:
        payload: Decoded JWT payload

    Returns:
        str: User role (admin or student)

    Raises:
        AuthorizationException: If no valid role found
    """
    settings = get_settings()

    # Strategy 1: Check 'roles' claim (Auth0 RBAC)
    roles = payload.get("roles", [])
    if roles:
        for role in roles:
            if role in settings.allowed_roles:
                return role

    # Strategy 2: Check custom namespace (e.g., "https://your-app.com/roles")
    # You may need to adjust this based on your Auth0 configuration
    for key, value in payload.items():
        if "role" in key.lower() and isinstance(value, list):
            for role in value:
                if role in settings.allowed_roles:
                    return role

    # Strategy 3: Check permissions claim
    permissions = payload.get("permissions", [])
    for perm in permissions:
        if perm.startswith("role:"):
            role = perm.split("role:")[1]
            if role in settings.allowed_roles:
                return role

    logger.error(f"No valid role found in token payload for user {payload.get('sub')}")
    raise AuthorizationException(
        f"User does not have a valid role. Allowed roles: {settings.allowed_roles}"
    )


def check_role_permission(user_role: str, required_role: str) -> bool:
    """
    Check if user has required role permission.

    Args:
        user_role: User's role from token
        required_role: Required role for the operation

    Returns:
        bool: True if user has permission
    """
    settings = get_settings()

    # Admin has all permissions
    if user_role == settings.admin_role:
        return True

    # Exact role match
    return user_role == required_role
