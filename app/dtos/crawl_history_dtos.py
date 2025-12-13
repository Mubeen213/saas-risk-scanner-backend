from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.crawl_history import CrawlStatus, CrawlType


class CreateCrawlHistoryDTO(BaseModel):
    organization_id: int
    connection_id: int
    crawl_type: CrawlType
    status: CrawlStatus
    started_at: datetime
    stats_json: dict[str, Any] = Field(default_factory=dict)
    raw_debug_json: dict[str, Any] = Field(default_factory=dict)


class UpdateCrawlHistoryDTO(BaseModel):
    status: CrawlStatus | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    stats_json: dict[str, Any] | None = None
    raw_debug_json: dict[str, Any] | None = None
