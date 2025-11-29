# Platform Signup & Authentication

## Overview

This document defines the technical requirements for user signup/signin functionality using Google OAuth. Users authenticate via Google SSO, and the platform issues JWT tokens for subsequent API calls.

**Key Constraints:**
- Google OAuth 2.0 only (no email/password)
- Company emails only — personal email providers (gmail.com, outlook.com, etc.) are blocked
- Minimal OAuth scopes: `openid`, `email`, `profile`
- JWT-based stateless authentication

---

## Authentication Flow

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              SIGNUP / SIGNIN FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────▶│ Backend  │────▶│  Google  │────▶│ Backend  │────▶│  Client  │
│ (React)  │     │  /auth/  │     │  OAuth   │     │ Callback │     │ (JWT)    │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                │                │                │
     │  1. Click      │                │                │                │
     │  "Sign in      │                │                │                │
     │   with Google" │                │                │                │
     │───────────────▶│                │                │                │
     │                │                │                │                │
     │  2. Return     │                │                │                │
     │  Google OAuth  │                │                │                │
     │  URL           │                │                │                │
     │◀───────────────│                │                │                │
     │                │                │                │                │
     │  3. Redirect   │                │                │                │
     │  to Google     │                │                │                │
     │────────────────────────────────▶│                │                │
     │                │                │                │                │
     │                │                │  4. User       │                │
     │                │                │  consents      │                │
     │                │                │                │                │
     │                │                │  5. Redirect   │                │
     │                │                │  with code     │                │
     │                │                │───────────────▶│                │
     │                │                │                │                │
     │                │                │                │  6. Validate   │
     │                │                │                │  domain        │
     │                │                │                │  Create/Login  │
     │                │                │                │  user          │
     │                │                │                │                │
     │                │                │                │  7. Return     │
     │                │                │                │  JWT tokens    │
     │◀───────────────────────────────────────────────────────────────────│
     │                │                │                │                │
```

### Detailed API Flow with Request/Response

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: User clicks "Sign in with Google" on SignInPage.tsx                        │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Frontend (React)                           Backend (FastAPI)                        │
│  ─────────────────                          ──────────────────                       │
│                                                                                      │
│  GET /api/v1/auth/google                                                             │
│  ┌─────────────────────────────────┐                                                 │
│  │ Query Params:                   │                                                 │
│  │   redirect_uri: string          │   ◀── Frontend callback URL                    │
│  │   (e.g., http://localhost:5173  │       (where frontend handles OAuth result)    │
│  │          /auth/callback)        │                                                 │
│  └─────────────────────────────────┘                                                 │
│                    │                                                                 │
│                    ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ Backend Actions:                                                             │    │
│  │ 1. Validate redirect_uri is in ALLOWED_REDIRECT_URIS                        │    │
│  │ 2. Generate random state token (CSRF protection)                            │    │
│  │ 3. Store state → {provider_slug, frontend_redirect_uri} in memory           │    │
│  │ 4. Build Google OAuth URL with:                                             │    │
│  │    - client_id (from DB/env)                                                │    │
│  │    - redirect_uri = GOOGLE_REDIRECT_URI (backend callback!)                 │    │
│  │    - scope = "openid email profile"                                         │    │
│  │    - state = generated state token                                          │    │
│  │    - response_type = "code"                                                 │    │
│  │    - access_type = "offline"                                                │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                    │                                                                 │
│                    ▼                                                                 │
│  Response (200):                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ {                                                                            │    │
│  │   "data": {                                                                  │    │
│  │     "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?      │    │
│  │       client_id=xxx&                                                         │    │
│  │       redirect_uri=http://localhost:8000/api/v1/auth/google/callback&        │    │
│  │       scope=openid%20email%20profile&                                        │    │
│  │       state=abc123...&                                                       │    │
│  │       response_type=code&                                                    │    │
│  │       access_type=offline"                                                   │    │
│  │   }                                                                          │    │
│  │ }                                                                            │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Frontend redirects user to Google                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Frontend executes:                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ window.location.href = response.data.authorization_url                       │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  User browser navigates to Google OAuth consent screen                              │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: User consents at Google                                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Google OAuth shows:                                                                 │
│  - App name requesting access                                                        │
│  - Requested permissions (email, profile)                                            │
│  - User clicks "Allow"                                                               │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Google redirects to BACKEND callback                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  Google redirects user's browser to:                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ http://localhost:8000/api/v1/auth/google/callback                            │    │
│  │   ?code=4/0AX4XfWh...                  ◀── Authorization code from Google   │    │
│  │   &state=abc123...                     ◀── Same state we sent earlier       │    │
│  │   &scope=openid%20email%20profile                                           │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  ⚠️  IMPORTANT: This is the GOOGLE_REDIRECT_URI that must be configured in          │
│      Google Cloud Console under "Authorized redirect URIs"                           │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Backend handles callback                                                    │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  GET /api/v1/auth/google/callback                                                    │
│  ┌─────────────────────────────────┐                                                 │
│  │ Query Params:                   │                                                 │
│  │   code: string                  │   ◀── Authorization code from Google           │
│  │   state: string                 │   ◀── CSRF state token                         │
│  └─────────────────────────────────┘                                                 │
│                    │                                                                 │
│                    ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ Backend Actions:                                                             │    │
│  │ 1. Validate & consume state token (CSRF check)                              │    │
│  │ 2. Exchange code for tokens with Google:                                    │    │
│  │    POST https://oauth2.googleapis.com/token                                 │    │
│  │    {code, client_id, client_secret, redirect_uri, grant_type}               │    │
│  │    → Returns: access_token, id_token, refresh_token                         │    │
│  │ 3. Decode id_token to get user info (email, name, picture, sub)             │    │
│  │ 4. Validate email domain is NOT in blocklist                                │    │
│  │ 5. Create/update user and organization in database                          │    │
│  │ 6. Generate JWT tokens (access_token + refresh_token)                       │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                    │                                                                 │
│                    ▼                                                                 │
│  Response (200 - Success):                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ {                                                                            │    │
│  │   "data": {                                                                  │    │
│  │     "access_token": "eyJhbGciOiJIUzI1NiIs...",                               │    │
│  │     "refresh_token": "eyJhbGciOiJIUzI1NiIs...",                              │    │
│  │     "token_type": "Bearer",                                                  │    │
│  │     "expires_in": 3600,                                                      │    │
│  │     "user": {                                                                │    │
│  │       "id": 1,                                                               │    │
│  │       "email": "john@acme.com",                                              │    │
│  │       "full_name": "John Doe",                                               │    │
│  │       "avatar_url": "https://lh3.googleusercontent.com/...",                 │    │
│  │       "role": { "id": 1, "name": "owner" },                                  │    │
│  │       "organization": { "id": 1, "name": "Acme", "slug": "acme-x7k2" }       │    │
│  │     },                                                                       │    │
│  │     "is_new_user": true                                                      │    │
│  │   }                                                                          │    │
│  │ }                                                                            │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
│  Response (400 - Invalid Domain):                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ {                                                                            │    │
│  │   "error": {                                                                 │    │
│  │     "code": "INVALID_EMAIL_DOMAIN",                                          │    │
│  │     "message": "Personal email addresses are not allowed."                   │    │
│  │   }                                                                          │    │
│  │ }                                                                            │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Frontend receives tokens at OAuthCallbackPage.tsx                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  The frontend OAuthCallbackPage receives the response and:                           │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │ 1. Extracts code & state from URL params                                     │    │
│  │ 2. Calls: GET /api/v1/auth/google/callback?code=xxx&state=yyy               │    │
│  │ 3. Receives JWT tokens + user data                                          │    │
│  │ 4. Stores tokens in AuthContext (memory/localStorage)                       │    │
│  │ 5. Redirects to /dashboard or saved destination                             │    │
│  └─────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Environment Variables

| Variable | Example Value | Purpose |
|----------|---------------|---------|
| `GOOGLE_REDIRECT_URI` | `http://localhost:8000/api/v1/auth/google/callback` | **Configure this in Google Cloud Console!** Backend callback URL that Google redirects to |
| `ALLOWED_REDIRECT_URIS` | `http://localhost:5173/auth/callback` | Frontend callback URLs (validated by backend, NOT sent to Google) |
| `GOOGLE_CLIENT_ID` | `xxx.apps.googleusercontent.com` | OAuth client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-xxx` | OAuth client secret from Google Cloud Console |

### Google Cloud Console Configuration

In Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs:

**Authorized JavaScript origins:**
```
http://localhost:5173
http://localhost:8000
```

**Authorized redirect URIs:**
```
http://localhost:8000/api/v1/auth/google/callback
```

⚠️ **Important:** The redirect URI registered in Google Cloud Console must **exactly match** `GOOGLE_REDIRECT_URI` in your backend `.env` file.

---

## Domain Validation

### Blocked Email Domains

Personal and disposable email providers are **blocked**. Maintain a blocklist in `constants/blocked_domains.py`:

```python
BLOCKED_EMAIL_DOMAINS = {
    # Major personal email providers
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "yahoo.com",
    "yahoo.co.uk",
    "ymail.com",
    "aol.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "protonmail.com",
    "proton.me",
    "zoho.com",
    "mail.com",
    "gmx.com",
    "gmx.net",
    
    # Disposable email providers
    "yopmail.com",
    "tempmail.com",
    "guerrillamail.com",
    "mailinator.com",
    "10minutemail.com",
    "throwaway.email",
    "fakeinbox.com",
    "sharklasers.com",
    "trashmail.com",
}
```

### Validation Logic

```python
def is_valid_company_domain(email: str) -> bool:
    domain = email.split("@")[1].lower()
    return domain not in BLOCKED_EMAIL_DOMAINS
```

---

## API Endpoints

### 1. Initiate Google OAuth

**Endpoint:** `GET /api/v1/auth/google`

Generates the Google OAuth URL for the client to redirect to.

**Request:**
```
GET /api/v1/auth/google?redirect_uri=https://app.example.com/auth/callback
```

| Query Param | Type | Required | Description |
|-------------|------|----------|-------------|
| `redirect_uri` | string | Yes | Where to redirect after OAuth (must be allowlisted) |

**Response (200):**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": {
    "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&scope=openid%20email%20profile&response_type=code&state=..."
  },
  "error": null
}
```

**Implementation Notes:**
- Generate a random `state` parameter and store in Redis/memory (5 min TTL) for CSRF protection
- Scopes: `openid email profile`

---

### 2. Google OAuth Callback

**Endpoint:** `GET /api/v1/auth/google/callback`

Handles the OAuth callback from Google, validates the user, and issues JWT tokens.

**Request:**
```
GET /api/v1/auth/google/callback?code=...&state=...
```

| Query Param | Type | Required | Description |
|-------------|------|----------|-------------|
| `code` | string | Yes | Authorization code from Google |
| `state` | string | Yes | State parameter for CSRF validation |

**Response (200) — Successful Authentication:**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": 1,
      "email": "john@acme.com",
      "full_name": "John Doe",
      "avatar_url": "https://lh3.googleusercontent.com/...",
      "email_verified": true,
      "status": "active",
      "role": {
        "id": 1,
        "name": "owner",
        "display_name": "Owner"
      },
      "organization": {
        "id": 1,
        "name": "Acme Corp",
        "slug": "acme-corp",
        "domain": "acme.com",
        "status": "pending_setup",
        "plan": {
          "id": 1,
          "name": "free",
          "display_name": "Free"
        }
      }
    },
    "is_new_user": true
  },
  "error": null
}
```

**Error Response (400) — Invalid Email Domain:**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": null,
  "error": {
    "code": "INVALID_EMAIL_DOMAIN",
    "message": "Personal email addresses are not allowed. Please use your company email.",
    "target": "email",
    "details": [
      {
        "field": "email",
        "value": "john@gmail.com",
        "reason": "gmail.com is a personal email provider"
      }
    ]
  }
}
```

**Error Response (400) — User Suspended:**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": null,
  "error": {
    "code": "USER_SUSPENDED",
    "message": "Your account has been suspended. Please contact your administrator.",
    "target": "user",
    "details": null
  }
}
```

---

### 3. Refresh Access Token

**Endpoint:** `POST /api/v1/auth/refresh`

Issues a new access token using a valid refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600
  },
  "error": null
}
```

**Error Response (401) — Invalid/Expired Refresh Token:**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": null,
  "error": {
    "code": "INVALID_REFRESH_TOKEN",
    "message": "Refresh token is invalid or expired. Please sign in again.",
    "target": "refresh_token",
    "details": null
  }
}
```

---

### 4. Get Current User

**Endpoint:** `GET /api/v1/auth/me`

Returns the currently authenticated user's profile.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200):**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": {
    "id": 1,
    "email": "john@acme.com",
    "full_name": "John Doe",
    "avatar_url": "https://lh3.googleusercontent.com/...",
    "email_verified": true,
    "status": "active",
    "last_login_at": "2025-11-28T10:00:00Z",
    "role": {
      "id": 1,
      "name": "owner",
      "display_name": "Owner",
      "permissions": {"all": true}
    },
    "organization": {
      "id": 1,
      "name": "Acme Corp",
      "slug": "acme-corp",
      "domain": "acme.com",
      "logo_url": null,
      "status": "pending_setup",
      "plan": {
        "id": 1,
        "name": "free",
        "display_name": "Free",
        "max_users": 5,
        "max_apps": 50
      }
    }
  },
  "error": null
}
```

---

### 5. Logout

**Endpoint:** `POST /api/v1/auth/logout`

Invalidates the current refresh token.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**
```json
{
  "meta": {
    "request_id": "01HX...",
    "timestamp": "2025-11-28T10:00:00Z"
  },
  "data": {
    "message": "Successfully logged out"
  },
  "error": null
}
```

---

## Business Logic

### Flow 1: New User Signup (First User from Domain)

When a user signs up and no organization exists for their email domain:

```
1. Exchange code for tokens with Google
2. Get user info from Google (email, name, picture, provider_id)
3. Validate email domain is NOT in blocklist → fail if blocked
4. Check if user exists by provider_id → if yes, go to Flow 2
5. Check if organization exists for domain → if no:
   a. Create organization:
      - name: Derive from domain (e.g., "acme.com" → "Acme")
      - slug: Generate from domain + random suffix (e.g., "acme-x7k2")
      - domain: Extract from email
      - plan_id: Get 'free' plan ID
      - status: 'pending_setup'
      - subscription_status: 'trialing'
      - trial_ends_at: NOW() + 14 days
   b. Create user:
      - organization_id: New org ID
      - role_id: Get 'owner' role ID
      - email: From Google
      - full_name: From Google
      - avatar_url: From Google picture
      - provider_id: From Google
      - email_verified: From Google
      - status: 'active'
      - joined_at: NOW()
      - last_login_at: NOW()
6. Generate JWT tokens
7. Return response with is_new_user: true
```

### Flow 2: Existing User Login

When a user signs in and already exists:

```
1. Exchange code for tokens with Google
2. Get user info from Google
3. Validate email domain → fail if blocked
4. Find user by provider_id
5. Check user status:
   - 'suspended' or 'deactivated' → return USER_SUSPENDED error
   - 'pending_invitation' → update to 'active', set joined_at
   - 'active' → continue
6. Update user:
   - last_login_at: NOW()
   - full_name: From Google (in case changed)
   - avatar_url: From Google (in case changed)
   - email_verified: From Google
7. Generate JWT tokens
8. Return response with is_new_user: false
```

### Flow 3: Invited User First Login

When an invited user (status: 'pending_invitation') signs in:

```
1. Exchange code for tokens with Google
2. Get user info from Google
3. Validate email domain → fail if blocked
4. Find user by email (they exist from invitation)
5. Validate user's email domain matches organization domain
6. Update user:
   - provider_id: Set from Google
   - status: 'active'
   - joined_at: NOW()
   - last_login_at: NOW()
   - full_name: From Google
   - avatar_url: From Google
   - email_verified: From Google
7. Generate JWT tokens
8. Return response with is_new_user: false
```

---

## JWT Token Structure

### Access Token

**Expiry:** 1 hour

**Payload:**
```json
{
  "sub": "1",
  "type": "access",
  "user_id": 1,
  "org_id": 1,
  "role": "owner",
  "email": "john@acme.com",
  "iat": 1732788000,
  "exp": 1732791600
}
```

### Refresh Token

**Expiry:** 7 days

**Payload:**
```json
{
  "sub": "1",
  "type": "refresh",
  "user_id": 1,
  "jti": "unique-token-id",
  "iat": 1732788000,
  "exp": 1733392800
}
```

### Token Configuration

| Setting | Value | Environment Variable |
|---------|-------|---------------------|
| Algorithm | HS256 | - |
| Access Token Expiry | 3600 seconds (1 hour) | `ACCESS_TOKEN_EXPIRE_SECONDS` |
| Refresh Token Expiry | 604800 seconds (7 days) | `REFRESH_TOKEN_EXPIRE_SECONDS` |
| Secret Key | 256-bit random | `JWT_SECRET_KEY` |

---

## Pydantic Schemas

### Request Schemas

```python
# schemas/auth_schema.py

class GoogleAuthRequest(BaseModel):
    redirect_uri: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str
```

### Response Schemas

```python
# schemas/auth_schema.py

class PlanResponse(BaseModel):
    id: int
    name: str
    display_name: str
    max_users: int | None
    max_apps: int | None

class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    permissions: dict | None = None

class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    domain: str | None
    logo_url: str | None
    status: str
    plan: PlanResponse

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None
    avatar_url: str | None
    email_verified: bool
    status: str
    last_login_at: datetime | None
    role: RoleResponse
    organization: OrganizationResponse

class AuthUrlResponse(BaseModel):
    authorization_url: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_in: int

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
    is_new_user: bool
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_EMAIL_DOMAIN` | 400 | Email domain is personal/disposable |
| `USER_SUSPENDED` | 403 | User account is suspended |
| `USER_DEACTIVATED` | 403 | User account is deactivated |
| `INVALID_OAUTH_STATE` | 400 | OAuth state mismatch (CSRF) |
| `OAUTH_ERROR` | 400 | Error exchanging code with Google |
| `INVALID_ACCESS_TOKEN` | 401 | Access token invalid or expired |
| `INVALID_REFRESH_TOKEN` | 401 | Refresh token invalid or expired |
| `ORGANIZATION_SUSPENDED` | 403 | Organization is suspended |

---

## Implementation File Structure

```
app/
├── api/
│   └── v1/
│       └── auth.py                 # FastAPI router for auth endpoints
├── constants/
│   └── blocked_domains.py          # BLOCKED_EMAIL_DOMAINS set
├── core/
│   ├── config.py                   # Settings (JWT secrets, Google OAuth config)
│   ├── security.py                 # JWT encode/decode, password hashing
│   └── dependencies.py             # get_current_user dependency
├── models/
│   ├── user.py                     # User SQLAlchemy model
│   ├── organization.py             # Organization SQLAlchemy model
│   ├── role.py                     # Role SQLAlchemy model
│   └── plan.py                     # Plan SQLAlchemy model
├── repositories/
│   ├── user_repository.py          # User CRUD operations
│   ├── organization_repository.py  # Organization CRUD operations
│   ├── role_repository.py          # Role CRUD operations
│   └── plan_repository.py          # Plan CRUD operations
├── schemas/
│   └── auth_schema.py              # Pydantic request/response models
├── services/
│   ├── auth_service.py             # Authentication business logic
│   ├── google_oauth_service.py     # Google OAuth handling
│   └── domain_validator.py         # Email domain validation
└── utils/
    └── slug_generator.py           # Organization slug generation
```

---

## Environment Variables

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://api.example.com/api/v1/auth/google/callback

# JWT
JWT_SECRET_KEY=your-256-bit-secret-key
ACCESS_TOKEN_EXPIRE_SECONDS=3600
REFRESH_TOKEN_EXPIRE_SECONDS=604800

# Frontend
FRONTEND_URL=https://app.example.com
ALLOWED_REDIRECT_URIS=https://app.example.com/auth/callback,http://localhost:3000/auth/callback
```

---

## Google OAuth Configuration

### Required Scopes

```
openid
email
profile
```

### Google Cloud Console Setup

1. Create OAuth 2.0 Client ID (Web application)
2. Add authorized redirect URIs:
   - `https://api.example.com/api/v1/auth/google/callback` (production)
   - `http://localhost:8000/api/v1/auth/google/callback` (development)
3. Note the Client ID and Client Secret

### Google User Info Response

```json
{
  "sub": "110248495921238986420",
  "name": "John Doe",
  "given_name": "John",
  "family_name": "Doe",
  "picture": "https://lh3.googleusercontent.com/a/...",
  "email": "john@acme.com",
  "email_verified": true,
  "hd": "acme.com"
}
```

**Note:** The `hd` (hosted domain) field is only present for Google Workspace accounts, not personal Gmail accounts.

---

## Slug Generation

Generate unique organization slugs from the email domain:

```python
# utils/slug_generator.py

import secrets
import re

def generate_org_slug(domain: str) -> str:
    # Extract company name from domain (e.g., "acme.com" → "acme")
    base = domain.split(".")[0]
    
    # Normalize: lowercase, replace non-alphanumeric with hyphen
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    
    # Add random suffix for uniqueness
    suffix = secrets.token_hex(2)  # 4 characters
    
    return f"{base}-{suffix}"
```

**Examples:**
- `acme.com` → `acme-x7k2`
- `my-company.io` → `my-company-a3b1`
- `startup.co.uk` → `startup-f9d2`

---

## Security Considerations

1. **CSRF Protection:** Use `state` parameter in OAuth flow, validate on callback
2. **Token Storage:** Store refresh tokens in httpOnly cookies (frontend) or secure storage
3. **Token Rotation:** Issue new refresh token on each refresh (optional, adds security)
4. **Rate Limiting:** Limit OAuth initiation to 10 requests/minute per IP
5. **Redirect URI Validation:** Only allow pre-configured redirect URIs
6. **HTTPS Only:** All auth endpoints must use HTTPS in production
