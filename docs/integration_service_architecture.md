# Integration Service Architecture

## 1. Architectural Principles

The Integration Service is designed to be the centralized gateway for all external SaaS provider interactions. It adheres to the following principles:

1.  **Async-First**: All I/O operations use `asyncio` for high concurrency and non-blocking execution.
2.  **Centralized Execution**: All HTTP requests flow through a single `ApiClient` core to enforce rate limiting, retries, logging, and authentication injection.
3.  **Abstracted Pagination**: Pagination logic is decoupled from business logic. The framework handles fetching next pages automatically.
4.  **Declarative Sync Pipelines**: The order of data fetching (e.g., Users → Groups → Activity) is configurable and strictly defined.
5.  **Provider Agnostic Core**: The core logic (`app/integrations/core/`) knows nothing about Google or Okta. Provider specifics are isolated in plugins (`app/integrations/providers/`).

---

┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Layer                                       │
│  /integrations/connect  │  /integrations/callback  │  /workspace/*          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                      │
│  IntegrationService  │  WorkspaceSyncService  │  DiscoveryService           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Provider Abstraction Layer                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  WorkspaceProvider (Abstract)                                         │   │
│  │  ├── authenticate(scopes) → tokens                                    │   │
│  │  ├── fetch_users() → List[WorkspaceUser]                              │   │
│  │  ├── fetch_groups() → List[WorkspaceGroup]                            │   │
│  │  ├── fetch_token_events(since) → List[TokenEvent]                     │   │
│  │  └── revoke_app_access(user, client_id)                               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│            ▲                    ▲                     ▲                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ GoogleWorkspace │  │ MicrosoftEntra  │  │   OktaProvider  │              │
│  │    Provider     │  │    Provider     │  │    (future)     │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Data Layer                                          │
│  OrgConnectionRepo  │  WorkspaceUserRepo  │  DiscoveredAppRepo              │
└─────────────────────────────────────────────────────────────────────────────┘

## 2. Folder Structure

```
app/
└── integrations/
    ├── __init__.py
    ├── core/                      # Framework Core (Provider Agnostic)
    │   ├── __init__.py
    │   ├── client.py              # Central Async HTTP Client
    │   ├── pagination.py          # Cursor, Offset, Link strategies
    │   ├── rate_limiter.py        # Token bucket / Leaky bucket implementation
    │   ├── orchestrator.py        # Manages sync job execution order
    │   └── types.py               # Common dataclasses (UnifiedUser, UnifiedGroup)
    └── providers/                 # Provider Implementations
        ├── __init__.py
        ├── google_workspace/
        │   ├── __init__.py
        │   ├── provider.py        # Main entry point
        │   ├── endpoints.py       # API definitions
        │   ├── adapters.py        # Data normalization (Google -> Unified)
        │   └── paginators.py      # Google-specific pagination config
        └── okta/                  # Future extensibility
            └── ...
```

---

## 3. Core Components

### 3.1. The Central `ApiClient`

Instead of raw HTTP calls, providers define a `RequestDefinition`. The `ApiClient` executes it.

```python
# app/integrations/core/client.py

class ApiClient:
    def __init__(self, rate_limiter: RateLimiter):
        self.session = aiohttp.ClientSession()
        self.rate_limiter = rate_limiter

    async def execute(self, request: RequestDefinition, auth_context: AuthContext) -> Any:
        """
        Single entry point for all API calls.
        Handles:
        - Auth header injection
        - Rate limiting (wait if needed)
        - Automatic Retries (429, 5xx)
        - Error normalization
        """
        await self.rate_limiter.acquire(request.cost)
        # ... execution logic ...

    # ...existing code...
    def execute_paginated(self, request: RequestDefinition, paginator: Paginator, auth_context: AuthContext):
        """
        Returns an AsyncGenerator yielding items from all pages.
        """
        # ... pagination loop ...

### 3.4. Credentials & Authentication Management

The `CredentialsManager` is responsible for the lifecycle of OAuth tokens. It ensures that the `ApiClient` always receives valid credentials and handles token rotation transparently.

```python
# app/integrations/core/auth.py

class CredentialsManager:
    def __init__(self, repo: CredentialsRepository, crypto: CryptoService, registry: ProviderRegistry):
        self.repo = repo
        self.crypto = crypto
        self.registry = registry

    async def get_valid_credentials(self, connection_id: UUID) -> AuthContext:
        """
        1. Load encrypted tokens from DB (org_provider_connection)
        2. Decrypt with Fernet
        3. Check token_expires_at
        4. If expired or near-expiry (<5 min):
           a. Get provider instance from registry
           b. Call provider.refresh_token(refresh_token)
           c. Encrypt new tokens
           d. Update DB (access_token, expires_at, last_token_refresh_at)
        5. Return AuthContext(access_token)
        """
        pass

    async def handle_api_error(self, connection_id: UUID, error: Exception) -> bool:
        """
        Handles 401/403 errors. Returns True if the operation should be retried.
        
        1. If 401 Unauthorized:
           - Trigger force refresh (call provider.refresh_token)
           - If refresh succeeds: Update DB, Return True (retry)
           - If refresh fails: Mark connection status='token_expired', Return False
        2. If 403 Forbidden:
           - Scopes likely revoked or insufficient
           - Mark connection status='error'
           - Log error_message
           - Return False
        3. If Rate Limited (429):
           - Handled by ApiClient's internal backoff, but if it bubbles up:
           - Return True (retry after delay)
        """
        pass
```

### 3.5. Interfaces & Protocols

To ensure loose coupling and testability, we define strict interfaces.

```python
# app/integrations/core/interfaces.py

class IProvider(ABC):
    """The contract that every SaaS provider (Google, Okta) must fulfill."""
    
    @property
    @abstractmethod
    def provider_slug(self) -> str: ...

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Exchanges a refresh token for a new access token."""
        ...

    @abstractmethod
    def get_sync_pipeline(self) -> list[SyncStep]:
        """Defines the order of sync operations."""
        ...

    @abstractmethod
    def get_paginator(self, step: SyncStep) -> PaginationStrategy:
        """Returns the pagination strategy for a specific step."""
        ...
        
    @abstractmethod
    def get_request_definition(self, step: SyncStep, params: dict) -> RequestDefinition:
        """Constructs the API request for a step."""
        ...

class ICredentialsRepository(ABC):
    """Abstracts database operations for credentials."""
    
    @abstractmethod
    async def get_connection_tokens(self, connection_id: UUID) -> ConnectionTokens: ...
    
    @abstractmethod
    async def update_tokens(self, connection_id: UUID, tokens: TokenResponse) -> None: ...
    
    @abstractmethod
    async def update_status(self, connection_id: UUID, status: ConnectionStatus, error: str | None = None) -> None: ...
```

---

## 4. Google Workspace Implementation
# ...existing code...
```

### 3.2. Centralized Pagination Framework

We define a `Paginator` protocol. Providers configure it, the Core executes it.

```python
# app/integrations/core/pagination.py

class PaginationStrategy(ABC):
    @abstractmethod
    def get_next_params(self, current_response: dict, current_params: dict) -> dict | None:
        """Calculates parameters for the next page"""
        pass

    @abstractmethod
    def extract_items(self, response: dict) -> list[Any]:
        """Extracts the list of items from the response body"""
        pass

# Strategies
class CursorPagination(PaginationStrategy):
    """For APIs like Google (pageToken)"""
    def __init__(self, cursor_key: str, input_param: str): ...

class OffsetPagination(PaginationStrategy):
    """For APIs like SQL-style (limit/offset)"""
    def __init__(self, limit: int, offset_key: str): ...

class LinkHeaderPagination(PaginationStrategy):
    """For APIs using RFC 5988 Link headers (GitHub style)"""
    ...
```

### 3.3. Sync Orchestrator & Execution Order

The order of operations is critical. For example, we cannot link Group Memberships if we haven't fetched Users yet.

We define a **Sync Pipeline** as a list of steps.

```python
# app/integrations/core/orchestrator.py

class SyncStep(Enum):
    USERS = "users"
    GROUPS = "groups"
    GROUP_MEMBERS = "group_members"
    TOKEN_EVENTS = "token_events"

class SyncOrchestrator:
    async def run_sync(self, provider: BaseProvider, connection: Connection):
        pipeline = provider.get_sync_pipeline() 
        # e.g., [USERS, GROUPS, GROUP_MEMBERS, TOKEN_EVENTS]
        
        for step in pipeline:
            await provider.execute_step(step, connection)
```

---

## 4. Google Workspace Implementation

### 4.1. API Endpoints & Correlation

Google Workspace does **not** return Group IDs in the `users.list` response. We must fetch Groups separately and then fetch Members for each group.

**Correlation Logic:**
1.  **Fetch Users**: Store `provider_user_id` (Google ID) and `email`.
2.  **Fetch Groups**: Store `provider_group_id` and `email`.
3.  **Fetch Members**: For each group, fetch members. The response contains `id` (User ID) or `email`. We match this against our `workspace_user` table to create the `group_membership` link.

# ...existing code...
### 4.2. Required Endpoints

| Resource | Method | Endpoint | Pagination Type | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Users** | `GET` | `/admin/directory/v1/users` | Cursor (`pageToken`) | |
| **Groups** | `GET` | `/admin/directory/v1/groups` | Cursor (`pageToken`) | |
| **Members** | `GET` | `/admin/directory/v1/groups/{groupKey}/members` | Cursor (`pageToken`) | |
| **User Tokens** | `GET` | `/admin/directory/v1/users/{userKey}/tokens` | None | **Per-User**. Use Batching. |
| **Token Events** | `GET` | `/admin/reports/v1/activity/users/all/applications/token` | Cursor (`pageToken`) | Domain-wide events. |

### 4.3. Google Provider Configuration

```python
# app/integrations/providers/google_workspace/provider.py

class GoogleWorkspaceProvider(BaseProvider):
    
    def get_sync_pipeline(self) -> list[SyncStep]:
        return [
            SyncStep.USERS,          # 1. Get all users
            SyncStep.GROUPS,         # 2. Get all groups
            SyncStep.GROUP_MEMBERS,  # 3. Link users to groups
            SyncStep.USER_TOKENS,    # 4. Batch fetch current tokens (Baseline Inventory)
            SyncStep.TOKEN_EVENTS    # 5. Get historical/recent activity
        ]

    def get_paginator(self, step: SyncStep) -> PaginationStrategy:
        if step == SyncStep.USERS:
            return CursorPagination(cursor_key="nextPageToken", input_param="pageToken")
        # ...
```

### 4.4. Batching Strategy for User Tokens

Since `tokens.list` is per-user, we use Google's Batch API to fetch tokens for multiple users in parallel, significantly reducing HTTP overhead.

**Execution Flow:**
1.  **Fetch All Users**: The `SyncOrchestrator` runs `SyncStep.USERS` first, populating the `workspace_user` table.
2.  **Chunk Users**: The provider reads users from the DB in chunks of 100 (Google Batch limit).
3.  **Construct Batch Request**: For each chunk, create a `multipart/mixed` HTTP request containing 100 individual `GET /users/{id}/tokens` calls.
4.  **Execute**: Send the single batch request to `https://www.googleapis.com/batch/admin/directory_v1`.
5.  **Parse**: Unpack the multipart response. Each part corresponds to one user.
6.  **Upsert**: Save tokens to `discovered_app` and `app_authorization`.

```python
# app/integrations/providers/google_workspace/adapters.py

async def fetch_tokens_batch(client: ApiClient, users: list[UnifiedUser]):
    """
    Constructs a multipart/mixed batch request to fetch tokens for up to 100 users at a time.
    """
    # Implementation details for Google Batch API
    pass
```

### 4.5. Required Scopes

To support all operations, the connection must request the following OAuth scopes:

| Scope URL | Purpose |
| :--- | :--- |
| `https://www.googleapis.com/auth/admin.reports.audit.readonly` | Fetch token activity events (Reports API) |
| `https://www.googleapis.com/auth/admin.directory.user.readonly` | List users and their metadata |
| `https://www.googleapis.com/auth/admin.directory.group.readonly` | List groups and memberships |
| `https://www.googleapis.com/auth/admin.directory.user.security` | **Sensitive**. List and revoke user tokens |

---

## 5. Data Models & Extensibility

### 5.1. Unified Data Models

To ensure the database remains clean, we normalize data *before* it leaves the integration layer.

```python
@dataclass
class UnifiedUser:
    provider_id: str
    email: str
    full_name: str
    is_admin: bool
    raw_data: dict  # Stored in JSONB

@dataclass
class UnifiedGroup:
    provider_id: str
    name: str
    email: str
    raw_data: dict

@dataclass
class UnifiedGroupMembership:
    user_provider_id: str
    group_provider_id: str
    role: str  # MEMBER, MANAGER, OWNER
```

### 5.2. Adding New Integrations (e.g., Okta)

To add Okta in the future:

1.  Create `app/integrations/providers/okta/`.
2.  Implement `OktaProvider` inheriting from `BaseProvider`.
3.  Define `OktaPaginator` (Okta uses Link headers).
4.  Define `get_sync_pipeline()` (Okta might have different dependencies).
5.  Register the provider in the `IntegrationRegistry`.

The `SyncOrchestrator` and `ApiClient` remain untouched.

---

## 6. Summary of Key Decisions

1.  **Single Async Client**: No scattered `requests.get` or `aiohttp.get`. Everything goes through `core.client.ApiClient`.
2.  **Explicit Ordering**: We explicitly define that Users must be fetched before Group Memberships.
3.  **Cursor Abstraction**: Google's `nextPageToken` is just configuration passed to the generic `execute_paginated` method.
4.  **Correlation**: We handle the "Google doesn't give groups in user object" problem by adding a dedicated `GROUP_MEMBERS` sync step.
