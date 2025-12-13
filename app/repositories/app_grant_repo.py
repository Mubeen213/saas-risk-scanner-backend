import json
from datetime import datetime
from typing import Any

from app.dtos.app_grant_dtos import CreateAppGrantDTO
from app.models.app_grant import AppGrant

from .base_repository import BaseRepository


class AppGrantRepository(BaseRepository[AppGrant]):
    def __init__(self, conn):
        super().__init__(conn, AppGrant)

    async def upsert(self, dto: CreateAppGrantDTO) -> AppGrant:
        query = """
            INSERT INTO app_grant (
                organization_id, connection_id, user_id, app_id, 
                status, scopes, granted_at, revoked_at, last_accessed_at, raw_data
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (user_id, app_id)
            DO UPDATE SET
                status = EXCLUDED.status,
                scopes = EXCLUDED.scopes,
                granted_at = COALESCE(EXCLUDED.granted_at, app_grant.granted_at),
                revoked_at = EXCLUDED.revoked_at,
                last_accessed_at = COALESCE(EXCLUDED.last_accessed_at, app_grant.last_accessed_at),
                raw_data = EXCLUDED.raw_data,
                updated_at = NOW()
            RETURNING *
        """
        row = await self.conn.fetchrow(
            query,
            dto.organization_id,
            dto.connection_id,
            dto.user_id,
            dto.app_id,
            dto.status,
            dto.scopes,
            dto.granted_at,
            dto.revoked_at,
            dto.last_accessed_at,
            json.dumps(dto.raw_data),
        )
        return AppGrant.model_validate(row)

    async def count_active_by_organization(self, organization_id: int) -> int:
        query = """
            SELECT COUNT(*) 
            FROM app_grant 
            WHERE organization_id = $1 AND status = 'active'
        """
        return await self.conn.fetchval(query, organization_id)

    async def find_by_app_with_users(
        self, organization_id: int, app_id: int
    ) -> list[Any]:
        from app.schemas.workspace import AppAuthorizationUserItemResponse
        
        query = """
            SELECT 
                g.user_id,
                u.email,
                u.full_name,
                u.avatar_url,
                g.scopes,
                g.granted_at as authorized_at,
                g.status
            FROM app_grant g
            JOIN workspace_user u ON u.id = g.user_id
            WHERE g.organization_id = $1 AND g.app_id = $2
            ORDER BY g.granted_at DESC
        """
        rows = await self.conn.fetch(query, organization_id, app_id)
        
        return [
            AppAuthorizationUserItemResponse(
                user_id=row["user_id"],
                email=row["email"],
                full_name=row["full_name"],
                avatar_url=row["avatar_url"],
                scopes=row["scopes"] if row["scopes"] else [],
                authorized_at=row["authorized_at"],
                status=row["status"]
            )
            for row in rows
        ]

    async def find_by_app_and_user(self, app_id: int, user_id: int) -> AppGrant | None:
        query = "SELECT * FROM app_grant WHERE app_id = $1 AND user_id = $2"
        row = await self.conn.fetchrow(query, app_id, user_id)
        return AppGrant.model_validate(row) if row else None
