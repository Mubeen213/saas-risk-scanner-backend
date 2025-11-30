import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Body, Cookie, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.dependencies import AuthServiceDep, CurrentUserDep
from app.core.settings import settings
from app.schemas.auth import (
    AuthSuccessResponse,
    AuthUrlResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.common import (
    ApiResponse,
    create_error_response,
    create_success_response,
)
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    """Set secure HTTP-only cookies for authentication tokens."""
    is_production = not settings.debug

    # Cookie settings:
    # - httponly: Prevents JavaScript access (XSS protection)
    # - secure: Only send over HTTPS (enabled in production)
    # - samesite: "lax" works with Vite proxy (same origin in dev)
    # - path: "/" ensures cookies are sent with all requests

    cookie_settings = {
        "httponly": True,
        "secure": is_production,
        "samesite": "lax",
        "path": "/",
    }

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.access_token_expire_seconds,
        **cookie_settings,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.refresh_token_expire_seconds,
        **cookie_settings,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@router.get(
    "/google",
    response_model=ApiResponse[AuthUrlResponse],
    summary="Initiate Google OAuth",
)
async def initiate_google_oauth(
    auth_service: AuthServiceDep,
    redirect_uri: str = Query(..., description="Frontend callback URL"),
) -> ApiResponse[AuthUrlResponse] | JSONResponse:
    logging.debug(f"Initiating Google OAuth with redirect_uri: {redirect_uri}")
    result = await auth_service.get_google_auth_url(redirect_uri)
    if not result.success:
        return create_error_response(
            code=result.error_code.value,
            message=result.error_message,
            target=result.error_target,
        )
    return create_success_response(result.data)


@router.get(
    "/google/callback",
    summary="Google OAuth Callback",
    description="Handles Google OAuth callback, sets secure cookies, and redirects to frontend",
)
async def google_oauth_callback(
    auth_service: AuthServiceDep,
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter for CSRF validation"),
) -> RedirectResponse:
    """
    Google redirects here after user consent. This endpoint:
    1. Exchanges the authorization code for tokens
    2. Creates/updates user in the database
    3. Generates JWT tokens
    4. Sets tokens in secure HTTP-only cookies
    5. Redirects to frontend with success/error status only (no tokens in URL)
    """
    try:
        result = await auth_service.handle_google_callback(code, state)
    except Exception as e:
        # Catch any unhandled exceptions and redirect gracefully
        logger.exception(f"Unexpected error during OAuth callback: {e}")
        frontend_callback = f"{settings.frontend_url}/auth/callback"
        error_params = urlencode(
            {
                "error": "INTERNAL_ERROR",
                "error_message": "An unexpected error occurred. Please try again.",
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")

    # Get the frontend redirect URI from the result (extracted from state)
    frontend_callback = (
        result.frontend_redirect_uri or f"{settings.frontend_url}/auth/callback"
    )

    if not result.success:
        # Redirect to frontend with error (no sensitive data)
        error_params = urlencode(
            {
                "error": (
                    result.error_code.value if result.error_code else "UNKNOWN_ERROR"
                ),
                "error_message": result.error_message or "Authentication failed",
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")

    # Success: Set tokens in secure HTTP-only cookies and redirect
    auth_data = result.data

    # Create redirect response with success indicator
    success_params = urlencode(
        {
            "success": "true",
            "is_new_user": str(auth_data.is_new_user).lower(),
        }
    )
    response = RedirectResponse(url=f"{frontend_callback}?{success_params}")

    # Set secure HTTP-only cookies (tokens never exposed in URL)
    _set_auth_cookies(response, auth_data.access_token, auth_data.refresh_token)

    return response


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Refresh Access Token",
)
async def refresh_access_token(
    response: Response,
    auth_service: AuthServiceDep,
    refresh_token_body: Annotated[
        str | None, Body(alias="refresh_token", embed=True)
    ] = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> ApiResponse[TokenResponse] | JSONResponse:
    # Use refresh token from request body or cookie
    refresh_token = refresh_token_body or refresh_token_cookie or ""

    if not refresh_token:
        return create_error_response(
            code="INVALID_TOKEN",
            message="Refresh token is required",
        )

    result = await auth_service.refresh_token(refresh_token)
    if not result.success:
        return create_error_response(
            code=result.error_code.value,
            message=result.error_message,
        )

    # Set new tokens in cookies
    _set_auth_cookies(response, result.data.access_token, result.data.refresh_token)

    return create_success_response(result.data)


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Get Current User",
)
async def get_current_user_profile(
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
) -> ApiResponse[UserResponse] | JSONResponse:
    result = await auth_service.get_current_user(current_user.id)
    if not result.success:
        return create_error_response(
            code=result.error_code.value,
            message=result.error_message,
        )
    return create_success_response(result.data)


@router.post(
    "/logout",
    response_model=ApiResponse[LogoutResponse],
    summary="Logout",
)
async def logout(
    response: Response,
    current_user: CurrentUserDep,
    auth_service: AuthServiceDep,
    request: LogoutRequest,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> ApiResponse[LogoutResponse]:
    # Use refresh token from request body or cookie
    refresh_token = request.refresh_token or refresh_token_cookie or ""
    result = await auth_service.logout(refresh_token)
    # Clear auth cookies
    _clear_auth_cookies(response)
    return create_success_response(result.data)
