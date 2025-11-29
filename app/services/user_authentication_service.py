from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

import asyncpg

from app.constants.auth_errors import AUTH_ERROR_MESSAGES, AuthErrorCode
from app.constants.enums import (
    OrganizationStatus,
    PlanName,
    RoleName,
    UserStatus,
)
from app.core.security import token_service
from app.core.settings import settings
from app.dtos.organization_dtos import CreateOrganizationDTO
from app.dtos.user_dtos import CreateUserDTO, UpdateUserDTO
from app.oauth.types import OAuthUserInfo
from app.repositories.organization_repository import organization_repository
from app.repositories.plan_repository import plan_repository
from app.repositories.role_repository import role_repository
from app.repositories.user_repository import user_repository
from app.schemas.auth import AuthSuccessResponse
from app.schemas.organization import OrganizationResponse
from app.schemas.plan import PlanResponse
from app.schemas.role import RoleResponse
from app.schemas.user import UserResponse
from app.services.domain_validator_service import domain_validator_service
from app.utils.slug_generator import generate_org_name_from_domain, generate_org_slug


@dataclass
class AuthResult:
    success: bool
    data: AuthSuccessResponse | None = None
    error_code: AuthErrorCode | None = None

    @property
    def error_message(self) -> str | None:
        if self.error_code:
            return AUTH_ERROR_MESSAGES.get(self.error_code)
        return None


class UserAuthenticationService:

    async def authenticate_with_oauth(
        self, conn: asyncpg.Connection, user_info: OAuthUserInfo
    ) -> AuthResult:
        if not domain_validator_service.is_valid_company_domain(user_info.email):
            return AuthResult(
                success=False,
                error_code=AuthErrorCode.INVALID_EMAIL_DOMAIN,
            )

        existing_user = await user_repository.find_by_provider_id(
            conn, user_info.provider_user_id
        )
        if existing_user:
            return await self._process_existing_user(conn, existing_user.id, user_info)

        invited_user = await user_repository.find_by_email(conn, user_info.email)
        if invited_user:
            return await self._process_invited_user(conn, invited_user.id, user_info)

        return await self._process_new_signup(conn, user_info)

    async def _process_existing_user(
        self, conn: asyncpg.Connection, user_id: int, user_info: OAuthUserInfo
    ) -> AuthResult:
        user = await user_repository.find_by_id(conn, user_id)
        if user is None:
            return AuthResult(success=False, error_code=AuthErrorCode.USER_NOT_FOUND)

        if user.status == UserStatus.SUSPENDED.value:
            return AuthResult(success=False, error_code=AuthErrorCode.USER_SUSPENDED)

        if user.status == UserStatus.DEACTIVATED.value:
            return AuthResult(success=False, error_code=AuthErrorCode.USER_DEACTIVATED)

        organization = await organization_repository.find_by_id(
            conn, user.organization_id
        )
        if organization is None:
            return AuthResult(
                success=False, error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND
            )

        if organization.status == OrganizationStatus.SUSPENDED.value:
            return AuthResult(
                success=False, error_code=AuthErrorCode.ORGANIZATION_SUSPENDED
            )

        update_dto = UpdateUserDTO(
            full_name=user_info.full_name,
            avatar_url=user_info.avatar_url,
            email_verified=user_info.email_verified,
            last_login_at=datetime.utcnow(),
        )
        if user.status == UserStatus.PENDING_INVITATION.value:
            update_dto.status = UserStatus.ACTIVE.value
            update_dto.joined_at = datetime.utcnow()

        updated_user = await user_repository.update(conn, user_id, update_dto)
        if updated_user is None:
            return AuthResult(success=False, error_code=AuthErrorCode.UPDATE_FAILED)

        return await self._build_auth_response(conn, updated_user.id, is_new_user=False)

    async def _process_invited_user(
        self, conn: asyncpg.Connection, user_id: int, user_info: OAuthUserInfo
    ) -> AuthResult:
        user = await user_repository.find_by_id(conn, user_id)
        if user is None:
            return AuthResult(success=False, error_code=AuthErrorCode.USER_NOT_FOUND)

        if user.status != UserStatus.PENDING_INVITATION.value:
            return AuthResult(
                success=False, error_code=AuthErrorCode.INVALID_USER_STATE
            )

        organization = await organization_repository.find_by_id(
            conn, user.organization_id
        )
        if organization is None:
            return AuthResult(
                success=False, error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND
            )

        user_domain = domain_validator_service.extract_domain(user_info.email)
        if organization.domain and organization.domain.lower() != user_domain:
            return AuthResult(success=False, error_code=AuthErrorCode.DOMAIN_MISMATCH)

        now = datetime.utcnow()
        update_dto = UpdateUserDTO(
            provider_id=user_info.provider_user_id,
            full_name=user_info.full_name,
            avatar_url=user_info.avatar_url,
            email_verified=user_info.email_verified,
            status=UserStatus.ACTIVE.value,
            joined_at=now,
            last_login_at=now,
        )

        updated_user = await user_repository.update(conn, user_id, update_dto)
        if updated_user is None:
            return AuthResult(success=False, error_code=AuthErrorCode.UPDATE_FAILED)

        return await self._build_auth_response(conn, updated_user.id, is_new_user=False)

    async def _process_new_signup(
        self, conn: asyncpg.Connection, user_info: OAuthUserInfo
    ) -> AuthResult:
        domain = domain_validator_service.extract_domain(user_info.email)

        existing_org = await organization_repository.find_by_domain(conn, domain)
        if existing_org:
            return AuthResult(
                success=False, error_code=AuthErrorCode.ORGANIZATION_EXISTS
            )

        free_plan = await plan_repository.find_by_name(conn, PlanName.FREE.value)
        if free_plan is None:
            return AuthResult(success=False, error_code=AuthErrorCode.PLAN_NOT_FOUND)

        owner_role = await role_repository.find_by_name(conn, RoleName.OWNER.value)
        if owner_role is None:
            return AuthResult(success=False, error_code=AuthErrorCode.ROLE_NOT_FOUND)

        org_slug = await self._generate_unique_slug(conn, domain)
        org_dto = CreateOrganizationDTO(
            name=generate_org_name_from_domain(domain),
            slug=org_slug,
            domain=domain,
            plan_id=free_plan.id,
            status=OrganizationStatus.ACTIVE.value,
        )
        organization = await organization_repository.create(conn, org_dto)

        now = datetime.utcnow()
        user_dto = CreateUserDTO(
            organization_id=organization.id,
            role_id=owner_role.id,
            email=user_info.email,
            full_name=user_info.full_name,
            avatar_url=user_info.avatar_url,
            provider_id=user_info.provider_user_id,
            email_verified=user_info.email_verified,
            status=UserStatus.ACTIVE.value,
            joined_at=now,
            last_login_at=now,
        )
        created_user = await user_repository.create(conn, user_dto)
        if created_user is None:
            return AuthResult(
                success=False, error_code=AuthErrorCode.USER_CREATION_FAILED
            )

        return await self._build_auth_response(conn, created_user.id, is_new_user=True)

    async def _generate_unique_slug(self, conn: asyncpg.Connection, domain: str) -> str:
        slug = generate_org_slug(domain)
        while await organization_repository.find_by_slug(conn, slug):
            slug = generate_org_slug(domain)
        return slug

    async def _build_auth_response(
        self, conn: asyncpg.Connection, user_id: int, is_new_user: bool
    ) -> AuthResult:
        user = await user_repository.find_by_id(conn, user_id)
        if user is None:
            return AuthResult(success=False, error_code=AuthErrorCode.USER_NOT_FOUND)

        organization = await organization_repository.find_by_id(
            conn, user.organization_id
        )
        if organization is None:
            return AuthResult(
                success=False, error_code=AuthErrorCode.ORGANIZATION_NOT_FOUND
            )

        role = await role_repository.find_by_id(conn, user.role_id)
        if role is None:
            return AuthResult(success=False, error_code=AuthErrorCode.ROLE_NOT_FOUND)

        plan = await plan_repository.find_by_id(conn, organization.plan_id)
        if plan is None:
            return AuthResult(success=False, error_code=AuthErrorCode.PLAN_NOT_FOUND)

        access_token = token_service.create_access_token(
            user_id=user.id,
            org_id=organization.id,
            role=role.name,
            email=user.email,
        )
        refresh_token = token_service.create_refresh_token(
            user_id=user.id, jti=str(uuid4())
        )

        response = AuthSuccessResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.access_token_expire_seconds,
            user=UserResponse(
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
            is_new_user=is_new_user,
        )
        return AuthResult(success=True, data=response)


user_authentication_service = UserAuthenticationService()
