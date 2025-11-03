"""
JWT Authentication
One responsibility: handle JWT token authentication
"""

from fastapi import Security, HTTPException, status
from fastapi_jwt import JwtAuthorizationCredentials, JwtAccessBearer
from loguru import logger

from src.config.settings import app_settings


class JWTAuthenticator:
    """
    Simple JWT authentication handler.
    """

    def __init__(self):
        """Initialize JWT handler."""
        self.access_security = JwtAccessBearer(
            secret_key=app_settings.security.JWT_SECRET_KEY,
            auto_error=True
        )

    def get_current_user(
        self,
        credentials: JwtAuthorizationCredentials = Security(None)
    ) -> dict[str, str]:
        """
        Get current user from JWT token.

        Args:
            credentials: JWT authorization credentials

        Returns:
            dict: User information from token
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        try:
            return {
                "username": credentials.subject.get("username", "unknown"),
                "role": credentials.subject.get("role", "user")
            }
        except Exception as e:
            logger.error(f"JWT token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

jwt_authenticator = JWTAuthenticator()

def get_current_user(
    credentials: JwtAuthorizationCredentials = Security(jwt_authenticator.access_security)
) -> dict[str, str]:
    """Get current user - for use as FastAPI dependency."""
    return jwt_authenticator.get_current_user(credentials)