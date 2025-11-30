import base64
import json
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from app.core.dependencies import (
    CurrentUserDep,
    IntegrationServiceDep,
    WorkspaceSyncServiceDep,
)
from app.core.settings import settings
from app.integrations.core.exceptions import (
    ConnectionAlreadyExistsError,
    ConnectionNotFoundError,
    IntegrationException,
    ProviderNotFoundError,
)
from app.schemas.common import (
    ApiResponse,
    create_error_response,
    create_success_response,
)
from app.schemas.integration import (
    ConnectionListResponse,
    ConnectionResponse,
    DisconnectResponse,
    IntegrationConnectRequest,
    IntegrationConnectResponse,
    SyncRequest,
    SyncResponse,
)
from app.utils.crypto import generate_oauth_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _encode_oauth_state(
    nonce: str,
    user_id: int,
    organization_id: int,
    email: str,
    provider_slug: str,
) -> str:
    state_data = {
        "nonce": nonce,
        "user_id": user_id,
        "organization_id": organization_id,
        "email": email,
        "provider_slug": provider_slug,
    }
    return base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()


def _decode_oauth_state(state: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(state.encode()).decode())
    except Exception:
        return {}


@router.post("/connect", response_model=ApiResponse)
async def initiate_connection(
    request: IntegrationConnectRequest,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
):
    logger.info(
        "Initiating connection for provider: %s, user: %d",
        request.provider_slug,
        current_user.id,
    )
    nonce = generate_oauth_state()

    state = _encode_oauth_state(
        nonce=nonce,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        email=current_user.email,
        provider_slug=request.provider_slug,
    )

    redirect_uri = f"{settings.backend_url}/api/v1/integrations/callback"

    try:
        authorization_url = await service.get_connect_url(
            request.provider_slug,
            state,
            redirect_uri,
        )

        logger.debug(
            f"Authorization URL generated for provider: {request.provider_slug}"
        )
        response_data = IntegrationConnectResponse(
            authorization_url=authorization_url,
            state=state,
        )
        return create_success_response(data=response_data.model_dump())

    except ProviderNotFoundError as e:
        logger.warning("Provider not found: %s", request.provider_slug)
        return create_error_response(
            code=e.code,
            message=e.message,
            status_code=e.status_code,
        )


@router.get(
    "/callback",
    summary="OAuth Callback",
    description="Handles OAuth callback for workspace integration, exchanges code for tokens, and redirects to frontend",
)
async def oauth_callback(
    service: IntegrationServiceDep,
    code: str = Query(..., description="Authorization code from provider"),
    state: str = Query(..., description="State parameter containing user context"),
) -> RedirectResponse:
    logger.info("Received OAuth callback")
    frontend_callback = f"{settings.frontend_url}/integrations/callback"

    state_data = _decode_oauth_state(state)
    if not state_data:
        logger.warning("Invalid OAuth state received")
        error_params = urlencode(
            {
                "error": "INVALID_STATE",
                "error_message": "Invalid OAuth state. Please try again.",
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")

    user_id = state_data.get("user_id")
    organization_id = state_data.get("organization_id")
    email = state_data.get("email")
    provider_slug = state_data.get("provider_slug")

    if not all([user_id, organization_id, email, provider_slug]):
        logger.warning("Missing user context in OAuth state")
        error_params = urlencode(
            {
                "error": "INVALID_STATE",
                "error_message": "Missing user context in state. Please try again.",
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")

    redirect_uri = f"{settings.backend_url}/api/v1/integrations/callback"

    try:
        connection = await service.handle_oauth_callback(
            provider_slug,
            code,
            organization_id,
            user_id,
            email,
            redirect_uri,
        )

        logger.info(
            "OAuth callback successful for connection: %d, org: %d",
            connection.id,
            organization_id,
        )
        success_params = urlencode(
            {
                "success": "true",
                "connection_id": str(connection.id),
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{success_params}")

    except ConnectionAlreadyExistsError as e:
        logger.warning(
            "Connection already exists for org: %d, provider: %s",
            organization_id,
            provider_slug,
        )
        error_params = urlencode(
            {
                "error": e.code,
                "error_message": e.message,
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")

    except ProviderNotFoundError as e:
        logger.warning("Provider not found: %s", provider_slug)
        error_params = urlencode(
            {
                "error": e.code,
                "error_message": e.message,
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")

    except Exception as e:
        logger.exception("Unexpected error during OAuth callback: %s", e)
        error_params = urlencode(
            {
                "error": "INTERNAL_ERROR",
                "error_message": "An unexpected error occurred. Please try again.",
            }
        )
        return RedirectResponse(url=f"{frontend_callback}?{error_params}")


@router.get("/connections", response_model=ApiResponse)
async def list_connections(
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
):
    logger.debug("Listing connections for org: %d", current_user.organization_id)
    connections = await service.get_organization_connections(
        current_user.organization_id
    )

    connection_list = [
        ConnectionResponse(
            id=c.id,
            organization_id=c.organization_id,
            provider_id=c.provider_id,
            status=c.status,
            admin_email=c.admin_email,
            workspace_domain=c.workspace_domain,
            scopes_granted=c.scopes_granted,
            last_sync_completed_at=c.last_sync_completed_at,
            last_sync_status=c.last_sync_status,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in connections
    ]

    return create_success_response(
        data=ConnectionListResponse(connections=connection_list).model_dump()
    )


@router.get("/connections/{connection_id}", response_model=ApiResponse)
async def get_connection_by_id(
    connection_id: int,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
):
    logger.debug(
        "Fetching connection: %d for org: %d",
        connection_id,
        current_user.organization_id,
    )
    try:
        connection = await service.find_connection_by_id(connection_id)

        if connection.organization_id != current_user.organization_id:
            logger.warning(
                "Access denied to connection: %d for user: %d",
                connection_id,
                current_user.id,
            )
            return create_error_response(
                code="FORBIDDEN",
                message="Access denied to this connection",
                status_code=403,
            )

        response_data = ConnectionResponse(
            id=connection.id,
            organization_id=connection.organization_id,
            provider_id=connection.provider_id,
            status=connection.status,
            admin_email=connection.admin_email,
            workspace_domain=connection.workspace_domain,
            scopes_granted=connection.scopes_granted,
            last_sync_completed_at=connection.last_sync_completed_at,
            last_sync_status=connection.last_sync_status,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )
        return create_success_response(data=response_data.model_dump())

    except ConnectionNotFoundError as e:
        logger.warning("Connection not found: %d", connection_id)
        return create_error_response(
            code=e.code,
            message=e.message,
            status_code=e.status_code,
        )


@router.post("/sync", response_model=ApiResponse)
async def trigger_sync(
    request: SyncRequest,
    current_user: CurrentUserDep,
    integration_service: IntegrationServiceDep,
    sync_service: WorkspaceSyncServiceDep,
):
    logger.info(
        "Triggering sync for connection: %d, user: %d",
        request.connection_id,
        current_user.id,
    )
    try:
        connection = await integration_service.find_connection_by_id(
            request.connection_id
        )

        if connection.organization_id != current_user.organization_id:
            logger.warning(
                "Access denied to sync connection: %d for user: %d",
                request.connection_id,
                current_user.id,
            )
            return create_error_response(
                code="FORBIDDEN",
                message="Access denied to this connection",
                status_code=403,
            )

        sync_status = await sync_service.sync_workspace(request.connection_id)

        logger.info(
            f"Sync completed for connection:{request.connection_id} with status: {sync_status.value}"
        )
        response_data = SyncResponse(
            connection_id=request.connection_id,
            status=sync_status.value,
            message="Sync completed successfully",
        )
        return create_success_response(data=response_data.model_dump())

    except ConnectionNotFoundError as e:
        logger.warning("Connection not found for sync: %d", request.connection_id)
        return create_error_response(
            code=e.code,
            message=e.message,
            status_code=e.status_code,
        )
    except IntegrationException as e:
        logger.error(
            "Integration error during sync for connection: %d - %s",
            request.connection_id,
            e.message,
        )
        return create_error_response(
            code=e.code,
            message=e.message,
            status_code=e.status_code,
        )


@router.delete("/connections/{connection_id}", response_model=ApiResponse)
async def disconnect(
    connection_id: int,
    current_user: CurrentUserDep,
    service: IntegrationServiceDep,
):
    logger.info(
        "Disconnecting connection: %d, user: %d", connection_id, current_user.id
    )
    try:
        connection = await service.find_connection_by_id(connection_id)

        if connection.organization_id != current_user.organization_id:
            logger.warning(
                "Access denied to disconnect connection: %d for user: %d",
                connection_id,
                current_user.id,
            )
            return create_error_response(
                code="FORBIDDEN",
                message="Access denied to this connection",
                status_code=403,
            )

        success = await service.disconnect(connection_id)

        logger.info("Connection %d disconnected: %s", connection_id, success)
        response_data = DisconnectResponse(
            success=success,
            message=(
                "Connection disconnected successfully"
                if success
                else "Failed to disconnect"
            ),
        )
        return create_success_response(data=response_data.model_dump())

    except ConnectionNotFoundError as e:
        logger.warning("Connection not found for disconnect: %d", connection_id)
        return create_error_response(
            code=e.code,
            message=e.message,
            status_code=e.status_code,
        )
