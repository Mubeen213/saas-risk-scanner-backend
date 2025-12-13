from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OAuthEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    connection_id: int

    user_id: int
    app_id: int

    event_type: str  # authorize, revoke, activity
    event_time: datetime

    raw_data: dict[str, Any] = Field(default_factory=dict)

    created_at: datetime
