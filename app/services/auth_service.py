import logging
from dataclasses import dataclass

from app.constants.auth_errors import AUTH_ERROR_MESSAGES, AuthErrorCode
from app.constants.enums import UserStatus
from app.core.security import token_service
from app.core.settings import settings
from app.oauth.service import OAuthService
from app.oauth.types import OAuthUserInfo
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
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
    UserAuthenticationService,
)

logger = logging.getLogger(__name__)


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
    frontend_redirect_uri: str | None = None

    @property
    def error_message(self) -> str | None:
        if self.error_code:
            return AUTH_ERROR_MESSAGES.get(self.error_code)
        return None


class AuthService:

    def __init__(
        self,
        user_repository: UserRepository,
        organization_repository: OrganizationRepository,
        plan_repository: PlanRepository,
        role_repository: RoleRepository,
        oauth_service: OAuthService,
        user_authentication_service: UserAuthenticationService,
    ):
        self._user_repository = user_repository
        self._organization_repository = organization_repository
        self._plan_repository = plan_repository
        self._role_repository = role_repository
        self._oauth_service = oauth_service
        self._user_authentication_service = user_authentication_service

    async def get_google_auth_url(self, redirect_uri: str) -> AuthServiceResult:
        if redirect_uri not in settings.allowed_redirect_uri_list:
            logger.warning("Invalid redirect URI: %s", redirect_uri)
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_REDIRECT_URI,
                error_target="redirect_uri",
            )

        provider_config = await self._oauth_service.get_provider_config(
            "google-workspace"
        )
        if provider_config is None:
            logger.warning("Provider config not found for google-workspace")
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.PROVIDER_NOT_FOUND,
                error_target="provider",
            )

        provider, config = provider_config
        authorization_url = self._oauth_service.generate_authorization_url(
            provider, config, redirect_uri
        )

        logger.info("Generated authorization URL for google-workspace")
        return AuthServiceResult(
            success=True,
            data=AuthUrlResponse(authorization_url=authorization_url),
        )

    async def handle_google_callback(self, code: str, state: str) -> AuthServiceResult:
        state_data = self._oauth_service.validate_and_consume_state(state)
        if state_data is None:
            logger.warning("Invalid OAuth state received")
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_OAUTH_STATE,
                error_target="state",
            )

        frontend_redirect_uri = state_data.get("frontend_redirect_uri")

        provider_config = await self._oauth_service.get_provider_config(
            "google-workspace"
        )
        if provider_config is None:
            logger.warning("Provider config not found during callback")
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.PROVIDER_NOT_FOUND,
                error_target="provider",
                frontend_redirect_uri=frontend_redirect_uri,
            )

        provider, config = provider_config

        token_result = await self._oauth_service.exchange_code_for_tokens(
            provider, config, code
        )
        if not token_result.success:
            logger.warning("Token exchange failed: %s", token_result.error_code)
            return AuthServiceResult(
                success=False,
                error_code=token_result.error_code,
                error_target="code",
                frontend_redirect_uri=frontend_redirect_uri,
            )

        tokens = token_result.data
        user_info_result = await self._oauth_service.fetch_user_info(
            provider, config, tokens.id_token or tokens.access_token
        )
        if not user_info_result.success:
            logger.warning("User info fetch failed: %s", user_info_result.error_code)
            return AuthServiceResult(
                success=False,
                error_code=user_info_result.error_code,
                error_target="access_token",
                frontend_redirect_uri=frontend_redirect_uri,
            )

        user_info: OAuthUserInfo = user_info_result.data
        auth_result: AuthResult = (
            await self._user_authentication_service.authenticate_with_oauth(user_info)
        )

        if not auth_result.success:
            logger.warning("Authentication failed: %s", auth_result.error_code)
            return AuthServiceResult(
                success=False,
                error_code=auth_result.error_code,
                frontend_redirect_uri=frontend_redirect_uri,
            )

        logger.info("User authenticated successfully: %s", user_info.email)
        return AuthServiceResult(
            success=True,
            data=auth_result.data,
            frontend_redirect_uri=frontend_redirect_uri,
        )

    async def refresh_token(self, refresh_token: str) -> AuthServiceResult:
        payload = token_service.verify_refresh_token(refresh_token)
        if payload is None:
            logger.warning("Invalid refresh token received")
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_REFRESH_TOKEN,
            )

        user_id = payload.user_id
        if user_id is None:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.INVALID_REFRESH_TOKEN,
            )

        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            logger.warning("User not found during token refresh: %s", user_id)
            return AuthServiceResult(
                success=False, error_code=AuthErrorCode.USER_NOT_FOUND
            )

        if user.status != UserStatus.ACTIVE.value:
            logger.warning("Inactive user attempted token refresh: %s", user.email)
            return AuthServiceResult(
                success=False, error_code=AuthErrorCode.USER_INACTIVE
            )

        organization = await self._organization_repository.find_by_id(
            user.organization_id
        )
        if organization is None:
            return AuthServiceResult(
                success=False, error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND
            )

        role = await self._role_repository.find_by_id(user.role_id)
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

        logger.info("Token refreshed successfully for user: %s", user.email)
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
        user = await self._user_repository.find_by_id(user_id)
        if user is None:
            logger.warning("User not found: %s", user_id)
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.USER_NOT_FOUND,
            )

        organization = await self._organization_repository.find_by_id(
            user.organization_id
        )
        if organization is None:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND,
            )

        role = await self._role_repository.find_by_id(user.role_id)
        if role is None:
            return AuthServiceResult(
                success=False,
                error_code=AuthErrorCode.ROLE_NOT_FOUND,
            )

        plan = await self._plan_repository.find_by_id(organization.plan_id)
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
        logger.info("User logout requested")
        return AuthServiceResult(
            success=True,
            data=LogoutResponse(message="Successfully logged out"),
        )
