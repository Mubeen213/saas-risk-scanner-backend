import logging
from datetime import datetime, timedelta, timezone

import asyncpg
from cryptography.fernet import Fernet

from app.integrations.core.exceptions import (
    ConnectionNotFoundError,
    TokenExpiredError,
    TokenRefreshError,
)
from app.integrations.core.interfaces import ICredentialsManager, IWorkspaceProvider
from app.integrations.core.types import AuthContext

logger = logging.getLogger(__name__)


class CredentialsManager(ICredentialsManager):
    TOKEN_EXPIRY_BUFFER_SECONDS = 300

    def __init__(self, conn: asyncpg.Connection, encryption_key: str):
        self._conn = conn
        self._fernet = Fernet(encryption_key.encode())
        self._provider: IWorkspaceProvider | None = None

    def set_provider(self, provider: IWorkspaceProvider) -> None:
        self._provider = provider

    async def get_valid_credentials(
        self,
        connection_id: int,
        client_id: str,
        client_secret: str,
    ) -> AuthContext:
        connection = await self._load_connection(connection_id)

        if connection is None:
            raise ConnectionNotFoundError(connection_id)

        access_token = self._decrypt(connection["access_token_encrypted"])
        token_expires_at = connection["token_expires_at"]

        if self._is_token_expired(token_expires_at):
            refresh_token = connection["refresh_token_encrypted"]
            if not refresh_token:
                raise TokenExpiredError(connection_id)

            decrypted_refresh = self._decrypt(refresh_token)
            access_token = await self._refresh_token(
                connection_id, decrypted_refresh, client_id, client_secret
            )

        return AuthContext(
            access_token=access_token,
            expires_at=token_expires_at,
        )

    async def store_credentials(
        self,
        connection_id: int,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None,
    ) -> None:
        encrypted_access = self._encrypt(access_token)
        encrypted_refresh = self._encrypt(refresh_token) if refresh_token else None

        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        query = """
            UPDATE org_provider_connection
            SET access_token_encrypted = $1,
                refresh_token_encrypted = COALESCE($2, refresh_token_encrypted),
                token_expires_at = $3,
                last_token_refresh_at = NOW(),
                token_refresh_count = token_refresh_count + 1,
                updated_at = NOW()
            WHERE id = $4
        """
        await self._conn.execute(
            query, encrypted_access, encrypted_refresh, expires_at, connection_id
        )

    async def handle_token_error(self, connection_id: int, error_code: str) -> bool:
        if error_code == "401":
            await self._mark_connection_error(
                connection_id, "TOKEN_EXPIRED", "Access token expired"
            )
            return False
        elif error_code == "403":
            await self._mark_connection_error(
                connection_id, "INSUFFICIENT_SCOPES", "Insufficient permissions"
            )
            return False
        return True

    def _encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def _decrypt(self, encrypted_value: str) -> str:
        return self._fernet.decrypt(encrypted_value.encode()).decode()

    def _is_token_expired(self, expires_at: datetime | None) -> bool:
        if expires_at is None:
            return False
        buffer = timedelta(seconds=self.TOKEN_EXPIRY_BUFFER_SECONDS)
        return datetime.now(timezone.utc) >= (expires_at - buffer)

    async def _load_connection(self, connection_id: int) -> asyncpg.Record | None:
        query = """
            SELECT access_token_encrypted, refresh_token_encrypted, token_expires_at
            FROM org_provider_connection
            WHERE id = $1 AND deleted_at IS NULL
        """
        return await self._conn.fetchrow(query, connection_id)

    async def _refresh_token(
        self,
        connection_id: int,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> str:
        if self._provider is None:
            raise TokenRefreshError("Provider not set for token refresh")

        try:
            token_response = await self._provider.refresh_access_token(
                refresh_token, client_id, client_secret
            )
            await self.store_credentials(
                connection_id,
                token_response.access_token,
                token_response.refresh_token,
                token_response.expires_in,
            )
            logger.info("Successfully refreshed token for connection %d", connection_id)
            return token_response.access_token
        except Exception as e:
            logger.error("Token refresh failed for connection %d: %s", connection_id, e)
            await self._mark_connection_error(
                connection_id, "TOKEN_REFRESH_FAILED", str(e)
            )
            raise TokenRefreshError(str(e)) from e

    async def _mark_connection_error(
        self,
        connection_id: int,
        error_code: str,
        error_message: str,
    ) -> None:
        query = """
            UPDATE org_provider_connection
            SET status = 'error',
                error_code = $1,
                error_message = $2,
                updated_at = NOW()
            WHERE id = $3
        """
        await self._conn.execute(query, error_code, error_message, connection_id)
