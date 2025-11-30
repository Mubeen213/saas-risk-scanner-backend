from datetime import datetime
from typing import Any

import asyncpg

from app.database.query_builder import bind_named
from app.dtos.integration.discovery_dtos import (
    CreateDiscoveredAppDTO,
    UpdateDiscoveredAppDTO,
)
from app.models.discovered_app import DiscoveredApp


class DiscoveredAppRepository:

    _SELECT_FIELDS = """
        id, organization_id, connection_id, client_id, display_name,
        product_id, client_type, status, first_seen_at, last_seen_at,
        all_scopes, raw_data, created_at, updated_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_id(self, app_id: int) -> DiscoveredApp | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM discovered_app
            WHERE id = :app_id
        """
        query, values = bind_named(query, {"app_id": app_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_client_id(
        self, organization_id: int, client_id: str
    ) -> DiscoveredApp | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM discovered_app
            WHERE organization_id = :organization_id 
              AND client_id = :client_id
        """
        query, values = bind_named(
            query, {"organization_id": organization_id, "client_id": client_id}
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_organization(self, organization_id: int) -> list[DiscoveredApp]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM discovered_app
            WHERE organization_id = :organization_id
            ORDER BY last_seen_at DESC
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_by_connection(self, connection_id: int) -> list[DiscoveredApp]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM discovered_app
            WHERE connection_id = :connection_id
            ORDER BY last_seen_at DESC
        """
        query, values = bind_named(query, {"connection_id": connection_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def upsert(self, dto: CreateDiscoveredAppDTO) -> DiscoveredApp:
        import json

        query = f"""
            INSERT INTO discovered_app (
                organization_id, connection_id, client_id, display_name,
                product_id, client_type, status, first_seen_at, last_seen_at,
                all_scopes, raw_data
            ) VALUES (
                :organization_id, :connection_id, :client_id, :display_name,
                :product_id, :client_type, :status, :first_seen_at, :last_seen_at,
                :all_scopes, :raw_data
            )
            ON CONFLICT (organization_id, client_id) DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, discovered_app.display_name),
                client_type = COALESCE(EXCLUDED.client_type, discovered_app.client_type),
                last_seen_at = GREATEST(EXCLUDED.last_seen_at, discovered_app.last_seen_at),
                all_scopes = (
                    SELECT jsonb_agg(DISTINCT value)
                    FROM (
                        SELECT jsonb_array_elements_text(discovered_app.all_scopes) AS value
                        UNION
                        SELECT jsonb_array_elements_text(EXCLUDED.all_scopes) AS value
                    ) combined
                ),
                updated_at = NOW()
            RETURNING {self._SELECT_FIELDS}
        """
        params = {
            "organization_id": dto.organization_id,
            "connection_id": dto.connection_id,
            "client_id": dto.client_id,
            "display_name": dto.display_name,
            "product_id": dto.product_id,
            "client_type": dto.client_type,
            "status": dto.status,
            "first_seen_at": dto.first_seen_at,
            "last_seen_at": dto.last_seen_at,
            "all_scopes": json.dumps(dto.all_scopes),
            "raw_data": json.dumps(dto.raw_data),
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def update_status(self, app_id: int, status: str) -> None:
        query = """
            UPDATE discovered_app
            SET status = $1, updated_at = NOW()
            WHERE id = $2
        """
        await self._conn.execute(query, status, app_id)

    def _map_to_model(self, row: asyncpg.Record | None) -> DiscoveredApp | None:
        if row is None:
            return None

        all_scopes = row["all_scopes"]
        if isinstance(all_scopes, str):
            import json

            all_scopes = json.loads(all_scopes)

        raw_data = row["raw_data"]
        if isinstance(raw_data, str):
            import json

            raw_data = json.loads(raw_data)

        return DiscoveredApp(
            id=row["id"],
            organization_id=row["organization_id"],
            connection_id=row["connection_id"],
            client_id=row["client_id"],
            display_name=row["display_name"],
            product_id=row["product_id"],
            client_type=row["client_type"],
            status=row["status"],
            first_seen_at=row["first_seen_at"],
            last_seen_at=row["last_seen_at"],
            all_scopes=all_scopes or [],
            raw_data=raw_data or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
