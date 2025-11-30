import asyncpg

from app.database.query_builder import bind_named
from app.models.role import Role


class RoleRepository:

    _SELECT_FIELDS = """
        id, name, display_name, description, created_at, updated_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_name(self, name: str) -> Role | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM role
            WHERE name = :name
        """
        query, values = bind_named(query, {"name": name})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_id(self, role_id: int) -> Role | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM role
            WHERE id = :role_id
        """
        query, values = bind_named(query, {"role_id": role_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    def _map_to_model(self, row: asyncpg.Record | None) -> Role | None:
        if row is None:
            return None
        return Role(
            id=row["id"],
            name=row["name"],
            display_name=row["display_name"],
            description=row["description"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
