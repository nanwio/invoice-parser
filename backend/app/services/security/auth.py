# Copyright 2024 Artificial Intelligence Labs, SL

from fastapi import Security
from fastapi_jwt import JwtAuthorizationCredentials, JwtAccessBearer

from app.settings import settings

# Create a JWT Token evaluator that will be called by FastAPI
# on every request that depends on it (or, in this case, another dependency)
access_security = JwtAccessBearer(
    secret_key=settings.SECRET_KEY,
    auto_error=True
)


# Use as a dependency on every authenticated endpoint
def get_current_user(
    credentials: JwtAuthorizationCredentials = Security(access_security)
) -> dict[str, str]:
    """
    Get current user from JWT token.
    
    Args:
        credentials: JWT authorization credentials
        
    Returns:
        dict: User information from token
    """
    return credentials.subject