import json
from datetime import datetime

import asyncpg

from app.database.query_builder import bind_named
from app.dtos.integration.discovery_dtos import (
    CreateAppAuthorizationDTO,
    UpdateAppAuthorizationDTO,
)
from app.models.app_authorization import AppAuthorization


class AppAuthorizationRepository:

    _SELECT_FIELDS = """
        id, discovered_app_id, workspace_user_id, scopes, status,
        authorized_at, revoked_at, raw_data, created_at, updated_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_id(self, auth_id: int) -> AppAuthorization | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM app_authorization
            WHERE id = :auth_id
        """
        query, values = bind_named(query, {"auth_id": auth_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_app_and_user(
        self, discovered_app_id: int, workspace_user_id: int
    ) -> AppAuthorization | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM app_authorization
            WHERE discovered_app_id = :discovered_app_id 
              AND workspace_user_id = :workspace_user_id
        """
        query, values = bind_named(
            query,
            {
                "discovered_app_id": discovered_app_id,
                "workspace_user_id": workspace_user_id,
            },
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_app(self, discovered_app_id: int) -> list[AppAuthorization]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM app_authorization
            WHERE discovered_app_id = :discovered_app_id
            ORDER BY authorized_at DESC
        """
        query, values = bind_named(query, {"discovered_app_id": discovered_app_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_by_user(self, workspace_user_id: int) -> list[AppAuthorization]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM app_authorization
            WHERE workspace_user_id = :workspace_user_id
            ORDER BY authorized_at DESC
        """
        query, values = bind_named(query, {"workspace_user_id": workspace_user_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_active_by_user(
        self, workspace_user_id: int
    ) -> list[AppAuthorization]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM app_authorization
            WHERE workspace_user_id = :workspace_user_id AND status = 'active'
            ORDER BY authorized_at DESC
        """
        query, values = bind_named(query, {"workspace_user_id": workspace_user_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def upsert(self, dto: CreateAppAuthorizationDTO) -> AppAuthorization:
        query = f"""
            INSERT INTO app_authorization (
                discovered_app_id, workspace_user_id, scopes, status,
                authorized_at, raw_data
            ) VALUES (
                :discovered_app_id, :workspace_user_id, :scopes, :status,
                :authorized_at, :raw_data
            )
            ON CONFLICT (discovered_app_id, workspace_user_id) DO UPDATE SET
                scopes = EXCLUDED.scopes,
                status = EXCLUDED.status,
                authorized_at = GREATEST(EXCLUDED.authorized_at, app_authorization.authorized_at),
                raw_data = EXCLUDED.raw_data,
                updated_at = NOW()
            RETURNING {self._SELECT_FIELDS}
        """
        params = {
            "discovered_app_id": dto.discovered_app_id,
            "workspace_user_id": dto.workspace_user_id,
            "scopes": json.dumps(dto.scopes),
            "status": dto.status,
            "authorized_at": dto.authorized_at,
            "raw_data": json.dumps(dto.raw_data),
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def mark_revoked(
        self, auth_id: int, revoked_at: datetime | None = None
    ) -> AppAuthorization | None:
        query = f"""
            UPDATE app_authorization
            SET status = 'revoked',
                revoked_at = COALESCE(:revoked_at, NOW()),
                updated_at = NOW()
            WHERE id = :auth_id
            RETURNING {self._SELECT_FIELDS}
        """
        query, values = bind_named(
            query, {"auth_id": auth_id, "revoked_at": revoked_at}
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def count_active_by_app(self, discovered_app_id: int) -> int:
        query = """
            SELECT COUNT(*) as count
            FROM app_authorization
            WHERE discovered_app_id = $1 AND status = 'active'
        """
        row = await self._conn.fetchrow(query, discovered_app_id)
        return row["count"] if row else 0

    def _map_to_model(self, row: asyncpg.Record | None) -> AppAuthorization | None:
        if row is None:
            return None

        scopes = row["scopes"]
        if isinstance(scopes, str):
            import json

            scopes = json.loads(scopes)

        raw_data = row["raw_data"]
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)

        return AppAuthorization(
            id=row["id"],
            discovered_app_id=row["discovered_app_id"],
            workspace_user_id=row["workspace_user_id"],
            scopes=scopes or [],
            status=row["status"],
            authorized_at=row["authorized_at"],
            revoked_at=row["revoked_at"],
            raw_data=raw_data or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
