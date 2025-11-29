import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging import setup_logging
from app.core.settings import settings
from app.database import db_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings.log_level)
    logger.info("Application startup initiated")
    await db_connection.connect()
    yield
    logger.info("Application shutdown initiated")
    await db_connection.close()
