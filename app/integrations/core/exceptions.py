from app.core.exceptions import AppException


class IntegrationException(AppException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(code, message, status_code)


class ProviderNotFoundError(IntegrationException):
    def __init__(self, provider_slug: str):
        super().__init__(
            code="PROVIDER_NOT_FOUND",
            message=f"Provider '{provider_slug}' not found or not supported",
            status_code=404,
        )


class ConnectionNotFoundError(IntegrationException):
    def __init__(self, connection_id: int):
        super().__init__(
            code="CONNECTION_NOT_FOUND",
            message=f"Connection with id {connection_id} not found",
            status_code=404,
        )


class TokenExpiredError(IntegrationException):
    def __init__(self, connection_id: int):
        super().__init__(
            code="TOKEN_EXPIRED",
            message=f"Access token for connection {connection_id} has expired and refresh failed",
            status_code=401,
        )


class TokenRefreshError(IntegrationException):
    def __init__(self, message: str):
        super().__init__(
            code="TOKEN_REFRESH_FAILED",
            message=message,
            status_code=401,
        )


class InsufficientScopesError(IntegrationException):
    def __init__(self, missing_scopes: list[str]):
        super().__init__(
            code="INSUFFICIENT_SCOPES",
            message=f"Missing required scopes: {', '.join(missing_scopes)}",
            status_code=403,
        )


class RateLimitExceededError(IntegrationException):
    def __init__(self, retry_after: int | None = None):
        message = "API rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
        )


class ApiRequestError(IntegrationException):
    def __init__(self, status_code: int, message: str):
        super().__init__(
            code="API_REQUEST_FAILED",
            message=message,
            status_code=status_code,
        )


class SyncError(IntegrationException):
    def __init__(self, step: str, message: str):
        super().__init__(
            code="SYNC_FAILED",
            message=f"Sync failed at step '{step}': {message}",
            status_code=500,
        )


class ConnectionAlreadyExistsError(IntegrationException):
    def __init__(self, organization_id: int, provider_slug: str):
        super().__init__(
            code="CONNECTION_ALREADY_EXISTS",
            message=f"Organization {organization_id} already has a connection to {provider_slug}",
            status_code=409,
        )


class ConfigurationError(IntegrationException):
    def __init__(self, message: str):
        super().__init__(
            code="CONFIGURATION_ERROR",
            message=message,
            status_code=500,
        )
