import json
from typing import Any

from app.dtos.oauth_app_dtos import CreateOAuthAppDTO
from app.models.oauth_app import OAuthApp

from .base_repository import BaseRepository


class OAuthAppRepository(BaseRepository[OAuthApp]):
    def __init__(self, conn):
        super().__init__(conn, OAuthApp)
        self._table_name = "oauth_app"

    async def find_by_id(self, id: int) -> OAuthApp | None:
        query = f"SELECT * FROM {self._table_name} WHERE id = $1"
        row = await self.conn.fetchrow(query, id)
        if not row:
            return None
            
        data = dict(row)
        if isinstance(data.get('raw_data'), str):
            import json
            data['raw_data'] = json.loads(data['raw_data'])
        return OAuthApp.model_validate(data)

    async def upsert(self, dto: CreateOAuthAppDTO) -> OAuthApp:
        query = """
            INSERT INTO oauth_app (
                organization_id, connection_id, client_id, name, 
                risk_score, is_system_app, is_trusted, scopes_summary, 
                image_url, raw_data
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (connection_id, client_id)
            DO UPDATE SET
                name = EXCLUDED.name,
                scopes_summary = EXCLUDED.scopes_summary,
                image_url = EXCLUDED.image_url,
                raw_data = EXCLUDED.raw_data,
                updated_at = NOW()
            RETURNING *
        """
        row = await self.conn.fetchrow(
            query,
            dto.organization_id,
            dto.connection_id,
            dto.client_id,
            dto.name,
            dto.risk_score,
            dto.is_system_app,
            dto.is_trusted,
            dto.scopes_summary,
            dto.image_url,
            json.dumps(dto.raw_data),
        )
        data = dict(row)
        if isinstance(data.get('raw_data'), str):
            data['raw_data'] = json.loads(data['raw_data'])
        
        result_app = OAuthApp.model_validate(data)
        # import logging
        # logger = logging.getLogger(__name__)
        # logger.info(f"Upserted app: {result_app.id} - {result_app.name} ({result_app.client_id})")
        return result_app

    async def find_paginated_with_stats(
        self, organization_id: int, limit: int, offset: int, search: str | None = None
    ) -> list[dict[str, Any]]:
        # Returns raw dicts to be mapped to OAuthAppWithStatsDTO by service
        # Using LEFT JOIN on app_grant to count active users
        params = [organization_id, limit, offset]
        search_clause = ""
        if search:
            search_clause = "AND name ILIKE $4"
            params.append(f"%{search}%")

        query = f"""
            SELECT 
                a.*,
                COUNT(g.id) FILTER (WHERE g.status = 'active') as active_grants_count,
                MAX(g.last_accessed_at) as last_activity_at
            FROM oauth_app a
            LEFT JOIN app_grant g ON a.id = g.app_id
            WHERE a.organization_id = $1
            {search_clause}
            GROUP BY a.id
            ORDER BY active_grants_count DESC, a.name ASC
            LIMIT $2 OFFSET $3
        """
        rows = await self.conn.fetch(query, *params)
        return [dict(row) for row in rows]

    async def count_by_organization(self, organization_id: int) -> int:
        query = "SELECT COUNT(*) FROM oauth_app WHERE organization_id = $1"
        return await self.conn.fetchval(query, organization_id)
