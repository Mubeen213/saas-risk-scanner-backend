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
from app.repositories.app_grant_repo import AppGrantRepository
from app.repositories.crawl_history_repo import CrawlHistoryRepository
from app.repositories.identity_provider_connection_repository import (
    IdentityProviderConnectionRepository,
)
from app.repositories.identity_provider_repository import IdentityProviderRepository
from app.repositories.oauth_app_repo import OAuthAppRepository
from app.repositories.oauth_event_repo import OAuthEventRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.product_auth_config_repository import ProductAuthConfigRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_group_repository import WorkspaceGroupRepository
from app.repositories.workspace_user_repository import WorkspaceUserRepository
from app.services.auth_service import AuthService
from app.services.domain_validator_service import DomainValidatorService
from app.services.integration_service import IntegrationService
from app.services.snapshot_service import SnapshotService
from app.services.stream_service import StreamService
from app.services.sync_manager import SyncManager
from app.services.user_authentication_service import UserAuthenticationService
from app.services.workspace_data_service import WorkspaceDataService
from app.services.directory_service import DirectoryService

logger = logging.getLogger(__name__)

http_bearer = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncGenerator[asyncpg.Connection, None]:
    async with db_connection.get_connection() as conn:
        yield conn


def get_identity_provider_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> IdentityProviderRepository:
    return IdentityProviderRepository(conn)


def get_product_auth_config_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> ProductAuthConfigRepository:
    return ProductAuthConfigRepository(conn)


def get_identity_provider_connection_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> IdentityProviderConnectionRepository:
    return IdentityProviderConnectionRepository(conn)


def get_workspace_user_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> WorkspaceUserRepository:
    return WorkspaceUserRepository(conn)


def get_workspace_group_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> WorkspaceGroupRepository:
    return WorkspaceGroupRepository(conn)


def get_oauth_app_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> OAuthAppRepository:
    return OAuthAppRepository(conn)


def get_app_grant_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> AppGrantRepository:
    return AppGrantRepository(conn)


def get_oauth_event_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> OAuthEventRepository:
    return OAuthEventRepository(conn)


def get_crawl_history_repository(
    conn: asyncpg.Connection = Depends(get_db_session),
) -> CrawlHistoryRepository:
    return CrawlHistoryRepository(conn)


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
    connection_repository: IdentityProviderConnectionRepository = Depends(
        get_identity_provider_connection_repository
    ),
) -> CredentialsManager:
    return CredentialsManager(connection_repository, settings.encryption_key)


def get_integration_service(
    identity_provider_repository: IdentityProviderRepository = Depends(
        get_identity_provider_repository
    ),
    product_auth_config_repository: ProductAuthConfigRepository = Depends(
        get_product_auth_config_repository
    ),
    connection_repository: IdentityProviderConnectionRepository = Depends(
        get_identity_provider_connection_repository
    ),
) -> IntegrationService:
    return IntegrationService(
        identity_provider_repository=identity_provider_repository,
        product_auth_config_repository=product_auth_config_repository,
        connection_repository=connection_repository,
        encryption_key=settings.encryption_key,
    )



def get_directory_service(
    user_repository: WorkspaceUserRepository = Depends(get_workspace_user_repository),
    group_repository: WorkspaceGroupRepository = Depends(get_workspace_group_repository),
) -> DirectoryService:
    return DirectoryService(user_repository, group_repository)


def get_snapshot_service(
    user_repository: WorkspaceUserRepository = Depends(get_workspace_user_repository),
    app_repo: OAuthAppRepository = Depends(get_oauth_app_repository),
    grant_repo: AppGrantRepository = Depends(get_app_grant_repository),
) -> SnapshotService:
    return SnapshotService(user_repository, app_repo, grant_repo)


def get_stream_service(
    user_repository: WorkspaceUserRepository = Depends(get_workspace_user_repository),
    app_repo: OAuthAppRepository = Depends(get_oauth_app_repository),
    grant_repo: AppGrantRepository = Depends(get_app_grant_repository),
    event_repo: OAuthEventRepository = Depends(get_oauth_event_repository),
) -> StreamService:
    return StreamService(user_repository, app_repo, grant_repo, event_repo)


def get_sync_manager(
    connection_repo: IdentityProviderConnectionRepository = Depends(
        get_identity_provider_connection_repository
    ),
    identity_provider_repo: IdentityProviderRepository = Depends(
        get_identity_provider_repository
    ),
    auth_config_repo: ProductAuthConfigRepository = Depends(
        get_product_auth_config_repository
    ),
    crawl_repo: CrawlHistoryRepository = Depends(get_crawl_history_repository),
    credentials_manager: CredentialsManager = Depends(get_credentials_manager),
    directory_service: DirectoryService = Depends(get_directory_service),
    snapshot_service: SnapshotService = Depends(get_snapshot_service),
    stream_service: StreamService = Depends(get_stream_service),
) -> SyncManager:
    return SyncManager(
        connection_repo,
        identity_provider_repo,
        auth_config_repo,
        crawl_repo,
        credentials_manager,
        directory_service,
        snapshot_service,
        stream_service,
    )


def get_domain_validator_service() -> DomainValidatorService:
    return DomainValidatorService()


def get_oauth_service(
    identity_provider_repository: IdentityProviderRepository = Depends(
        get_identity_provider_repository
    ),
    product_auth_config_repository: ProductAuthConfigRepository = Depends(
        get_product_auth_config_repository
    ),
) -> OAuthService:
    return OAuthService(
        identity_provider_repository=identity_provider_repository,
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
SyncManagerDep = Annotated[SyncManager, Depends(get_sync_manager)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_workspace_data_service(
    connection_repository: IdentityProviderConnectionRepository = Depends(
        get_identity_provider_connection_repository
    ),
    workspace_user_repository: WorkspaceUserRepository = Depends(
        get_workspace_user_repository
    ),
    workspace_group_repository: WorkspaceGroupRepository = Depends(
        get_workspace_group_repository
    ),
    oauth_app_repo: OAuthAppRepository = Depends(get_oauth_app_repository),
    app_grant_repo: AppGrantRepository = Depends(get_app_grant_repository),
    oauth_event_repo: OAuthEventRepository = Depends(get_oauth_event_repository),
    crawl_history_repo: CrawlHistoryRepository = Depends(get_crawl_history_repository),
) -> WorkspaceDataService:
    return WorkspaceDataService(
        connection_repository=connection_repository,
        workspace_user_repository=workspace_user_repository,
        workspace_group_repository=workspace_group_repository,
        oauth_app_repo=oauth_app_repo,
        app_grant_repo=app_grant_repo,
        oauth_event_repo=oauth_event_repo,
        crawl_history_repo=crawl_history_repo,
    )


WorkspaceDataServiceDep = Annotated[
    WorkspaceDataService, Depends(get_workspace_data_service)
]
