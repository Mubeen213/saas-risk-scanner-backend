import logging
from collections.abc import AsyncGenerator
from typing import Annotated

import asyncpg
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import token_service
from app.core.settings import settings
from app.database import db_connection
from app.integrations.core.credentials import CredentialsManager
from app.models.user import User
from app.oauth.service import OAuthService
from app.repositories.app_authorization_repository import AppAuthorizationRepository
from app.repositories.discovered_app_repository import DiscoveredAppRepository
from app.repositories.org_provider_connection_repository import (
    OrgProviderConnectionRepository,
)
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.product_auth_config_repository import ProductAuthConfigRepository
from app.repositories.provider_repository import ProviderRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_group_repository import WorkspaceGroupRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository
from app.services.auth_service import AuthService
from app.services.domain_validator_service import DomainValidatorService
from app.services.integration_service import IntegrationService
from app.services.user_authentication_service import UserAuthenticationService
from app.services.workspace_sync_service import WorkspaceSyncService

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[asyncpg.Connection, None]:
    async with db_connection.get_connection() as conn:
        yield conn


def get_provider_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> ProviderRepository:
    return ProviderRepository(conn)


def get_product_auth_config_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> ProductAuthConfigRepository:
    return ProductAuthConfigRepository(conn)


def get_org_provider_connection_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> OrgProviderConnectionRepository:
    return OrgProviderConnectionRepository(conn)


def get_workspace_user_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> WorkspaceUserRepository:
    return WorkspaceUserRepository(conn)


def get_workspace_group_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> WorkspaceGroupRepository:
    return WorkspaceGroupRepository(conn)


def get_discovered_app_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> DiscoveredAppRepository:
    return DiscoveredAppRepository(conn)


def get_app_authorization_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> AppAuthorizationRepository:
    return AppAuthorizationRepository(conn)


def get_user_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> UserRepository:
    return UserRepository(conn)


def get_organization_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> OrganizationRepository:
    return OrganizationRepository(conn)


def get_plan_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> PlanRepository:
    return PlanRepository(conn)


def get_role_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> RoleRepository:
    return RoleRepository(conn)


def get_credentials_manager(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> CredentialsManager:
    return CredentialsManager(conn, settings.encryption_key)


def get_integration_service(
    provider_repository: ProviderRepository = Depends(get_provider_repository),
    product_auth_config_repository: ProductAuthConfigRepository = Depends(
        get_product_auth_config_repository
    ),
    connection_repository: OrgProviderConnectionRepository = Depends(
        get_org_provider_connection_repository
    ),
) -> IntegrationService:
    return IntegrationService(
        provider_repository=provider_repository,
        product_auth_config_repository=product_auth_config_repository,
        connection_repository=connection_repository,
        encryption_key=settings.encryption_key,
    )


def get_workspace_sync_service(
    connection_repository: OrgProviderConnectionRepository = Depends(
        get_org_provider_connection_repository
    ),
    provider_repository: ProviderRepository = Depends(get_provider_repository),
    auth_config_repository: ProductAuthConfigRepository = Depends(
        get_product_auth_config_repository
    ),
    workspace_user_repository: WorkspaceUserRepository = Depends(
        get_workspace_user_repository
    ),
    workspace_group_repository: WorkspaceGroupRepository = Depends(
        get_workspace_group_repository
    ),
    discovered_app_repository: DiscoveredAppRepository = Depends(
        get_discovered_app_repository
    ),
    app_authorization_repository: AppAuthorizationRepository = Depends(
        get_app_authorization_repository
    ),
    credentials_manager: CredentialsManager = Depends(get_credentials_manager),
) -> WorkspaceSyncService:
    return WorkspaceSyncService(
        connection_repository=connection_repository,
        provider_repository=provider_repository,
        auth_config_repository=auth_config_repository,
        workspace_user_repository=workspace_user_repository,
        workspace_group_repository=workspace_group_repository,
        discovered_app_repository=discovered_app_repository,
        app_authorization_repository=app_authorization_repository,
        credentials_manager=credentials_manager,
    )


def get_domain_validator_service() -> DomainValidatorService:
    return DomainValidatorService()


def get_oauth_service(
    provider_repository: ProviderRepository = Depends(get_provider_repository),
    product_auth_config_repository: ProductAuthConfigRepository = Depends(
        get_product_auth_config_repository
    ),
) -> OAuthService:
    return OAuthService(
        provider_repository=provider_repository,
        product_auth_config_repository=product_auth_config_repository,
    )


def get_user_authentication_service(
    user_repository: UserRepository = Depends(get_user_repository),
    organization_repository: OrganizationRepository = Depends(
        get_organization_repository
    ),
    plan_repository: PlanRepository = Depends(get_plan_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    domain_validator_service: DomainValidatorService = Depends(
        get_domain_validator_service
    ),
) -> UserAuthenticationService:
    return UserAuthenticationService(
        user_repository=user_repository,
        organization_repository=organization_repository,
        plan_repository=plan_repository,
        role_repository=role_repository,
        domain_validator_service=domain_validator_service,
    )


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    organization_repository: OrganizationRepository = Depends(
        get_organization_repository
    ),
    plan_repository: PlanRepository = Depends(get_plan_repository),
    role_repository: RoleRepository = Depends(get_role_repository),
    oauth_service: OAuthService = Depends(get_oauth_service),
    user_authentication_service: UserAuthenticationService = Depends(
        get_user_authentication_service
    ),
) -> AuthService:
    return AuthService(
        user_repository=user_repository,
        organization_repository=organization_repository,
        plan_repository=plan_repository,
        role_repository=role_repository,
        oauth_service=oauth_service,
        user_authentication_service=user_authentication_service,
    )


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    access_token_cookie: str | None,
) -> str | None:
    if credentials is not None:
        return credentials.credentials
    if access_token_cookie:
        return access_token_cookie
    return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    user_repository: UserRepository = Depends(get_user_repository),
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

    user = await user_repository.find_by_id(payload.user_id)
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
IntegrationServiceDep = Annotated[IntegrationService, Depends(get_integration_service)]
WorkspaceSyncServiceDep = Annotated[
    WorkspaceSyncService, Depends(get_workspace_sync_service)
]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
