from typing import Any

import asyncpg

from app.database.query_builder import bind_named
from app.dtos.integration.workspace_dtos import (
    CreateWorkspaceUserDTO,
    UpdateWorkspaceUserDTO,
)
from app.dtos.workspace_dtos import (
    AuthorizationWithAppDTO,
    PaginationParamsDTO,
    UserWithAuthorizationsDTO,
    WorkspaceUserWithAppCountDTO,
)
from app.models.workspace_user import WorkspaceUser


class WorkspaceUserRepository:

    _SELECT_FIELDS = """
        id, organization_id, connection_id, provider_user_id, email,
        full_name, given_name, family_name, is_admin, is_delegated_admin,
        status, org_unit_path, avatar_url, raw_data, last_synced_at,
        created_at, updated_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_id(self, user_id: int) -> WorkspaceUser | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM identity_user
            WHERE id = :user_id
        """
        query, values = bind_named(query, {"user_id": user_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_provider_user_id(
        self, organization_id: int, provider_user_id: str
    ) -> WorkspaceUser | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM identity_user
            WHERE organization_id = :organization_id 
              AND provider_user_id = :provider_user_id
        """
        query, values = bind_named(
            query,
            {"organization_id": organization_id, "provider_user_id": provider_user_id},
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_email(
        self, organization_id: int, email: str
    ) -> WorkspaceUser | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM identity_user
            WHERE organization_id = :organization_id 
              AND LOWER(email) = LOWER(:email)
        """
        query, values = bind_named(
            query, {"organization_id": organization_id, "email": email}
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_organization(self, organization_id: int) -> list[WorkspaceUser]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM identity_user
            WHERE organization_id = :organization_id
            ORDER BY email
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_by_connection(self, connection_id: int) -> list[WorkspaceUser]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM identity_user
            WHERE connection_id = :connection_id
            ORDER BY email
        """
        query, values = bind_named(query, {"connection_id": connection_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def upsert(self, dto: CreateWorkspaceUserDTO) -> WorkspaceUser:
        import json

        query = f"""
            INSERT INTO identity_user (
                organization_id, connection_id, provider_user_id, email,
                full_name, given_name, family_name, is_admin, is_delegated_admin,
                status, org_unit_path, avatar_url, raw_data, last_synced_at
            ) VALUES (
                :organization_id, :connection_id, :provider_user_id, :email,
                :full_name, :given_name, :family_name, :is_admin, :is_delegated_admin,
                :status, :org_unit_path, :avatar_url, :raw_data, NOW()
            )
            ON CONFLICT (organization_id, provider_user_id) DO UPDATE SET
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                given_name = EXCLUDED.given_name,
                family_name = EXCLUDED.family_name,
                is_admin = EXCLUDED.is_admin,
                is_delegated_admin = EXCLUDED.is_delegated_admin,
                status = EXCLUDED.status,
                org_unit_path = EXCLUDED.org_unit_path,
                avatar_url = EXCLUDED.avatar_url,
                raw_data = EXCLUDED.raw_data,
                last_synced_at = NOW(),
                updated_at = NOW()
            RETURNING {self._SELECT_FIELDS}
        """
        params = {
            "organization_id": dto.organization_id,
            "connection_id": dto.connection_id,
            "provider_user_id": dto.provider_user_id,
            "email": dto.email,
            "full_name": dto.full_name,
            "given_name": dto.given_name,
            "family_name": dto.family_name,
            "is_admin": dto.is_admin,
            "is_delegated_admin": dto.is_delegated_admin,
            "status": dto.status,
            "org_unit_path": dto.org_unit_path,
            "avatar_url": dto.avatar_url,
            "raw_data": json.dumps(dto.raw_data),
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def bulk_upsert(self, dtos: list[CreateWorkspaceUserDTO]) -> int:
        import json

        if not dtos:
            return 0

        values_list = []
        for dto in dtos:
            values_list.append(
                (
                    dto.organization_id,
                    dto.connection_id,
                    dto.provider_user_id,
                    dto.email,
                    dto.full_name,
                    dto.given_name,
                    dto.family_name,
                    dto.is_admin,
                    dto.is_delegated_admin,
                    dto.status,
                    dto.org_unit_path,
                    dto.avatar_url,
                    json.dumps(dto.raw_data),
                )
            )

        query = """
            INSERT INTO identity_user (
                organization_id, connection_id, provider_user_id, email,
                full_name, given_name, family_name, is_admin, is_delegated_admin,
                status, org_unit_path, avatar_url, raw_data, last_synced_at
            ) 
            SELECT * FROM unnest(
                $1::bigint[], $2::bigint[], $3::varchar[], $4::varchar[],
                $5::varchar[], $6::varchar[], $7::varchar[], $8::boolean[], $9::boolean[],
                $10::varchar[], $11::varchar[], $12::text[], $13::jsonb[]
            ), NOW()
            ON CONFLICT (organization_id, provider_user_id) DO UPDATE SET
                email = EXCLUDED.email,
                full_name = EXCLUDED.full_name,
                given_name = EXCLUDED.given_name,
                family_name = EXCLUDED.family_name,
                is_admin = EXCLUDED.is_admin,
                is_delegated_admin = EXCLUDED.is_delegated_admin,
                status = EXCLUDED.status,
                org_unit_path = EXCLUDED.org_unit_path,
                avatar_url = EXCLUDED.avatar_url,
                raw_data = EXCLUDED.raw_data,
                last_synced_at = NOW(),
                updated_at = NOW()
        """

        columns = list(zip(*values_list))
        result = await self._conn.execute(query, *columns)
        count = int(result.split()[-1]) if result else 0
        return count

    def _map_to_model(self, row: asyncpg.Record | None) -> WorkspaceUser | None:
        if row is None:
            return None

        raw_data = row["raw_data"]
        if isinstance(raw_data, str):
            import json

            raw_data = json.loads(raw_data)

        return WorkspaceUser(
            id=row["id"],
            organization_id=row["organization_id"],
            connection_id=row["connection_id"],
            provider_user_id=row["provider_user_id"],
            email=row["email"],
            full_name=row["full_name"],
            given_name=row["given_name"],
            family_name=row["family_name"],
            is_admin=row["is_admin"],
            is_delegated_admin=row["is_delegated_admin"],
            status=row["status"],
            org_unit_path=row["org_unit_path"],
            avatar_url=row["avatar_url"],
            raw_data=raw_data or {},
            last_synced_at=row["last_synced_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def find_paginated_with_app_count(
        self, organization_id: int, params: PaginationParamsDTO
    ) -> tuple[list[WorkspaceUserWithAppCountDTO], int]:
        offset = (params.page - 1) * params.page_size
        search_pattern = f"%{params.search}%" if params.search else None

        if search_pattern:
            count_query = """
                SELECT COUNT(*) as total
                FROM identity_user
                WHERE organization_id = :organization_id
                  AND (email ILIKE :search OR full_name ILIKE :search)
            """
            count_query, count_values = bind_named(
                count_query,
                {"organization_id": organization_id, "search": search_pattern},
            )
        else:
            count_query = """
                SELECT COUNT(*) as total
                FROM identity_user
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
                    wu.id, wu.email, wu.full_name, wu.avatar_url,
                    wu.is_admin, wu.is_delegated_admin, wu.status,
                    COUNT(g.id) FILTER (WHERE g.status = 'active') as authorized_apps_count
                FROM identity_user wu
                LEFT JOIN app_grant g ON g.user_id = wu.id
                WHERE wu.organization_id = :organization_id
                  AND (wu.email ILIKE :search OR wu.full_name ILIKE :search)
                GROUP BY wu.id
                ORDER BY wu.email
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
                    wu.id, wu.email, wu.full_name, wu.avatar_url,
                    wu.is_admin, wu.is_delegated_admin, wu.status,
                    COUNT(g.id) FILTER (WHERE g.status = 'active') as authorized_apps_count
                FROM identity_user wu
                LEFT JOIN app_grant g ON g.user_id = wu.id
                WHERE wu.organization_id = :organization_id
                GROUP BY wu.id
                ORDER BY wu.email
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
        users = [
            WorkspaceUserWithAppCountDTO(
                id=row["id"],
                email=row["email"],
                full_name=row["full_name"],
                avatar_url=row["avatar_url"],
                is_admin=row["is_admin"],
                is_delegated_admin=row["is_delegated_admin"],
                status=row["status"],
                authorized_apps_count=row["authorized_apps_count"],
            )
            for row in rows
        ]
        return users, total

    async def count_by_organization(self, organization_id: int) -> int:
        query = """
            SELECT COUNT(*) as count
            FROM identity_user
            WHERE organization_id = :organization_id
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        row = await self._conn.fetchrow(query, *values)
        return row["count"] if row else 0


    async def find_all_active_by_connection(self, connection_id: int) -> list[WorkspaceUser]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM identity_user
            WHERE connection_id = :connection_id AND status = 'active'
        """
        query, values = bind_named(query, {"connection_id": connection_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_with_authorizations(
        self, organization_id: int, user_id: int
    ) -> UserWithAuthorizationsDTO | None:
        user_query = """
            SELECT id, email, full_name, avatar_url, is_admin, status, org_unit_path
            FROM identity_user
            WHERE id = :user_id AND organization_id = :organization_id
        """
        user_query, user_values = bind_named(
            user_query, {"user_id": user_id, "organization_id": organization_id}
        )
        user_row = await self._conn.fetchrow(user_query, *user_values)
        if not user_row:
            return None

        auth_query = """
            SELECT 
                oa.id as app_id, oa.name as app_name, oa.client_id,
                g.scopes, g.granted_at as authorized_at, g.status
            FROM app_grant g
            JOIN oauth_app oa ON oa.id = g.app_id
            WHERE g.user_id = :user_id
            ORDER BY g.granted_at DESC
        """
        auth_query, auth_values = bind_named(auth_query, {"user_id": user_id})
        auth_rows = await self._conn.fetch(auth_query, *auth_values)

        authorizations = []
        for row in auth_rows:
            authorizations.append(
                AuthorizationWithAppDTO(
                    app_id=row["app_id"],
                    app_name=row["app_name"],
                    client_id=row["client_id"],
                    scopes=row["scopes"] or [],
                    authorized_at=row["authorized_at"],
                    status=row["status"],
                )
            )

        return UserWithAuthorizationsDTO(
            id=user_row["id"],
            email=user_row["email"],
            full_name=user_row["full_name"],
            avatar_url=user_row["avatar_url"],
            is_admin=user_row["is_admin"],
            status=user_row["status"],
            org_unit_path=user_row["org_unit_path"],
            authorizations=authorizations,
        )
