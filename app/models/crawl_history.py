from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CrawlType(str, Enum):
    USERS = "users"
    GROUPS = "groups"
    TOKENS = "tokens"
    EVENTS = "events"
    FULL = "full"


class CrawlStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class CrawlHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int

    crawl_type: CrawlType
    status: CrawlStatus

    started_at: datetime
    finished_at: datetime | None = None

    error_message: str | None = None
    stats_json: dict[str, Any] = Field(default_factory=dict)
    raw_debug_json: dict[str, Any] = Field(default_factory=dict)
