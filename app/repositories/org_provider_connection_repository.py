from typing import Any

import asyncpg

from app.database.query_builder import bind_named
from app.dtos.integration.connection_dtos import (
    CreateOrgProviderConnectionDTO,
    UpdateOrgProviderConnectionDTO,
)
from app.models.org_provider_connection import OrgProviderConnection


class OrgProviderConnectionRepository:

    _SELECT_FIELDS = """
        id, organization_id, provider_id, connected_by_user_id, status,
        access_token_encrypted, refresh_token_encrypted, token_expires_at,
        scopes_granted, admin_email, workspace_domain,
        last_sync_started_at, last_sync_completed_at, last_sync_status, last_sync_error,
        last_token_refresh_at, token_refresh_count,
        error_code, error_message,
        created_at, updated_at, deleted_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_id(self, connection_id: int) -> OrgProviderConnection | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM org_provider_connection
            WHERE id = :connection_id AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"connection_id": connection_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_org_and_provider(
        self, organization_id: int, provider_id: int
    ) -> OrgProviderConnection | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM org_provider_connection
            WHERE organization_id = :organization_id 
              AND provider_id = :provider_id 
              AND deleted_at IS NULL
        """
        query, values = bind_named(
            query, {"organization_id": organization_id, "provider_id": provider_id}
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_organization(
        self, organization_id: int
    ) -> list[OrgProviderConnection]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM org_provider_connection
            WHERE organization_id = :organization_id AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_active_connections(self) -> list[OrgProviderConnection]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM org_provider_connection
            WHERE status = 'active' AND deleted_at IS NULL
        """
        rows = await self._conn.fetch(query)
        return [self._map_to_model(row) for row in rows if row]

    async def create(
        self, dto: CreateOrgProviderConnectionDTO
    ) -> OrgProviderConnection:
        query = f"""
            INSERT INTO org_provider_connection (
                organization_id, provider_id, connected_by_user_id, status,
                access_token_encrypted, refresh_token_encrypted, token_expires_at,
                scopes_granted, admin_email, workspace_domain
            ) VALUES (
                :organization_id, :provider_id, :connected_by_user_id, :status,
                :access_token_encrypted, :refresh_token_encrypted, :token_expires_at,
                :scopes_granted, :admin_email, :workspace_domain
            )
            RETURNING {self._SELECT_FIELDS}
        """
        import json

        params = {
            "organization_id": dto.organization_id,
            "provider_id": dto.provider_id,
            "connected_by_user_id": dto.connected_by_user_id,
            "status": dto.status,
            "access_token_encrypted": dto.access_token_encrypted,
            "refresh_token_encrypted": dto.refresh_token_encrypted,
            "token_expires_at": dto.token_expires_at,
            "scopes_granted": json.dumps(dto.scopes_granted),
            "admin_email": dto.admin_email,
            "workspace_domain": dto.workspace_domain,
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def update(
        self,
        connection_id: int,
        dto: UpdateOrgProviderConnectionDTO,
    ) -> OrgProviderConnection | None:
        update_fields = self._build_update_fields(dto)
        if not update_fields:
            return await self.find_by_id(connection_id)

        params = {"connection_id": connection_id, **update_fields}
        set_clause = ", ".join(f"{k} = :{k}" for k in update_fields.keys())

        query = f"""
            UPDATE org_provider_connection
            SET {set_clause}, updated_at = NOW()
            WHERE id = :connection_id AND deleted_at IS NULL
            RETURNING {self._SELECT_FIELDS}
        """
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def update_sync_status(
        self,
        connection_id: int,
        status: str,
        error: str | None = None,
    ) -> None:
        query = """
            UPDATE org_provider_connection
            SET last_sync_status = $1,
                last_sync_error = $2,
                last_sync_completed_at = NOW(),
                updated_at = NOW()
            WHERE id = $3
        """
        await self._conn.execute(query, status, error, connection_id)

    async def mark_sync_started(self, connection_id: int) -> None:
        query = """
            UPDATE org_provider_connection
            SET last_sync_started_at = NOW(),
                last_sync_status = 'in_progress',
                updated_at = NOW()
            WHERE id = $1
        """
        await self._conn.execute(query, connection_id)

    async def soft_delete(self, connection_id: int) -> bool:
        query = """
            UPDATE org_provider_connection
            SET deleted_at = NOW(), updated_at = NOW()
            WHERE id = $1 AND deleted_at IS NULL
        """
        result = await self._conn.execute(query, connection_id)
        return result == "UPDATE 1"

    def _build_update_fields(
        self, dto: UpdateOrgProviderConnectionDTO
    ) -> dict[str, Any]:
        import json

        fields: dict[str, Any] = {}
        if dto.status is not None:
            fields["status"] = dto.status
        if dto.access_token_encrypted is not None:
            fields["access_token_encrypted"] = dto.access_token_encrypted
        if dto.refresh_token_encrypted is not None:
            fields["refresh_token_encrypted"] = dto.refresh_token_encrypted
        if dto.token_expires_at is not None:
            fields["token_expires_at"] = dto.token_expires_at
        if dto.scopes_granted is not None:
            fields["scopes_granted"] = json.dumps(dto.scopes_granted)
        if dto.last_sync_started_at is not None:
            fields["last_sync_started_at"] = dto.last_sync_started_at
        if dto.last_sync_completed_at is not None:
            fields["last_sync_completed_at"] = dto.last_sync_completed_at
        if dto.last_sync_status is not None:
            fields["last_sync_status"] = dto.last_sync_status
        if dto.last_sync_error is not None:
            fields["last_sync_error"] = dto.last_sync_error
        if dto.last_token_refresh_at is not None:
            fields["last_token_refresh_at"] = dto.last_token_refresh_at
        if dto.token_refresh_count is not None:
            fields["token_refresh_count"] = dto.token_refresh_count
        if dto.error_code is not None:
            fields["error_code"] = dto.error_code
        if dto.error_message is not None:
            fields["error_message"] = dto.error_message
        return fields

    def _map_to_model(self, row: asyncpg.Record | None) -> OrgProviderConnection | None:
        if row is None:
            return None

        scopes = row["scopes_granted"]
        if isinstance(scopes, str):
            import json

            scopes = json.loads(scopes)

        return OrgProviderConnection(
            id=row["id"],
            organization_id=row["organization_id"],
            provider_id=row["provider_id"],
            connected_by_user_id=row["connected_by_user_id"],
            status=row["status"],
            access_token_encrypted=row["access_token_encrypted"],
            refresh_token_encrypted=row["refresh_token_encrypted"],
            token_expires_at=row["token_expires_at"],
            scopes_granted=scopes or [],
            admin_email=row["admin_email"],
            workspace_domain=row["workspace_domain"],
            last_sync_started_at=row["last_sync_started_at"],
            last_sync_completed_at=row["last_sync_completed_at"],
            last_sync_status=row["last_sync_status"],
            last_sync_error=row["last_sync_error"],
            last_token_refresh_at=row["last_token_refresh_at"],
            token_refresh_count=row["token_refresh_count"],
            error_code=row["error_code"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )
