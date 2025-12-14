from typing import Generic, Type, TypeVar, Any
import re
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    def __init__(self, conn, model_cls: Type[T]):
        self.conn = conn
        self.model_cls = model_cls
        self._table_name = self._get_table_name()

    def _get_table_name(self) -> str:
        # Convert CamelCase to snake_case
        # e.g. OAuthApp -> oauth_app, AppGrant -> app_grant
        # Simple regex for CamelCase to snake_case
        name = self.model_cls.__name__
        # Handle OAuthApp -> oauth_app is tricky with simple regex if not standard
        # Let's use a explicit mapping or simple conversion
        # Standard: AppGrant -> app_grant. OAuthApp -> oauth_app (if O_Auth_App?)
        # Let's try to infer or just set it manually in child classes if needed.
        # But for now, let's implement the standard regex.
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    async def find_by_id(self, id: int) -> T | None:
        query = f"SELECT * FROM {self._table_name} WHERE id = $1"
        row = await self.conn.fetchrow(query, id)
        return self.model_cls.model_validate(dict(row)) if row else None
        
    async def find_all(self) -> list[T]:
        query = f"SELECT * FROM {self._table_name}"
        rows = await self.conn.fetch(query)
        return [self.model_cls.model_validate(dict(row)) for row in rows]
    
    async def delete(self, id: int) -> bool:
        query = f"DELETE FROM {self._table_name} WHERE id = $1"
        result = await self.conn.execute(query, id)
        return result == "DELETE 1"
