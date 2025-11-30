import asyncpg

from app.database.query_builder import bind_named
from app.dtos.organization_dtos import CreateOrganizationDTO
from app.models.organization import Organization


class OrganizationRepository:

    _SELECT_FIELDS = """
        id, name, slug, domain, logo_url, plan_id,
        status, created_at, updated_at, deleted_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_domain(self, domain: str) -> Organization | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM organization
            WHERE LOWER(domain) = LOWER(:domain) AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"domain": domain})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_id(self, org_id: int) -> Organization | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM organization
            WHERE id = :org_id AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"org_id": org_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_slug(self, slug: str) -> Organization | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM organization
            WHERE slug = :slug AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"slug": slug})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def create(self, dto: CreateOrganizationDTO) -> Organization:
        query = f"""
            INSERT INTO organization (
                name, slug, domain, plan_id, status
            ) VALUES (
                :name, :slug, :domain, :plan_id, :status
            )
            RETURNING {self._SELECT_FIELDS}
        """
        params = {
            "name": dto.name,
            "slug": dto.slug,
            "domain": dto.domain,
            "plan_id": dto.plan_id,
            "status": dto.status,
        }
        query, values = bind_named(query, params)
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    def _map_to_model(self, row: asyncpg.Record | None) -> Organization | None:
        if row is None:
            return None
        return Organization(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            domain=row["domain"],
            logo_url=row["logo_url"],
            plan_id=row["plan_id"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )
