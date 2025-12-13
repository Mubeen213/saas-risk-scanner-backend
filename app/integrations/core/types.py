from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SyncStep(str, Enum):
    USERS = "users"
    GROUPS = "groups"
    GROUP_MEMBERS = "group_members"
    TOKEN_EVENTS = "token_events"
    USER_TOKENS = "user_tokens"


class SyncStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


@dataclass
class AuthContext:
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None

    @property
    def authorization_header(self) -> str:
        return f"{self.token_type} {self.access_token}"


@dataclass
class RequestDefinition:
    method: HttpMethod
    url: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    cost: int = 1


@dataclass
class ApiResponse:
    status_code: int
    data: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def is_rate_limited(self) -> bool:
        return self.status_code == 429

    @property
    def is_unauthorized(self) -> bool:
        return self.status_code == 401

    @property
    def is_forbidden(self) -> bool:
        return self.status_code == 403


@dataclass
class TokenResponse:
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None
    token_type: str = "Bearer"
    scope: str | None = None


@dataclass
class UnifiedUser:
    provider_id: str
    email: str
    full_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    is_admin: bool = False
    is_delegated_admin: bool = False
    org_unit_path: str | None = None
    avatar_url: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedGroup:
    provider_id: str
    email: str
    name: str
    description: str | None = None
    direct_members_count: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedGroupMembership:
    user_provider_id: str
    group_provider_id: str
    role: str = "MEMBER"


@dataclass
class UnifiedTokenEvent:
    client_id: str
    user_email: str
    app_name: str | None = None
    scopes: list[str] = field(default_factory=list)
    client_type: str | None = None
    event_type: str = "authorize"
    event_time: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedToken:
    client_id: str
    app_name: str
    scopes: list[str]
    user_email: str | None = None  # Populated during context enrichment if needed
    is_system_app: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncContext:
    connection_id: int
    organization_id: int
    provider_slug: str
    auth_context: AuthContext
    started_at: datetime = field(default_factory=datetime.utcnow)
    current_step: SyncStep | None = None
    completed_steps: list[SyncStep] = field(default_factory=list)
    failed_steps: list[SyncStep] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
