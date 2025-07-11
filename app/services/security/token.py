# Copyright 2024 Artificial Intelligence Labs, SL

from .auth import access_security


def create_token(data: dict[str, str], expiration_days: int = 30) -> str:
    """
    Create a new JWT token with the given data and expiration
    
    Args:
        data: Dictionary containing the claims to encode in the token
        expiration_days: Number of days after which the token is expired (default 30)
        
    Returns:
        str: The encoded JWT token
    """
    return access_security.create_access_token(
        subject=data,
        expires_delta=expiration_days,
    )