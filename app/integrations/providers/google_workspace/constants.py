GOOGLE_WORKSPACE_PROVIDER_SLUG = "google-workspace"

GOOGLE_DIRECTORY_API_BASE = "https://admin.googleapis.com/admin/directory/v1"
GOOGLE_REPORTS_API_BASE = "https://admin.googleapis.com/admin/reports/v1"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

GOOGLE_USERS_ENDPOINT = f"{GOOGLE_DIRECTORY_API_BASE}/users"
GOOGLE_GROUPS_ENDPOINT = f"{GOOGLE_DIRECTORY_API_BASE}/groups"
GOOGLE_GROUP_MEMBERS_ENDPOINT = (
    f"{GOOGLE_DIRECTORY_API_BASE}/groups/{{group_key}}/members"
)
GOOGLE_USER_TOKENS_ENDPOINT = f"{GOOGLE_DIRECTORY_API_BASE}/users/{{user_key}}/tokens"
GOOGLE_TOKEN_ACTIVITIES_ENDPOINT = (
    f"{GOOGLE_REPORTS_API_BASE}/activity/users/all/applications/token"
)

GOOGLE_WORKSPACE_ADMIN_SCOPES = [
    "https://www.googleapis.com/auth/admin.reports.audit.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/admin.directory.group.readonly",
    "https://www.googleapis.com/auth/admin.directory.user.security",
]

GOOGLE_SSO_SCOPES = [
    "openid",
    "email",
    "profile",
]

GOOGLE_RATE_LIMITS = {
    "users": {"requests_per_second": 10.0, "burst_size": 20},
    "groups": {"requests_per_second": 10.0, "burst_size": 20},
    "members": {"requests_per_second": 10.0, "burst_size": 20},
    "token_events": {"requests_per_second": 2.0, "burst_size": 5},
}

GOOGLE_DEFAULT_PAGE_SIZE = 100
GOOGLE_MAX_PAGE_SIZE = 500
