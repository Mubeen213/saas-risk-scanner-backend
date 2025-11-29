import asyncpg

from app.database.query_builder import bind_named
from app.dtos.user_dtos import CreateUserDTO, UpdateUserDTO
from app.models.user import User


class UserRepository:

    _SELECT_FIELDS = """
        id, organization_id, role_id, email, full_name, avatar_url,
        provider_id, email_verified, status, invited_by_user_id,
        invited_at, joined_at, last_login_at, created_at, updated_at, deleted_at
    """

    async def find_by_provider_id(
        self, conn: asyncpg.Connection, provider_id: str
    ) -> User | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM "user"
            WHERE provider_id = :provider_id AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"provider_id": provider_id})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_email(self, conn: asyncpg.Connection, email: str) -> User | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM "user"
            WHERE LOWER(email) = LOWER(:email) AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"email": email})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def find_by_id(self, conn: asyncpg.Connection, user_id: int) -> User | None:
        query = f"""
            SELECT {self._SELECT_FIELDS}
            FROM "user"
            WHERE id = :user_id AND deleted_at IS NULL
        """
        query, values = bind_named(query, {"user_id": user_id})
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def create(self, conn: asyncpg.Connection, dto: CreateUserDTO) -> User:
        query = f"""
            INSERT INTO "user" (
                organization_id, role_id, email, full_name, avatar_url,
                provider_id, email_verified, status, joined_at, last_login_at
            ) VALUES (
                :organization_id, :role_id, :email, :full_name, :avatar_url,
                :provider_id, :email_verified, :status, :joined_at, :last_login_at
            )
            RETURNING {self._SELECT_FIELDS}
        """
        params = {
            "organization_id": dto.organization_id,
            "role_id": dto.role_id,
            "email": dto.email,
            "full_name": dto.full_name,
            "avatar_url": dto.avatar_url,
            "provider_id": dto.provider_id,
            "email_verified": dto.email_verified,
            "status": dto.status,
            "joined_at": dto.joined_at,
            "last_login_at": dto.last_login_at,
        }
        query, values = bind_named(query, params)
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    async def update(
        self, conn: asyncpg.Connection, user_id: int, dto: UpdateUserDTO
    ) -> User | None:
        update_fields = self._build_update_fields(dto)
        if not update_fields:
            return await self.find_by_id(conn, user_id)

        params = {"user_id": user_id, **update_fields}
        set_clause = ", ".join(f"{k} = :{k}" for k in update_fields.keys())

        query = f"""
            UPDATE "user"
            SET {set_clause}, updated_at = NOW()
            WHERE id = :user_id AND deleted_at IS NULL
            RETURNING {self._SELECT_FIELDS}
        """
        query, values = bind_named(query, params)
        row = await conn.fetchrow(query, *values)
        return self._map_to_model(row)

    def _build_update_fields(self, dto: UpdateUserDTO) -> dict:
        fields = {}
        if dto.full_name is not None:
            fields["full_name"] = dto.full_name
        if dto.avatar_url is not None:
            fields["avatar_url"] = dto.avatar_url
        if dto.email_verified is not None:
            fields["email_verified"] = dto.email_verified
        if dto.status is not None:
            fields["status"] = dto.status
        if dto.provider_id is not None:
            fields["provider_id"] = dto.provider_id
        if dto.joined_at is not None:
            fields["joined_at"] = dto.joined_at
        if dto.last_login_at is not None:
            fields["last_login_at"] = dto.last_login_at
        return fields

    def _map_to_model(self, row: asyncpg.Record | None) -> User | None:
        if row is None:
            return None
        return User(
            id=row["id"],
            organization_id=row["organization_id"],
            role_id=row["role_id"],
            email=row["email"],
            full_name=row["full_name"],
            avatar_url=row["avatar_url"],
            provider_id=row["provider_id"],
            email_verified=row["email_verified"],
            status=row["status"],
            invited_by_user_id=row["invited_by_user_id"],
            invited_at=row["invited_at"],
            joined_at=row["joined_at"],
            last_login_at=row["last_login_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )


user_repository = UserRepository()
