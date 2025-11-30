from datetime import datetime
from typing import Any

import asyncpg

from app.database.query_builder import bind_named
from app.dtos.integration.discovery_dtos import (
    CreateDiscoveredAppDTO,
    UpdateDiscoveredAppDTO,
)
from app.dtos.workspace_dtos import (
    AppWithAuthorizationsDTO,
    AuthorizationWithUserDTO,
    DiscoveredAppWithUserCountDTO,
    PaginationParamsDTO,
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

    async def find_paginated_with_user_count(
        self, organization_id: int, params: PaginationParamsDTO
    ) -> tuple[list[DiscoveredAppWithUserCountDTO], int]:
        offset = (params.page - 1) * params.page_size
        search_pattern = f"%{params.search}%" if params.search else None

        if search_pattern:
            count_query = """
                SELECT COUNT(*) as total
                FROM discovered_app
                WHERE organization_id = :organization_id
                  AND (display_name ILIKE :search OR client_id ILIKE :search)
            """
            count_query, count_values = bind_named(
                count_query,
                {"organization_id": organization_id, "search": search_pattern},
            )
        else:
            count_query = """
                SELECT COUNT(*) as total
                FROM discovered_app
                WHERE organization_id = :organization_id
            """
            count_query, count_values = bind_named(
                count_query,
                {"organization_id": organization_id},
            )
        count_row = await self._conn.fetchrow(count_query, *count_values)
        total = count_row["total"] if count_row else 0

        if search_pattern:
            query = """
                SELECT 
                    da.id, da.display_name, da.client_id, da.client_type,
                    da.status, da.first_seen_at, da.last_seen_at, da.all_scopes,
                    COUNT(aa.id) FILTER (WHERE aa.status = 'active') as authorized_users_count
                FROM discovered_app da
                LEFT JOIN app_authorization aa ON aa.discovered_app_id = da.id
                WHERE da.organization_id = :organization_id
                  AND (da.display_name ILIKE :search OR da.client_id ILIKE :search)
                GROUP BY da.id
                ORDER BY da.last_seen_at DESC
                LIMIT :page_size OFFSET :offset
            """
            query, values = bind_named(
                query,
                {
                    "organization_id": organization_id,
                    "search": search_pattern,
                    "page_size": params.page_size,
                    "offset": offset,
                },
            )
        else:
            query = """
                SELECT 
                    da.id, da.display_name, da.client_id, da.client_type,
                    da.status, da.first_seen_at, da.last_seen_at, da.all_scopes,
                    COUNT(aa.id) FILTER (WHERE aa.status = 'active') as authorized_users_count
                FROM discovered_app da
                LEFT JOIN app_authorization aa ON aa.discovered_app_id = da.id
                WHERE da.organization_id = :organization_id
                GROUP BY da.id
                ORDER BY da.last_seen_at DESC
                LIMIT :page_size OFFSET :offset
            """
            query, values = bind_named(
                query,
                {
                    "organization_id": organization_id,
                    "page_size": params.page_size,
                    "offset": offset,
                },
            )
        rows = await self._conn.fetch(query, *values)

        apps = []
        for row in rows:
            all_scopes = row["all_scopes"]
            if isinstance(all_scopes, str):
                import json

                all_scopes = json.loads(all_scopes)
            apps.append(
                DiscoveredAppWithUserCountDTO(
                    id=row["id"],
                    display_name=row["display_name"],
                    client_id=row["client_id"],
                    client_type=row["client_type"],
                    status=row["status"],
                    first_seen_at=row["first_seen_at"],
                    last_seen_at=row["last_seen_at"],
                    scopes_count=len(all_scopes) if all_scopes else 0,
                    authorized_users_count=row["authorized_users_count"],
                )
            )
        return apps, total

    async def count_by_organization(self, organization_id: int) -> int:
        query = """
            SELECT COUNT(*) as count
            FROM discovered_app
            WHERE organization_id = :organization_id
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        row = await self._conn.fetchrow(query, *values)
        return row["count"] if row else 0

    async def find_with_authorizations(
        self, organization_id: int, app_id: int
    ) -> AppWithAuthorizationsDTO | None:
        app_query = """
            SELECT id, display_name, client_id, client_type, status, 
                   all_scopes, first_seen_at, last_seen_at
            FROM discovered_app
            WHERE id = :app_id AND organization_id = :organization_id
        """
        app_query, app_values = bind_named(
            app_query, {"app_id": app_id, "organization_id": organization_id}
        )
        app_row = await self._conn.fetchrow(app_query, *app_values)
        if not app_row:
            return None

        all_scopes = app_row["all_scopes"]
        if isinstance(all_scopes, str):
            import json

            all_scopes = json.loads(all_scopes)

        auth_query = """
            SELECT 
                wu.id as user_id, wu.email, wu.full_name, wu.avatar_url,
                aa.scopes, aa.authorized_at, aa.status
            FROM app_authorization aa
            JOIN workspace_user wu ON wu.id = aa.workspace_user_id
            WHERE aa.discovered_app_id = :app_id
            ORDER BY aa.authorized_at DESC
        """
        auth_query, auth_values = bind_named(auth_query, {"app_id": app_id})
        auth_rows = await self._conn.fetch(auth_query, *auth_values)

        authorizations = []
        for row in auth_rows:
            scopes = row["scopes"]
            if isinstance(scopes, str):
                import json

                scopes = json.loads(scopes)
            authorizations.append(
                AuthorizationWithUserDTO(
                    user_id=row["user_id"],
                    email=row["email"],
                    full_name=row["full_name"],
                    avatar_url=row["avatar_url"],
                    scopes=scopes or [],
                    authorized_at=row["authorized_at"],
                    status=row["status"],
                )
            )

        return AppWithAuthorizationsDTO(
            id=app_row["id"],
            display_name=app_row["display_name"],
            client_id=app_row["client_id"],
            client_type=app_row["client_type"],
            status=app_row["status"],
            all_scopes=all_scopes or [],
            first_seen_at=app_row["first_seen_at"],
            last_seen_at=app_row["last_seen_at"],
            authorizations=authorizations,
        )
