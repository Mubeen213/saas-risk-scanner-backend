import asyncpg

from app.database.query_builder import bind_named
from app.models.plan import Plan


class PlanRepository:

    _SELECT_FIELDS = """
        id, name, display_name, description, max_users, max_apps,
        price_monthly_cents, price_yearly_cents, is_active, created_at, updated_at
    """

    async def find_by_name(self, conn: asyncpg.Connection, name: str) -> Plan | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM plan
            WHERE name = :name AND is_active = TRUE
        """
        query, values = bind_named(query, {"name": name})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_id(self, conn: asyncpg.Connection, plan_id: int) -> Plan | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM plan
            WHERE id = :plan_id
        """
        query, values = bind_named(query, {"plan_id": plan_id})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    def _map_to_model(self, row: asyncpg.Record | None) -> Plan | None:
        if row is None:
            return None
        return Plan(
            id=row["id"],
            name=row["name"],
            display_name=row["display_name"],
            description=row["description"],
            max_users=row["max_users"],
            max_apps=row["max_apps"],
            price_monthly_cents=row["price_monthly_cents"],
            price_yearly_cents=row["price_yearly_cents"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


plan_repository = PlanRepository()
