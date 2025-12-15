import json

from app.dtos.crawl_history_dtos import CreateCrawlHistoryDTO, UpdateCrawlHistoryDTO
from app.models.crawl_history import CrawlHistory

from .base_repository import BaseRepository


class CrawlHistoryRepository(BaseRepository[CrawlHistory]):
    def __init__(self, conn):
        super().__init__(conn, CrawlHistory)

    async def create(self, dto: CreateCrawlHistoryDTO) -> CrawlHistory:
        query = """
            INSERT INTO crawl_history (
                organization_id, connection_id, crawl_type, status, 
                started_at, finished_at, error_message, stats_json, raw_debug_json
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """
        row = await self.conn.fetchrow(
            query,
            dto.organization_id,
            dto.connection_id,
            dto.crawl_type.value,
            dto.status.value,
            dto.started_at,
            None,
            None,
            json.dumps(dto.stats_json),
            json.dumps(dto.raw_debug_json),
        )
        data = dict(row)
        if isinstance(data.get('stats_json'), str):
            data['stats_json'] = json.loads(data['stats_json'])
        if isinstance(data.get('raw_debug_json'), str):
            data['raw_debug_json'] = json.loads(data['raw_debug_json'])
        return CrawlHistory.model_validate(data)

    async def update(self, id: int, dto: UpdateCrawlHistoryDTO) -> CrawlHistory | None:
        update_data = dto.model_dump(exclude_unset=True)
        if not update_data:
            return await self.find_by_id(id)

        set_clauses = []
        values = []
        idx = 1
        
        for key, value in update_data.items():
            if key in ('stats_json', 'raw_debug_json') and isinstance(value, dict):
                value = json.dumps(value)
            # Handle Enum serialization
            if hasattr(value, "value"):
                value = value.value
            
            set_clauses.append(f"{key} = ${idx}")
            values.append(value)
            idx += 1
            
        values.append(id)
        query = f"""
            UPDATE crawl_history 
            SET {', '.join(set_clauses)}
            WHERE id = ${idx}
            RETURNING *
        """
        
        row = await self.conn.fetchrow(query, *values)
        if not row:
            return None
            
        data = dict(row)
        if isinstance(data.get('stats_json'), str):
            data['stats_json'] = json.loads(data['stats_json'])
        if isinstance(data.get('raw_debug_json'), str):
            data['raw_debug_json'] = json.loads(data['raw_debug_json'])
            
        return CrawlHistory.model_validate(data)

    async def find_last_successful_crawl(
        self, connection_id: int, crawl_type: str
    ) -> CrawlHistory | None:
        query = """
            SELECT *
            FROM crawl_history
            WHERE connection_id = $1 
              AND crawl_type = $2 
              AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1
        """
        row = await self.conn.fetchrow(query, connection_id, crawl_type)
        if not row:
            return None
            
        data = dict(row)
        if isinstance(data.get('stats_json'), str):
            data['stats_json'] = json.loads(data['stats_json'])
        if isinstance(data.get('raw_debug_json'), str):
            data['raw_debug_json'] = json.loads(data['raw_debug_json'])
            
        return CrawlHistory.model_validate(data)

    async def find_last_crawl(self, connection_id: int) -> CrawlHistory | None:
        query = """
            SELECT *
            FROM crawl_history
            WHERE connection_id = $1
            ORDER BY started_at DESC
            LIMIT 1
        """
        row = await self.conn.fetchrow(query, connection_id)
        if not row:
            return None
            
        data = dict(row)
        if isinstance(data.get('stats_json'), str):
            data['stats_json'] = json.loads(data['stats_json'])
        if isinstance(data.get('raw_debug_json'), str):
            data['raw_debug_json'] = json.loads(data['raw_debug_json'])
            
        return CrawlHistory.model_validate(data)
