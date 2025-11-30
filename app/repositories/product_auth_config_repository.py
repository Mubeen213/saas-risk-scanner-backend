import json

import asyncpg

from app.database.query_builder import bind_named
from app.models.product_auth_config import ProductAuthConfig


class ProductAuthConfigRepository:

    _SELECT_FIELDS = """
        id, product_id, identity_provider_id, auth_type, client_id, client_secret,
        authorization_url, token_url, userinfo_url, revoke_url,
        scopes, redirect_uri, additional_params, is_active, created_at, updated_at
    """

    def __init__(self, conn: asyncpg.Connection):
        self._conn = conn

    async def find_by_identity_provider_id(
        self, identity_provider_id: int
    ) -> ProductAuthConfig | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM product_auth_config
            WHERE identity_provider_id = :identity_provider_id AND product_id IS NULL AND is_active = TRUE
            LIMIT 1
        """
        query, values = bind_named(
            query, {"identity_provider_id": identity_provider_id}
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_product_id(self, product_id: int) -> ProductAuthConfig | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM product_auth_config
            WHERE product_id = :product_id AND is_active = TRUE
            LIMIT 1
        """
        query, values = bind_named(query, {"product_id": product_id})
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_platform_config_by_identity_provider_slug(
        self, identity_provider_slug: str
    ) -> ProductAuthConfig | None:
        query = """
            SELECT pac.id, pac.product_id, pac.identity_provider_id, pac.auth_type,
                   pac.client_id, pac.client_secret, pac.authorization_url,
                   pac.token_url, pac.userinfo_url, pac.revoke_url,
                   pac.scopes, pac.redirect_uri, pac.additional_params,
                   pac.is_active, pac.created_at, pac.updated_at
            FROM product_auth_config pac
            JOIN identity_provider ip ON pac.identity_provider_id = ip.id
            WHERE ip.slug = :identity_provider_slug AND pac.product_id IS NULL AND pac.is_active = TRUE
            LIMIT 1
        """
        query, values = bind_named(
            query, {"identity_provider_slug": identity_provider_slug}
        )
        row = await self._conn.fetchrow(query, *values)
        return self._map_to_model(row)

    def _map_to_model(self, row: asyncpg.Record | None) -> ProductAuthConfig | None:
        if row is None:
            return None
        scopes = row["scopes"]
        if isinstance(scopes, str):
            scopes = json.loads(scopes)
        additional_params = row["additional_params"]
        if isinstance(additional_params, str):
            additional_params = json.loads(additional_params)
        return ProductAuthConfig(
            id=row["id"],
            product_id=row["product_id"],
            identity_provider_id=row["identity_provider_id"],
            auth_type=row["auth_type"],
            client_id=row["client_id"],
            client_secret=row["client_secret"],
            authorization_url=row["authorization_url"],
            token_url=row["token_url"],
            userinfo_url=row["userinfo_url"],
            revoke_url=row["revoke_url"],
            scopes=scopes or [],
            redirect_uri=row["redirect_uri"],
            additional_params=additional_params or {},
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
