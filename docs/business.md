# SaaS Risk Scanner - Business & Technical Documentation

## Executive Summary

SaaS Risk Scanner monitors Google Workspace organizations to detect risky third-party app authorizations. Employees often connect their work accounts to random AI chatbots, MCP servers, and other third-party services—exposing company data. We discover who is doing what and assess the risk.

**Value Proposition:** Your employees are logging into random chatbots and placing the company's data, connecting Google Drives to any random MCP server. We will find it for you—who is doing what.

---

## 1. Google APIs - Core Requirements

### API Strategy

| API | Purpose | Required |
|-----|---------|----------|
| **Reports API** | Get all token authorizations across all users (efficient, single call) | ✅ Primary |
| **Directory API** | List users (metadata, org unit) + revoke tokens | ✅ Supporting |

**Why Reports API is Primary:**
- Single paginated call returns ALL token events across ALL users
- Includes timestamps (when authorized)
- More efficient than N+1 calls with Directory API tokens.list
- Supports real-time alerts via `activities.watch`

**Trade-off:** Reports API only has 180 days of data. Apps authorized before that won't appear unless we do an initial Directory API crawl.

---

### 1.1 Reports API - Token Activity (PRIMARY)

**Purpose:** Get all third-party app authorizations across all users in a single efficient call.

**Official Documentation:**
- Overview: https://developers.google.com/admin-sdk/reports/v1/guides
- Token Activity: https://developers.google.com/admin-sdk/reports/v1/guides/manage-audit-tokens
- API Reference: https://developers.google.com/admin-sdk/reports/v1/reference/activities/list
- Limits & Quotas: https://developers.google.com/admin-sdk/reports/v1/limits

**Required OAuth Scope:**
```
https://www.googleapis.com/auth/admin.reports.audit.readonly
```

#### Primary Endpoint: Get All Token Events
```http
GET https://admin.googleapis.com/admin/reports/v1/activity/users/all/applications/token
```

**Query Parameters:**
- `customerId` - Use `my_customer` (auto-resolves to your org)
- `startTime` / `endTime` - RFC 3339 format (e.g., `2024-01-01T00:00:00.000Z`)
- `maxResults` - Results per page (max 1000)
- `pageToken` - For pagination
- `eventName` - Filter: `authorize`, `revoke`
- `filters` - Filter by specific parameters

**Event Types:**
| Event Name | Description |
|------------|-------------|
| `authorize` | User granted access to a third-party app |
| `revoke` | Access revoked for an application |

**Response Structure:**
```json
{
  "kind": "admin#reports#activities",
  "items": [
    {
      "id": { "time": "2024-11-27T10:30:00.000Z" },
      "actor": {
        "email": "employee@company.com",
        "profileId": "12345"
      },
      "events": [
        {
          "name": "authorize",
          "parameters": [
            { "name": "app_name", "value": "Suspicious AI Chatbot" },
            { "name": "client_id", "value": "123456789.apps.googleusercontent.com" },
            { "name": "scope", "multiValue": [
              "https://www.googleapis.com/auth/drive.readonly",
              "https://www.googleapis.com/auth/gmail.read"
            ]},
            { "name": "client_type", "value": "WEB" }
          ]
        }
      ]
    }
  ],
  "nextPageToken": "..."
}
```

**Key Data Points Returned:**
| Field | Description |
|-------|-------------|
| `actor.email` | Which user authorized the app |
| `id.time` | When the authorization happened |
| `app_name` | Display name of the third-party app |
| `client_id` | OAuth client ID (unique identifier) |
| `scope` | Array of OAuth scopes granted |
| `client_type` | WEB, NATIVE_ANDROID, NATIVE_IOS, NATIVE_DESKTOP |

**Rate Limits & Quotas:**
| Limit Type | Value |
|------------|-------|
| Queries per minute per user | 2,400 |
| Filter queries per minute | 250 |
| Maximum results per page | 1,000 |
| **Data retention** | **180 days** |

#### Real-time Monitoring (Optional)
```http
POST https://admin.googleapis.com/admin/reports/v1/activity/users/all/applications/token/watch
```
Set up push notifications for new token events.

---

### 1.2 Directory API - Users, Groups & Token Revocation (SUPPORTING)

**Purpose:** 
1. Get user metadata (name, org unit, admin status)
2. Map users to teams/groups for risk segmentation
3. Revoke app access when needed
4. Initial crawl for apps authorized >180 days ago

**Official Documentation:**
- Users Resource: https://developers.google.com/admin-sdk/directory/v1/reference/users
- Groups Resource: https://developers.google.com/admin-sdk/directory/v1/reference/groups
- Tokens Resource: https://developers.google.com/admin-sdk/directory/v1/reference/tokens

**Required OAuth Scopes:**
```
https://www.googleapis.com/auth/admin.directory.user.readonly
https://www.googleapis.com/auth/admin.directory.group.readonly
https://www.googleapis.com/auth/admin.directory.user.security
```

#### Endpoint 1: List All Users
```http
GET https://admin.googleapis.com/admin/directory/v1/users?customer=my_customer
```

**Response includes:** User email, name, org unit, admin status, 2FA status

#### Endpoint 2: List Groups & Members
**Purpose:** Map users to teams/departments for risk segmentation.

```http
GET https://admin.googleapis.com/admin/directory/v1/groups?customer=my_customer
GET https://admin.googleapis.com/admin/directory/v1/groups/{groupKey}/members
```

#### Endpoint 3: Revoke App Access
```http
DELETE https://admin.googleapis.com/admin/directory/v1/users/{userKey}/tokens/{clientId}
```

#### Endpoint 4: List User Tokens (Initial Crawl Only)
```http
GET https://admin.googleapis.com/admin/directory/v1/users/{userKey}/tokens
```
Use this once during initial setup to catch apps authorized >180 days ago.

---

### 1.3 API Comparison

| Capability | Reports API | Directory API |
|------------|-------------|---------------|
| Get all apps (efficient) | ✅ Single call | ❌ N+1 calls |
| User who authorized | ✅ | ✅ |
| App name | ✅ | ✅ |
| Scopes granted | ✅ | ✅ |
| Client ID | ✅ | ✅ |
| **When authorized** | ✅ | ❌ |
| **Historical events** | ✅ (180 days) | ❌ |
| **Real-time alerts** | ✅ (watch) | ❌ |
| Revoke capability | ❌ | ✅ |
| User metadata | ❌ | ✅ |
| Apps >180 days old | ❌ | ✅ |

---

## 2. OAuth Scopes Strategy

### 2.1 User SSO Login (Minimal Scopes)

When users sign up/sign in to our platform:

```
openid
email
profile
```

**Purpose:** Only authenticate the user and get their identity. No access to their organizational data.

### 2.2 Google Workspace Admin Connection (MVP Scopes)

When an admin connects their organization:

```
https://www.googleapis.com/auth/admin.reports.audit.readonly
https://www.googleapis.com/auth/admin.directory.user.readonly
https://www.googleapis.com/auth/admin.directory.user.security
```

**What these provide:**
| Scope | Capability |
|-------|------------|
| `admin.reports.audit.readonly` | Get all token events (who authorized what, when) |
| `admin.directory.user.readonly` | List all users in the workspace |
| `admin.directory.user.security` | Revoke OAuth tokens |

**Requirements:**
- User must be a Google Workspace **Super Admin** OR have **Reports Administrator** + **User Management Administrator** roles
- For background sync: Domain-wide delegation must be configured

### 2.3 Scope Sensitivity Warning

The `admin.directory.user.security` scope is marked as **"sensitive"** by Google. Production apps may require:
- Google OAuth verification
- Security assessment for sensitive scopes

---

## 3. User Experience Flow

### 3.1 Onboarding Journey

#### Step 1: Sign Up / Sign In
- User clicks "Sign in with Google"
- OAuth consent with minimal scopes (`openid`, `email`, `profile`)
- User lands on empty dashboard with onboarding prompt

#### Step 2: Connect Google Workspace
- Dashboard shows prominent "Connect your Google Workspace" CTA
- Explains what data will be accessed and why
- User clicks → Redirected to Google OAuth
- Requests admin scopes (reports, directory)
- **User must be a Workspace Admin**
- After consent → Redirected back to dashboard

#### Step 3: Initial Discovery (Background Process)
1. **Reports API** → Fetch all token events (last 180 days) in single paginated call
2. **Directory API** → Fetch user list (for metadata: name, org unit, admin status)
3. **(Optional)** Directory API `tokens.list` per user for apps authorized >180 days ago
4. Build inventory of all third-party apps with:
   - App name
   - Which users authorized it
   - What scopes (permissions) it has
   - When it was authorized

#### Step 4: AI Risk Analysis (Background Process)
For each discovered third-party app:
1. Identify app website from OAuth client info
2. Scrape their website
3. Locate and analyze privacy policy
4. Check compliance certifications (SOC2, GDPR, ISO 27001)
5. Analyze data handling practices
6. Assign risk score (1-100)

#### Step 5: Dashboard Populated
- User sees complete list of discovered apps
- Which employees authorized which apps
- What data access (scopes) each app has
- Actionable recommendations

### 3.2 Dashboard Views

#### Main Dashboard
- **Summary Cards:**
  - Total apps discovered
  - High/Medium/Low risk distribution
  - New authorizations (last 7 days)
  - Users with risky apps
- **Recent Activity Feed:**
  - New app authorizations
  - Revocations
  - Suspicious logins
- **Top Risky Apps Widget**

#### Apps List View
| Column | Description |
|--------|-------------|
| App Name | Name and icon (if available) |
| Risk Score | 1-100 with color indicator |
| Users | Number of employees who authorized |
| Scopes | Drive, Gmail, Calendar, etc. |
| Privacy Rating | Based on policy analysis |
| Compliance | SOC2, GDPR badges or warnings |
| Actions | View details, Alert users |

#### User Activity View
- List of employees
- Apps each employee has authorized
- Login activity (locations, devices, times)
- Risk flags per user
- Filter by department/OU

#### App Detail View
- Full privacy policy analysis
- Complete list of users who authorized
- Exact OAuth scopes granted with explanations
- Website security analysis (HTTPS, security headers)
- Company information (founded, location, size)
- Compliance documentation links
- Recommendations and action items

---

## 4. Implementation Requirements

### 4.1 Google Cloud Project Setup

1. **Create Project**
   - Go to https://console.cloud.google.com/
   - Create new project: "SaaS Risk Scanner"

2. **Enable APIs**
   - Admin SDK API
   - Cloud Identity API (optional)
   - Alert Center API (optional)

3. **Configure OAuth Consent Screen**
   - User Type: External (for customers to authorize)
   - App name, logo, support email
   - Add all required scopes
   - Submit for verification (required for sensitive scopes)

4. **Create OAuth Credentials**
   - Type: Web application
   - Authorized redirect URIs: Your callback URLs

### 4.2 Domain-Wide Delegation (For Background Sync)

For service account to sync data without user interaction:

1. **Create Service Account**
   - IAM & Admin → Service Accounts
   - Generate JSON key file

2. **Enable Domain-Wide Delegation**
   - In service account details, enable delegation
   - Copy the Client ID

3. **Customer Admin Console Configuration**
   Customer must:
   - Go to Admin Console → Security → Access and data control → API controls
   - Click "Manage Domain Wide Delegation"
   - Add new client with:
     - **Client ID:** Service account's client ID
     - **Scopes:** Comma-separated list of required scopes

### 4.3 Required Admin Roles

For the admin connecting their workspace:
- **Super Administrator** (full access), OR
- **Reports Administrator** + **User Management Administrator** + **Security Settings Administrator**

---

## 5. API Usage Summary (MVP)

| Use Case | API | Endpoint | Required Scope |
|----------|-----|----------|----------------|
| User SSO login | Google OAuth | Standard OAuth flow | `openid email profile` |
| **Get all app authorizations** | Reports API | `applications/token` | `admin.reports.audit.readonly` |
| List all domain users | Directory API | `users.list` | `admin.directory.user.readonly` |
| Revoke app access | Directory API | `tokens.delete` | `admin.directory.user.security` |
| Get old authorizations (>180 days) | Directory API | `tokens.list` | `admin.directory.user.security` |

### Efficiency Comparison

| Approach | API Calls for 500 users | Data |
|----------|------------------------|------|
| ❌ Directory API only | 501 calls (1 + N) | Current state, no timestamps |
| ✅ Reports API primary | 1-2 calls (paginated) | 180 days history + timestamps |

---

## 6. Data Flow Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Admin User    │────▶│  Our Platform    │────▶│  Reports API    │
│  (Workspace)    │     │                  │     │  (Primary)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                        │
                               │                        ▼
                               │                 ┌─────────────────┐
                               │                 │ GET /token      │
                               │                 │ All users, all  │
                               │                 │ apps, timestamps│
                               │                 └─────────────────┘
                               │                        │
                               ▼                        │
                        ┌──────────────────┐            │
                        │  Directory API   │            │
                        │  - users.list    │            │
                        │  - tokens.delete │            │
                        └──────────────────┘            │
                               │                        │
                               ▼                        ▼
                        ┌──────────────────────────────────┐
                        │         Our Database             │
                        │   - Users (email, name, org)     │
                        │   - Apps (client_id, name)       │
                        │   - Authorizations (who, when)   │
                        │   - Scopes per authorization     │
                        └──────────────────────────────────┘
                                       │
                                       ▼
                        ┌──────────────────┐
                        │   AI Agent       │
                        │   - Scrape sites │
                        │   - Analyze      │
                        │   - Score risk   │
                        └──────────────────┘
```

### MVP Data Model

```
Users (from Directory API)
├── email
├── name
├── org_unit
└── is_admin

Apps (from Reports API)
├── client_id (unique)
├── display_name
├── client_type (WEB, NATIVE, etc.)
└── risk_score (from AI)

Authorizations (from Reports API)
├── user_email
├── client_id
├── scopes[]
├── authorized_at (timestamp)
└── is_active (true until revoke event)
```

---

## 7. Key Considerations

### 7.1 MVP Limitations (Directory API Only)
- No timestamp for when apps were authorized
- No historical view (only current state)
- No real-time alerts for new authorizations
- Must poll periodically to detect changes

### 7.2 Phase 2 Benefits (Adding Reports API)
- Get authorization timestamps
- Build activity timeline
- Real-time alerts via `activities.watch`
- Track revocations

### 7.3 Rate Limiting Strategy
- Implement exponential backoff
- Cache user lists (refresh every 6-24 hours)
- Batch token fetches where possible
- Use pagination properly (max 500 users/page)
