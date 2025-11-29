import logging
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import token_service
from app.database import db_connection
from app.models.user import User
from app.repositories.user_repository import user_repository

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    access_token_cookie: str | None,
) -> str | None:
    """Extract JWT token from either Authorization header or cookie."""
    # Prefer Authorization header if present
    if credentials is not None:
        return credentials.credentials
    # Fall back to cookie
    if access_token_cookie:
        return access_token_cookie
    return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    access_token_cookie: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> User:
    token = _extract_token(credentials, access_token_cookie)

    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = token_service.verify_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with db_connection.get_connection() as conn:
        user = await user_repository.find_by_id(conn, payload.user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user.status not in ("active",):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )
        return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
