import json
from typing import Any

from app.dtos.oauth_event_dtos import CreateOAuthEventDTO, OAuthEventResponseDTO
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
        data = dict(row)
        if isinstance(data.get('raw_data'), str):
            data['raw_data'] = json.loads(data['raw_data'])
        return OAuthEvent.model_validate(data)

    async def exists(
        self, 
        organization_id: int, 
        user_id: int, 
        app_id: int, 
        event_type: str, 
        event_time: Any
    ) -> bool:
        query = """
            SELECT EXISTS(
                SELECT 1 FROM oauth_event 
                WHERE organization_id = $1 
                AND user_id = $2 
                AND app_id = $3 
                AND event_type = $4 
                AND event_time = $5
            )
        """
        return await self.conn.fetchval(
            query, 
            organization_id, 
            user_id, 
            app_id, 
            event_type, 
            event_time
        )

    async def find_paginated_by_app(
        self, organization_id: int, app_id: int, limit: int, offset: int, user_id: int | None = None
    ) -> list[OAuthEventResponseDTO]:
        # Returns raw dicts for DTO mapping
        # Joining with workspace_user to get actor details
        base_query = """
            SELECT 
                e.*,
                u.email as actor_email,
                u.full_name as actor_name,
                u.avatar_url as actor_avatar_url
            FROM oauth_event e
            LEFT JOIN identity_user u ON e.user_id = u.id
            WHERE e.organization_id = $1 AND e.app_id = $2
        """
        args = [organization_id, app_id]
        
        if user_id is not None:
            base_query += f" AND e.user_id = ${len(args) + 1}"
            args.append(user_id)
            
        base_query += f" ORDER BY e.event_time DESC LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}"
        args.extend([limit, offset])

        rows = await self.conn.fetch(base_query, *args)
        return [OAuthEventResponseDTO(**dict(row)) for row in rows]

    async def count_by_app(self, organization_id: int, app_id: int, user_id: int | None = None) -> int:
        query = "SELECT COUNT(*) FROM oauth_event WHERE organization_id = $1 AND app_id = $2"
        args = [organization_id, app_id]
        
        if user_id is not None:
            query += f" AND user_id = ${len(args) + 1}"
            args.append(user_id)
            
        return await self.conn.fetchval(query, *args)
