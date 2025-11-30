from typing import Any

import asyncpg

from app.database.query_builder import bind_named
from app.dtos.integration.workspace_dtos import (
    CreateGroupMembershipDTO,
    CreateWorkspaceGroupDTO,
    UpdateWorkspaceGroupDTO,
)
from app.dtos.workspace_dtos import (
    GroupMemberWithUserDTO,
    GroupWithMembersDTO,
    PaginationParamsDTO,
    WorkspaceGroupWithMemberCountDTO,
)
from app.models.group_membership import GroupMembership
from app.models.workspace_group import WorkspaceGroup


class WorkspaceGroupRepository:

    _SELECT_FIELDS = """
        id, organization_id, connection_id, provider_group_id, email,
        name, description, direct_members_count, raw_data, last_synced_at,
        created_at, updated_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_id(self, group_id: int) -> WorkspaceGroup | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM workspace_group
            WHERE id = :group_id
        """
        query, values = bind_named(query, {"group_id": group_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_provider_group_id(
        self, organization_id: int, provider_group_id: str
    ) -> WorkspaceGroup | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM workspace_group
            WHERE organization_id = :organization_id 
              AND provider_group_id = :provider_group_id
        """
        query, values = bind_named(
            query,
            {
                "organization_id": organization_id,
                "provider_group_id": provider_group_id,
            },
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_organization(self, organization_id: int) -> list[WorkspaceGroup]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM workspace_group
            WHERE organization_id = :organization_id
            ORDER BY name
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def find_by_connection(self, connection_id: int) -> list[WorkspaceGroup]:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM workspace_group
            WHERE connection_id = :connection_id
            ORDER BY name
        """
        query, values = bind_named(query, {"connection_id": connection_id})
        rows = await self._conn.fetch(query, *values)
        return [self._map_to_model(row) for row in rows if row]

    async def upsert(self, dto: CreateWorkspaceGroupDTO) -> WorkspaceGroup:
        import json

        query = f"""
            INSERT INTO workspace_group (
                organization_id, connection_id, provider_group_id, email,
                name, description, direct_members_count, raw_data, last_synced_at
            ) VALUES (
                :organization_id, :connection_id, :provider_group_id, :email,
                :name, :description, :direct_members_count, :raw_data, NOW()
            )
            ON CONFLICT (organization_id, provider_group_id) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                direct_members_count = EXCLUDED.direct_members_count,
                raw_data = EXCLUDED.raw_data,
                last_synced_at = NOW(),
                updated_at = NOW()
            RETURNING {self._SELECT_FIELDS}
        """
        params = {
            "organization_id": dto.organization_id,
            "connection_id": dto.connection_id,
            "provider_group_id": dto.provider_group_id,
            "email": dto.email,
            "name": dto.name,
            "description": dto.description,
            "direct_members_count": dto.direct_members_count,
            "raw_data": json.dumps(dto.raw_data),
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def upsert_membership(self, dto: CreateGroupMembershipDTO) -> GroupMembership:
        query = """
            INSERT INTO group_membership (workspace_user_id, workspace_group_id, role)
            VALUES (:workspace_user_id, :workspace_group_id, :role)
            ON CONFLICT (workspace_user_id, workspace_group_id) DO UPDATE SET
                role = EXCLUDED.role
            RETURNING workspace_user_id, workspace_group_id, role, created_at
        """
        params = {
            "workspace_user_id": dto.workspace_user_id,
            "workspace_group_id": dto.workspace_group_id,
            "role": dto.role,
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return GroupMembership(
            workspace_user_id=row["workspace_user_id"],
            workspace_group_id=row["workspace_group_id"],
            role=row["role"],
            created_at=row["created_at"],
        )

    async def delete_memberships_for_group(self, group_id: int) -> int:
        query = "DELETE FROM group_membership WHERE workspace_group_id = $1"
        result = await self._conn.execute(query, group_id)
        count = int(result.split()[-1]) if result else 0
        return count

    def _map_to_model(self, row: asyncpg.Record | None) -> WorkspaceGroup | None:
        if row is None:
            return None

        raw_data = row["raw_data"]
        if isinstance(raw_data, str):
            import json

            raw_data = json.loads(raw_data)

        return WorkspaceGroup(
            id=row["id"],
            organization_id=row["organization_id"],
            connection_id=row["connection_id"],
            provider_group_id=row["provider_group_id"],
            email=row["email"],
            name=row["name"],
            description=row["description"],
            direct_members_count=row["direct_members_count"],
            raw_data=raw_data or {},
            last_synced_at=row["last_synced_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def find_paginated_with_member_count(
        self, organization_id: int, params: PaginationParamsDTO
    ) -> tuple[list[WorkspaceGroupWithMemberCountDTO], int]:
        offset = (params.page - 1) * params.page_size
        search_pattern = f"%{params.search}%" if params.search else None

        if search_pattern:
            count_query = """
                SELECT COUNT(*) as total
                FROM workspace_group
                WHERE organization_id = :organization_id
                  AND (name ILIKE :search OR email ILIKE :search)
            """
            count_query, count_values = bind_named(
                count_query,
                {"organization_id": organization_id, "search": search_pattern},
            )
        else:
            count_query = """
                SELECT COUNT(*) as total
                FROM workspace_group
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
                SELECT id, email, name, description, direct_members_count
                FROM workspace_group
                WHERE organization_id = :organization_id
                  AND (name ILIKE :search OR email ILIKE :search)
                ORDER BY name
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
                SELECT id, email, name, description, direct_members_count
                FROM workspace_group
                WHERE organization_id = :organization_id
                ORDER BY name
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
        groups = [
            WorkspaceGroupWithMemberCountDTO(
                id=row["id"],
                email=row["email"],
                name=row["name"],
                description=row["description"],
                direct_members_count=row["direct_members_count"],
            )
            for row in rows
        ]
        return groups, total

    async def count_by_organization(self, organization_id: int) -> int:
        query = """
            SELECT COUNT(*) as count
            FROM workspace_group
            WHERE organization_id = :organization_id
        """
        query, values = bind_named(query, {"organization_id": organization_id})
        row = await self._conn.fetchrow(query, *values)
        return row["count"] if row else 0

    async def find_with_members(
        self, organization_id: int, group_id: int
    ) -> GroupWithMembersDTO | None:
        group_query = """
            SELECT id, email, name, description, direct_members_count
            FROM workspace_group
            WHERE id = :group_id AND organization_id = :organization_id
        """
        group_query, group_values = bind_named(
            group_query, {"group_id": group_id, "organization_id": organization_id}
        )
        group_row = await self._conn.fetchrow(group_query, *group_values)
        if not group_row:
            return None

        members_query = """
            SELECT 
                wu.id as user_id, wu.email, wu.full_name, wu.avatar_url,
                gm.role
            FROM group_membership gm
            JOIN workspace_user wu ON wu.id = gm.workspace_user_id
            WHERE gm.workspace_group_id = :group_id
            ORDER BY wu.email
        """
        members_query, members_values = bind_named(
            members_query, {"group_id": group_id}
        )
        member_rows = await self._conn.fetch(members_query, *members_values)

        members = [
            GroupMemberWithUserDTO(
                user_id=row["user_id"],
                email=row["email"],
                full_name=row["full_name"],
                avatar_url=row["avatar_url"],
                role=row["role"],
            )
            for row in member_rows
        ]

        return GroupWithMembersDTO(
            id=group_row["id"],
            email=group_row["email"],
            name=group_row["name"],
            description=group_row["description"],
            direct_members_count=group_row["direct_members_count"],
            members=members,
        )
