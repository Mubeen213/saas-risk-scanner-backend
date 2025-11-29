from enum import Enum


class UserStatus(str, Enum):
    PENDING_INVITATION = "pending_invitation"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OrganizationStatus(str, Enum):
    PENDING_SETUP = "pending_setup"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    COMING_SOON = "coming_soon"
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    BLOCKED = "blocked"


class AuthType(str, Enum):
    OAUTH2 = "oauth2"
    BASIC_AUTH = "basic_auth"
    API_KEY = "api_key"


class ConnectionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    ERROR = "error"


class WorkspaceUserStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class DiscoveredAppStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class AuthorizationStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class RoleName(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class PlanName(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
