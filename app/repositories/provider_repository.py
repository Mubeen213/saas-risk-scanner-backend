import json

import asyncpg

from app.database.query_builder import bind_named
from app.models.provider import Provider


class ProviderRepository:

    _SELECT_FIELDS = """
        id, name, slug, display_name, description, logo_url,
        website_url, documentation_url, status, metadata, created_at, updated_at
    """

    async def find_by_slug(
        self, conn: asyncpg.Connection, slug: str
    ) -> Provider | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM provider
            WHERE slug = :slug
        """
        query, values = bind_named(query, {"slug": slug})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_id(
        self, conn: asyncpg.Connection, provider_id: int
    ) -> Provider | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM provider
            WHERE id = :provider_id
        """
        query, values = bind_named(query, {"provider_id": provider_id})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    def _map_to_model(self, row: asyncpg.Record | None) -> Provider | None:
        if row is None:
            return None
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return Provider(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            display_name=row["display_name"],
            description=row["description"],
            logo_url=row["logo_url"],
            website_url=row["website_url"],
            documentation_url=row["documentation_url"],
            status=row["status"],
            metadata=metadata or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


provider_repository = ProviderRepository()
