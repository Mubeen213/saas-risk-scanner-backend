# SaaS Risk Scanner - Database Models

## Overview

This document defines the database schema for the SaaS Risk Scanner platform. The design follows these principles:

- **Primary Keys:** Integer-based (`SERIAL`/`BIGSERIAL`) for performance
- **State Management:** Enum-based status fields for all stateful entities
- **Audit Trail:** `created_at`, `updated_at`, `deleted_at` (soft delete) on all tables
- **Self-Explanatory Naming:** Clear, descriptive field names
- **Single Responsibility:** Each table has one clear purpose
- **No Stored Aggregates:** Statistics are computed via queries/views

---

## Table Tiers

| Tier | Purpose | Tables |
|------|---------|--------|
| **Tier 1** | Platform Core | `plan`, `role`, `organization`, `user` |
| **Tier 2** | Knowledge Base (Seed/Static) | `provider`, `category`, `product`, `product_auth_config` |
| **Tier 3** | Org Connections | `org_provider_connection` |
| **Tier 4** | Discovery | `workspace_user`, `discovered_app`, `app_authorization` |
| **Tier 5** | Risk Analysis | `risk_assessment` |
| **Tier 6** | Operations | `sync_schedule`, `sync_job`, `audit_log` |

---

## Entity Relationship Diagram

```
TIER 1: Platform Core
┌──────────┐     ┌──────────────┐     ┌──────────┐
│   plan   │◀────│ organization │────▶│   role   │
└──────────┘     └──────────────┘     └──────────┘
                        │
                        ▼
                 ┌──────────┐
                 │   user   │
                 └──────────┘

TIER 2: Knowledge Base
┌──────────┐     ┌──────────┐     ┌──────────────────┐
│ provider │     │ product  │────▶│product_auth_config│
└──────────┘     └──────────┘     └──────────────────┘
      │               │
      │               ▼
      │         ┌──────────┐
      │         │ category │
      │         └──────────┘
      │
TIER 3: Org Connections
      │
      ▼
┌───────────────────────┐
│org_provider_connection│◀──── organization
└───────────────────────┘
            │
            │
TIER 4: Discovery
            │
            ├──────────────────┐
            ▼                  ▼
    ┌──────────────┐   ┌───────────────┐
    │workspace_user│   │ discovered_app│───▶ product (optional match)
    └──────────────┘   └───────────────┘
            │                  │
            └────────┬─────────┘
                     ▼
            ┌─────────────────┐
            │app_authorization│
            └─────────────────┘
```

---

# TIER 1: Platform Core

## 1.1 plan

Subscription plans available on the platform.

```sql
CREATE TABLE plan (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,   -- 'free', 'starter', 'professional', 'enterprise'
    display_name    VARCHAR(100) NOT NULL,
    description     TEXT,
    
    -- Limits
    max_users               INTEGER,               -- NULL = unlimited
    max_apps                INTEGER,               -- Max discovered apps
    
    -- Pricing
    price_monthly_cents     INTEGER DEFAULT 0,
    price_yearly_cents      INTEGER DEFAULT 0,
    
    is_active       BOOLEAN DEFAULT TRUE,
    
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed data
INSERT INTO plan (name, display_name, max_users, price_monthly_cents) VALUES
    ('free', 'Free', 24, 0),
    ('starter', 'Starter',  12, 2900),
    ('professional', 'Professional', 6, 9900),
    ('enterprise', 'Enterprise', NULL, NULL, 1, NULL);
```

---

## 1.2 role

User roles within an organization.

```sql
CREATE TABLE role (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(50) NOT NULL UNIQUE,   -- 'owner', 'admin', 'member', 'viewer'
    display_name    VARCHAR(100) NOT NULL,
    description     TEXT,
    
    -- Permissions (granular)
    permissions     JSONB DEFAULT '{}',            -- {"manage_users": true, "revoke_apps": true, "view_only": false}
    
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed data
INSERT INTO role (name, display_name, is_system, permissions, sort_order) VALUES
    ('owner', 'Owner', TRUE, '{"all": true}', 1),
    ('admin', 'Admin', TRUE, '{"manage_users": true, "manage_settings": true, "revoke_apps": true, "view_reports": true}', 2),
    ('member', 'Member', TRUE, '{"revoke_apps": true, "view_reports": true}', 3),
    ('viewer', 'Viewer', TRUE, '{"view_reports": true}', 4);
```

---

## 1.3 organization

Customer accounts (companies using our platform).

```sql
CREATE TYPE organization_status AS ENUM (
    'pending_setup',
    'active',
    'suspended',
    'cancelled'
);

CREATE TABLE organization (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    
    -- Identity
    name                    VARCHAR(255) NOT NULL,
    slug                    VARCHAR(100) NOT NULL UNIQUE,
    domain                  VARCHAR(255),
    logo_url                TEXT,
    
    -- Subscription
    plan_id                 INTEGER NOT NULL REFERENCES plan(id),
    subscription_status     VARCHAR(50) DEFAULT 'trialing',  -- 'trialing', 'active', 'past_due', 'cancelled'
    subscription_started_at TIMESTAMP WITH TIME ZONE,
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    trial_ends_at           TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status                  organization_status NOT NULL DEFAULT 'pending_setup',
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_organization_slug ON organization(slug);
CREATE INDEX idx_organization_domain ON organization(domain);
CREATE INDEX idx_organization_status ON organization(status);
CREATE INDEX idx_organization_plan ON organization(plan_id);
```

---

## 1.4 user

Platform users (people who log into our dashboard). Each user belongs to one organization.

```sql
CREATE TYPE user_status AS ENUM (
    'pending_invitation',
    'active',
    'suspended',
    'deactivated'
);

CREATE TABLE "user" (
    id                  SERIAL PRIMARY KEY,
    organization_id     INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    role_id             INTEGER NOT NULL REFERENCES role(id),
    
    -- Identity
    email               VARCHAR(255) NOT NULL,
    full_name           VARCHAR(255),
    avatar_url          TEXT,
    
    -- Auth (Google SSO)
    provider_id           VARCHAR(255) UNIQUE,
    email_verified      BOOLEAN DEFAULT FALSE,
    
    -- Status
    status              user_status NOT NULL DEFAULT 'pending_invitation',
    
    -- Invitation tracking
    invited_by_user_id  INTEGER REFERENCES "user"(id),
    invited_at          TIMESTAMP WITH TIME ZONE,
    joined_at           TIMESTAMP WITH TIME ZONE,
    
    -- Activity
    last_login_at       TIMESTAMP WITH TIME ZONE,
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(organization_id, email)
);

CREATE INDEX idx_user_organization ON "user"(organization_id);
CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_provider_id ON "user"(provider_id);
CREATE INDEX idx_user_status ON "user"(status);
CREATE INDEX idx_user_role ON "user"(role_id);
```

---

# TIER 2: Knowledge Base (Our Catalog)

These are seed/static tables that we maintain. They represent our knowledge about providers and third-party apps.

## 2.1 provider

Identity providers we integrate with (Google Workspace, Microsoft 365, etc.).

```sql
CREATE TYPE provider_status AS ENUM (
    'active',
    'coming_soon',
    'deprecated',
    'maintenance'
);

CREATE TABLE provider (
    id                  SERIAL PRIMARY KEY,
    
    -- Identity
    name                VARCHAR(100) NOT NULL UNIQUE,  -- 'google_workspace'
    slug                VARCHAR(50) NOT NULL UNIQUE,   -- 'google-workspace'
    display_name        VARCHAR(255) NOT NULL,         -- 'Google Workspace'
    
    -- Branding
    description         TEXT,
    logo_url            TEXT,
    website_url         TEXT,
    documentation_url   TEXT,
    
    -- Status
    status              provider_status NOT NULL DEFAULT 'active',
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed data
INSERT INTO provider (name, slug, display_name, status) VALUES
    ('google_workspace', 'google-workspace', 'Google Workspace', 'active'),
    ('microsoft_365', 'microsoft-365', 'Microsoft 365', 'coming_soon');
```

---

## 2.2 category

App categories for organizing products.

```sql
CREATE TABLE category (
    id              SERIAL PRIMARY KEY,
    
    -- Identity
    name            VARCHAR(100) NOT NULL UNIQUE,  -- 'ai_ml'
    slug            VARCHAR(50) NOT NULL UNIQUE,   -- 'ai-ml'
    display_name    VARCHAR(255) NOT NULL,         -- 'AI & Machine Learning'
    
    -- Branding
    description     TEXT,
    
    sort_order      INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed data
INSERT INTO category (name, slug, display_name, icon) VALUES
    ('ai_ml', 'ai-ml', 'AI & Machine Learning', '🤖'),
    ('productivity', 'productivity', 'Productivity', '📊'),
    ('storage', 'storage', 'Cloud Storage', '☁️'),
    ('communication', 'communication', 'Communication', '💬'),
    ('development', 'development', 'Development Tools', '🛠️'),
    ('security', 'security', 'Security', '🔒'),
    ('analytics', 'analytics', 'Analytics', '📈'),
    ('other', 'other', 'Other', '📦');
```

---

## 2.3 product

Catalog of known third-party applications. Pure identity info - no risk data here.

```sql
CREATE TYPE product_status AS ENUM (
    'active',
    'inactive',
    'under_review',
    'blocked'
);

CREATE TABLE product (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    
    -- Relationships
    provider_id             INTEGER REFERENCES provider(id),   -- Which provider ecosystem (nullable)
    category_id             INTEGER REFERENCES category(id),
    
    -- Identity
    name                    VARCHAR(255) NOT NULL,
    slug                    VARCHAR(100) UNIQUE,
    
    -- Branding
    description             TEXT,
    logo_url                TEXT,
    website_url             TEXT,
    
    -- Legal/Compliance links (for reference, not risk assessment)
    privacy_policy_url      TEXT,
    terms_of_service_url    TEXT,
    security_page_url       TEXT,
    
    
    -- Company info
    company_name            VARCHAR(255),
    
    -- Status
    status                  product_status NOT NULL DEFAULT 'active',
    is_verified             BOOLEAN DEFAULT FALSE,  -- We've manually verified this product
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_provider ON product(provider_id);
CREATE INDEX idx_product_category ON product(category_id);
CREATE INDEX idx_product_status ON product(status);
CREATE INDEX idx_product_slug ON product(slug);
```

---

## 2.4 product_auth_config

Authentication configuration templates for products. Defines HOW to authenticate - not the actual credentials.

Supports: OAuth2, Basic Auth, API Key

```sql
CREATE TYPE auth_type AS ENUM (
    'oauth2',
    'basic_auth',
    'api_key'
);

CREATE TABLE product_auth_config (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    product_id              INTEGER NOT NULL REFERENCES product(id) ON DELETE CASCADE,
    
    -- Auth type
    auth_type               auth_type NOT NULL,
    name                    VARCHAR(100),           -- e.g., 'Default OAuth', 'Admin API'
    description             TEXT,
    
    -- ============ OAuth2 Configuration ============
    -- URLs
    oauth_authorization_url TEXT,
    oauth_token_url         TEXT,
    oauth_revoke_url        TEXT,
    oauth_userinfo_url      TEXT,
    
    -- OAuth settings
    oauth_scopes            TEXT[] DEFAULT '{}',                    -- Available scopes
    oauth_grant_types       TEXT[] DEFAULT '{authorization_code}',  -- 'authorization_code', 'client_credentials', 'refresh_token'
    oauth_response_type     VARCHAR(50) DEFAULT 'code',
    oauth_pkce_required     BOOLEAN DEFAULT FALSE,
    
    -- Default client credentials (can be overridden per org)
    oauth_default_client_id     VARCHAR(255),
    oauth_default_client_secret TEXT,                               -- Encrypted
    oauth_default_redirect_urls TEXT[] DEFAULT '{}',
    
    -- ============ API Key Configuration ============
    api_key_header_name     VARCHAR(100),           -- e.g., 'X-API-Key', 'Authorization'
    api_key_prefix          VARCHAR(50),            -- e.g., 'Bearer ', 'Api-Key '
    api_key_query_param     VARCHAR(100),           -- If passed as query param instead
    
    -- ============ Basic Auth Configuration ============
    basic_auth_username_field   VARCHAR(100) DEFAULT 'username',
    basic_auth_password_field   VARCHAR(100) DEFAULT 'password',
    
    -- ============ Common Configuration ============
    base_url                TEXT,                   -- API base URL
    extra_headers           JSONB DEFAULT '{}',     -- Additional headers to send
    extra_params            JSONB DEFAULT '{}',     -- Additional params
    
    -- Status
    is_active               BOOLEAN DEFAULT TRUE,
    is_default              BOOLEAN DEFAULT FALSE,  -- Default config for this product
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_product_auth_config_product ON product_auth_config(product_id);
CREATE INDEX idx_product_auth_config_type ON product_auth_config(auth_type);
CREATE INDEX idx_product_auth_config_active ON product_auth_config(is_active) WHERE is_active = TRUE;
```

---

# Summary: Tier 1 & Tier 2

## Tier 1: Platform Core

| Table | Purpose |
|-------|---------|
| `plan` | Subscription plans (free, starter, pro, enterprise) with limits and pricing |
| `role` | User roles (owner, admin, member, viewer) with permissions |
| `organization` | Customer accounts with plan reference |
| `user` | Platform users belonging to one org with role |

## Tier 2: Knowledge Base

| Table | Purpose |
|-------|---------|
| `provider` | Identity providers we integrate with (Google, Microsoft) |
| `category` | App categories (AI/ML, Productivity, Storage) |
| `product` | Known third-party apps catalog (identity info only) |
| `product_auth_config` | How to authenticate with products (OAuth2, Basic Auth, API Key templates) |

---

# TIER 3: Org Connections

## 3.1 org_provider_connection

Stores org's connection to a provider (Google Workspace). Contains OAuth tokens for scanning.

```sql
CREATE TYPE connection_status AS ENUM (
    'pending',
    'connected',
    'expired',
    'revoked',
    'error'
);

CREATE TABLE org_provider_connection (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    organization_id         INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    provider_id             INTEGER NOT NULL REFERENCES provider(id),
    
    -- Status
    status                  connection_status NOT NULL DEFAULT 'pending',
    
    -- OAuth tokens (encrypted at app level)
    access_token            TEXT,
    refresh_token           TEXT,
    token_expires_at        TIMESTAMP WITH TIME ZONE,
    granted_scopes          TEXT[] DEFAULT '{}',
    
    -- Provider-specific identifiers
    provider_customer_id    VARCHAR(100),          -- Google: customerId, Microsoft: tenantId
    provider_domain         VARCHAR(255),          -- Primary domain from provider
    
    -- Connection tracking
    connected_by_user_id    INTEGER REFERENCES "user"(id),
    connected_at            TIMESTAMP WITH TIME ZONE,
    last_token_refresh_at   TIMESTAMP WITH TIME ZONE,
    
    -- Error tracking
    last_error_message      TEXT,
    last_error_at           TIMESTAMP WITH TIME ZONE,
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(organization_id, provider_id)
);

CREATE INDEX idx_org_provider_conn_org ON org_provider_connection(organization_id);
CREATE INDEX idx_org_provider_conn_status ON org_provider_connection(status);
```

---

# TIER 4: Discovery

Data discovered from scanning customer's workspace via Reports API and Directory API.

## 4.1 workspace_user

Employees discovered from org's Google Workspace (via Directory API).

**Deduplication:** `provider_user_id` is unique per org - upsert on sync.

```sql
CREATE TYPE workspace_user_status AS ENUM (
    'active',
    'suspended',
    'deleted'
);

CREATE TABLE workspace_user (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    organization_id         INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    org_provider_connection_id INTEGER NOT NULL REFERENCES org_provider_connection(id) ON DELETE CASCADE,
    
    -- Provider's unique ID (for deduplication)
    provider_user_id        VARCHAR(255) NOT NULL,     -- Google: user.id
    
    -- User info (from Directory API)
    email                   VARCHAR(255) NOT NULL,
    full_name               VARCHAR(255),
    avatar_url              TEXT,
    
    -- Organizational info
    org_unit_path           TEXT,                      -- /Engineering/Backend
    is_admin                BOOLEAN DEFAULT FALSE,
    is_suspended            BOOLEAN DEFAULT FALSE,
    
    -- Status
    status                  workspace_user_status NOT NULL DEFAULT 'active',
    
    -- Sync metadata
    first_seen_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_synced_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Raw API response (for debugging/future fields)
    raw_data                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Deduplication: one record per user per org
    UNIQUE(organization_id, provider_user_id)
);

CREATE INDEX idx_workspace_user_org ON workspace_user(organization_id);
CREATE INDEX idx_workspace_user_email ON workspace_user(email);
CREATE INDEX idx_workspace_user_provider_id ON workspace_user(provider_user_id);
CREATE INDEX idx_workspace_user_status ON workspace_user(status);
```

---

## 4.2 discovered_app

Third-party apps discovered in org's workspace (via Reports API token events).

**Deduplication:** `client_id` is unique per org - upsert on sync.

```sql
CREATE TYPE discovered_app_status AS ENUM (
    'active',
    'revoked',
    'blocked'
);

CREATE TABLE discovered_app (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    organization_id         INTEGER NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
    org_provider_connection_id INTEGER NOT NULL REFERENCES org_provider_connection(id) ON DELETE CASCADE,
    
    -- Link to our catalog (nullable if unknown app)
    product_id              INTEGER REFERENCES product(id),
    
    -- App identity from Reports API (for deduplication)
    client_id               VARCHAR(255) NOT NULL,     -- OAuth client_id (unique identifier)
    
    -- App info from Reports API
    app_name                VARCHAR(255),              -- display name from Google
    client_type             VARCHAR(50),               -- WEB, NATIVE_ANDROID, NATIVE_IOS, NATIVE_DESKTOP
    
    -- Aggregated scopes (union of all user authorizations)
    all_scopes              TEXT[] DEFAULT '{}',
    
    -- Status & admin actions
    status                  discovered_app_status NOT NULL DEFAULT 'active',
    is_sanctioned           BOOLEAN,                   -- NULL=pending, TRUE=approved, FALSE=blocked
    sanctioned_by_user_id   INTEGER REFERENCES "user"(id),
    sanctioned_at           TIMESTAMP WITH TIME ZONE,
    sanction_notes          TEXT,
    
    -- Sync metadata
    first_seen_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_synced_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Deduplication: one record per client_id per org
    UNIQUE(organization_id, client_id)
);

CREATE INDEX idx_discovered_app_org ON discovered_app(organization_id);
CREATE INDEX idx_discovered_app_client_id ON discovered_app(client_id);
CREATE INDEX idx_discovered_app_product ON discovered_app(product_id);
CREATE INDEX idx_discovered_app_status ON discovered_app(status);
```

---

## 4.3 app_authorization

Which workspace_user authorized which discovered_app, with what scopes.

**Source:** Reports API `authorize` events
**Deduplication:** One record per (user, app) pair - upsert scopes on re-authorization

```sql
CREATE TYPE authorization_status AS ENUM (
    'active',
    'revoked'
);

CREATE TABLE app_authorization (
   id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY
    discovered_app_id       INTEGER NOT NULL REFERENCES discovered_app(id) ON DELETE CASCADE,
    workspace_user_id       INTEGER NOT NULL REFERENCES workspace_user(id) ON DELETE CASCADE,
    
    -- Authorization details (from Reports API)
    scopes                  TEXT[] DEFAULT '{}',
    
    -- Status
    status                  authorization_status NOT NULL DEFAULT 'active',
    
    -- Timeline (from Reports API events)
    authorized_at           TIMESTAMP WITH TIME ZONE,  -- From Reports API event timestamp
    revoked_at              TIMESTAMP WITH TIME ZONE,
    
    -- Revocation tracking (if revoked via our platform)
    revoked_by_user_id      INTEGER REFERENCES "user"(id),
    revoke_method           VARCHAR(50),               -- 'manual', 'bulk', 'policy'
    
    -- Sync metadata
    first_seen_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_synced_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Raw API response (Reports API event)
    raw_data                JSONB DEFAULT '{}',
    
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Deduplication: one record per user-app pair
    UNIQUE(discovered_app_id, workspace_user_id)
);

CREATE INDEX idx_app_auth_app ON app_authorization(discovered_app_id);
CREATE INDEX idx_app_auth_user ON app_authorization(workspace_user_id);
CREATE INDEX idx_app_auth_status ON app_authorization(status);
CREATE INDEX idx_app_auth_authorized_at ON app_authorization(authorized_at);
```

---

# Summary: Tier 3 & Tier 4

## Tier 3: Org Connections

| Table | Purpose | Unique Key |
|-------|---------|------------|
| `org_provider_connection` | Org's OAuth connection to Google Workspace (tokens for scanning) | `(organization_id, provider_id)` |

## Tier 4: Discovery

| Table | Purpose | Unique Key | Source API |
|-------|---------|------------|------------|
| `workspace_user` | Employees from customer's workspace | `(organization_id, provider_user_id)` | Directory API |
| `discovered_app` | Third-party apps found in workspace | `(organization_id, client_id)` | Reports API |
| `app_authorization` | Who authorized what app with which scopes | `(discovered_app_id, workspace_user_id)` | Reports API |

---

## Deduplication Strategy

All Tier 4 tables use **upsert** on sync:

```sql
-- Example: Upsert workspace_user
INSERT INTO workspace_user (organization_id, provider_user_id, email, full_name, raw_data, last_synced_at)
VALUES ($1, $2, $3, $4, $5, NOW())
ON CONFLICT (organization_id, provider_user_id)
DO UPDATE SET
    email = EXCLUDED.email,
    full_name = EXCLUDED.full_name,
    raw_data = EXCLUDED.raw_data,
    last_synced_at = NOW(),
    updated_at = NOW();
```

---

## Data Flow (from business.md)

```
Reports API (token events)          Directory API (users)
        │                                   │
        ▼                                   ▼
┌─────────────────┐                ┌─────────────────┐
│  discovered_app │                │  workspace_user │
│  (by client_id) │                │ (by provider_id)│
└────────┬────────┘                └────────┬────────┘
         │                                  │
         └──────────┬───────────────────────┘
                    ▼
           ┌─────────────────┐
           │ app_authorization│
           │ (user + app)    │
           └─────────────────┘
```

---

## Key Design Decisions

1. **User belongs to one org directly** - No junction table, simpler for MVP
2. **Role is a separate table** - Allows custom roles later, permissions in JSONB
3. **Plan is a separate table** - Easy to add/modify plans, limits in dedicated columns
4. **Product has no risk data** - Risk assessment is separate (Tier 5)
5. **product_auth_config is generic** - Supports OAuth2, Basic Auth, API Key with clear field naming
6. **Deduplication via unique constraints** - Upsert pattern prevents duplicates
7. **raw_data JSONB** - Store full API response for debugging and future field extraction
8. **Timestamps from API** - `authorized_at` comes from Reports API, not our system

---

## Next: Tier 5, 6

Coming next:
- **Tier 5:** `risk_assessment` (product-level and discovered_app-level risk scores)
- **Tier 6:** `sync_schedule`, `sync_job`, `audit_log`
