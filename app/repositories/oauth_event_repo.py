import json
from typing import Any

from app.dtos.oauth_event_dtos import CreateOAuthEventDTO
from app.models.oauth_event import OAuthEvent

from .base_repository import BaseRepository


class OAuthEventRepository(BaseRepository[OAuthEvent]):
    def __init__(self, conn):
        super().__init__(conn, OAuthEvent)

    async def create(self, dto: CreateOAuthEventDTO) -> OAuthEvent:
        query = """
            INSERT INTO oauth_event (
                organization_id, connection_id, user_id, app_id, 
                event_type, event_time, raw_data
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        row = await self.conn.fetchrow(
            query,
            dto.organization_id,
            dto.connection_id,
            dto.user_id,
            dto.app_id,
            dto.event_type,
            dto.event_time,
            json.dumps(dto.raw_data),
        )
        return OAuthEvent.model_validate(row)

    async def find_paginated_by_app(
        self, organization_id: int, app_id: int, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        # Returns raw dicts for DTO mapping
        # Joining with workspace_user to get actor details
        query = """
            SELECT 
                e.*,
                u.email as actor_email,
                u.full_name as actor_name,
                u.avatar_url as actor_avatar_url
            FROM oauth_event e
            LEFT JOIN workspace_user u ON e.user_id = u.id
            WHERE e.organization_id = $1 AND e.app_id = $2
            ORDER BY e.event_time DESC
            LIMIT $3 OFFSET $4
        """
        rows = await self.conn.fetch(query, organization_id, app_id, limit, offset)
        return [dict(row) for row in rows]

    async def count_by_app(self, organization_id: int, app_id: int) -> int:
        query = "SELECT COUNT(*) FROM oauth_event WHERE organization_id = $1 AND app_id = $2"
        return await self.conn.fetchval(query, organization_id, app_id)
