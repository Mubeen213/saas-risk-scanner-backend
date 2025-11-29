import logging
from collections.abc import AsyncGenerator
from typing import Annotated, Optional

import asyncpg
from fastapi import Depends, HTTPException, status

from app.core.settings import settings

logger = logging.getLogger(__name__)


class PostgreSQLConnection:

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        min_size: int = 1,
        max_size: int = 10,
    ):
        self.pool: Optional[asyncpg.Pool] = None
        self.database = database
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "min_size": min_size,
            "max_size": max_size,
        }
        logger.debug(
            f"PostgreSQL connection config initialized for database: {self.database}"
        )

    async def connect(self) -> None:
        if self.pool is not None:
            logger.debug(
                f"PostgreSQL connection pool already exists for: {self.database}"
            )
            return

        try:
            logger.info(f"Connecting to PostgreSQL database: {self.database}")
            self.pool = await asyncpg.create_pool(**self.config)
            logger.info(
                f"PostgreSQL connection pool created successfully: {self.database}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create PostgreSQL connection pool for {self.database}: {str(e)}"
            )
            self.pool = None
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection failed: {str(e)}",
            )

    async def close(self) -> None:
        if self.pool is None:
            logger.debug(f"No active connection pool to close for: {self.database}")
            return

        try:
            logger.info(f"Closing PostgreSQL connection pool: {self.database}")
            await self.pool.close()
            self.pool = None
            logger.info(
                f"PostgreSQL connection pool closed successfully: {self.database}"
            )
        except Exception as e:
            logger.error(
                f"Error closing PostgreSQL connection pool for {self.database}: {str(e)}"
            )
            self.pool = None

    def get_connection(self) -> asyncpg.pool.PoolAcquireContext:
        if self.pool is None:
            logger.error(f"Connection pool not initialized for {self.database}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database connection pool is not initialized. Call connect() first.",
            )
        return self.pool.acquire()

    async def is_connected(self) -> bool:
        try:
            if self.pool is None:
                logger.debug(f"Connection pool is None for database: {self.database}")
                return False

            if self.pool.is_closing():
                logger.debug(
                    f"Connection pool is closing for database: {self.database}"
                )
                return False

            return True
        except Exception as e:
            logger.error(
                f"Unexpected error checking connection status for {self.database}: {str(e)}"
            )
            return False


db_connection = PostgreSQLConnection(
    host=settings.database_host,
    port=settings.database_port,
    user=settings.database_user,
    password=settings.database_password,
    database=settings.database_name,
    min_size=settings.database_pool_min_size,
    max_size=settings.database_pool_max_size,
)


async def get_db_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    async with db_connection.get_connection() as connection:
        yield connection


DbConnectionDep = Annotated[asyncpg.Connection, Depends(get_db_connection)]
