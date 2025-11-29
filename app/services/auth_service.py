from dataclasses import dataclass

from app.constants.auth_errors import AUTH_ERROR_MESSAGES, AuthErrorCode
from app.constants.enums import UserStatus
from app.core.security import token_service
from app.core.settings import settings
from app.database import db_connection
from app.oauth import oauth_service
from app.oauth.types import OAuthUserInfo
from app.repositories.organization_repository import organization_repository
from app.repositories.plan_repository import plan_repository
from app.repositories.role_repository import role_repository
from app.repositories.user_repository import user_repository
from app.schemas.auth import (
    AuthSuccessResponse,
    AuthUrlResponse,
    LogoutResponse,
    TokenResponse,
)
from app.schemas.organization import OrganizationResponse
from app.schemas.plan import PlanResponse
from app.schemas.role import RoleResponse
from app.schemas.user import UserResponse
from app.services.user_authentication_service import (
    AuthResult,
    user_authentication_service,
)


@dataclass
class AuthServiceResult:
    success: bool
    data: (
        AuthSuccessResponse
        | AuthUrlResponse
        | TokenResponse
        | UserResponse
        | LogoutResponse
        | None
    ) = None
    error_code: AuthErrorCode | None = None
    error_target: str | None = None
    frontend_redirect_uri: str | None = None  # Used for OAuth callback redirect

    @property
    def error_message(self) -> str | None:
        if self.error_code:
            return AUTH_ERROR_MESSAGES.get(self.error_code)
        return None


class AuthService:

    async def get_google_auth_url(self, redirect_uri: str) -> AuthServiceResult:
        if redirect_uri not in settings.allowed_redirect_uri_list:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_REDIRECT_URI,
                error_target="redirect_uri",
            )

        async with db_connection.get_connection() as conn:
            provider_config = await oauth_service.get_provider_config(
                conn, "google-workspace"
            )
            if provider_config is None:
                return AuthServiceResult(
                    success=False,
                    error_code=AuthErrorCode.PROVIDER_NOT_FOUND,
                    error_target="provider",
                )

            provider, config = provider_config
            authorization_url = oauth_service.generate_authorization_url(
                provider, config, redirect_uri
            )

        return AuthServiceResult(
            success=True,
            data=AuthUrlResponse(authorization_url=authorization_url),
        )

    async def handle_google_callback(self, code: str, state: str) -> AuthServiceResult:
        state_data = oauth_service.validate_and_consume_state(state)
        if state_data is None:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_OAUTH_STATE,
                error_target="state",
            )

        frontend_redirect_uri = state_data.get("frontend_redirect_uri")

        async with db_connection.get_connection() as conn:
            provider_config = await oauth_service.get_provider_config(
                conn, "google-workspace"
            )
            if provider_config is None:
                return AuthServiceResult(
                    success=False,
                    error_code=AuthErrorCode.PROVIDER_NOT_FOUND,
                    error_target="provider",
                    frontend_redirect_uri=frontend_redirect_uri,
                )

            provider, config = provider_config

            token_result = await oauth_service.exchange_code_for_tokens(
                provider, config, code
            )
            if not token_result.success:
                return AuthServiceResult(
                    success=False,
                    error_code=token_result.error_code,
                    error_target="code",
                    frontend_redirect_uri=frontend_redirect_uri,
                )

            tokens = token_result.data
            user_info_result = await oauth_service.fetch_user_info(
                provider, config, tokens.id_token or tokens.access_token
            )
            if not user_info_result.success:
                return AuthServiceResult(
                    success=False,
                    error_code=user_info_result.error_code,
                    error_target="access_token",
                    frontend_redirect_uri=frontend_redirect_uri,
                )

            user_info: OAuthUserInfo = user_info_result.data
            auth_result: AuthResult = (
                await user_authentication_service.authenticate_with_oauth(
                    conn, user_info
                )
            )

            if not auth_result.success:
                return AuthServiceResult(
                    success=False,
                    error_code=auth_result.error_code,
                    frontend_redirect_uri=frontend_redirect_uri,
                )

            return AuthServiceResult(
                success=True,
                data=auth_result.data,
                frontend_redirect_uri=frontend_redirect_uri,
            )

    async def refresh_token(self, refresh_token: str) -> AuthServiceResult:
        payload = token_service.verify_refresh_token(refresh_token)
        if payload is None:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_REFRESH_TOKEN,
            )

        user_id = payload.get("user_id")
        if user_id is None:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_REFRESH_TOKEN,
            )

        async with db_connection.get_connection() as conn:
            user = await user_repository.find_by_id(conn, user_id)
            if user is None:
                return AuthServiceResult(
                    success=False, error_code=AuthErrorCode.USER_NOT_FOUND
                )

            if user.status != UserStatus.ACTIVE.value:
                return AuthServiceResult(
                    success=False, error_code=AuthErrorCode.USER_INACTIVE
                )

            organization = await organization_repository.find_by_id(
                conn, user.organization_id
            )
            if organization is None:
                return AuthServiceResult(
                    success=False, error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND
                )

            role = await role_repository.find_by_id(conn, user.role_id)
            if role is None:
                return AuthServiceResult(
                    success=False, error_code=AuthErrorCode.ROLE_NOT_FOUND
                )

        access_token = token_service.create_access_token(
            user_id=user.id,
            org_id=organization.id,
            role=role.name,
            email=user.email,
        )

        return AuthServiceResult(
            success=True,
            data=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="Bearer",
                expires_in=settings.access_token_expire_seconds,
            ),
        )

    async def get_current_user(self, user_id: int) -> AuthServiceResult:
        async with db_connection.get_connection() as conn:
            user = await user_repository.find_by_id(conn, user_id)
            if user is None:
                return AuthServiceResult(
                    success=False,
                    error_code=AuthErrorCode.USER_NOT_FOUND,
                )

            organization = await organization_repository.find_by_id(
                conn, user.organization_id
            )
            if organization is None:
                return AuthServiceResult(
                    success=False,
                    error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND,
                )

            role = await role_repository.find_by_id(conn, user.role_id)
            if role is None:
                return AuthServiceResult(
                    success=False,
                    error_code=AuthErrorCode.ROLE_NOT_FOUND,
                )

            plan = await plan_repository.find_by_id(conn, organization.plan_id)
            if plan is None:
                return AuthServiceResult(
                    success=False,
                    error_code=AuthErrorCode.PLAN_NOT_FOUND,
                )

        return AuthServiceResult(
            success=True,
            data=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                email_verified=user.email_verified,
                status=user.status,
                last_login_at=user.last_login_at,
                role=RoleResponse(
                    id=role.id,
                    name=role.name,
                    display_name=role.display_name,
                ),
                organization=OrganizationResponse(
                    id=organization.id,
                    name=organization.name,
                    slug=organization.slug,
                    domain=organization.domain,
                    logo_url=organization.logo_url,
                    status=organization.status,
                    plan=PlanResponse(
                        id=plan.id,
                        name=plan.name,
                        display_name=plan.display_name,
                        max_users=plan.max_users,
                        max_apps=plan.max_apps,
                    ),
                ),
            ),
        )

    async def logout(self, refresh_token: str) -> AuthServiceResult:
        # TODO: Invalidate refresh token in production (blacklist/whitelist)
        return AuthServiceResult(
            success=True,
            data=LogoutResponse(message="Successfully logged out"),
        )


auth_service = AuthService()
