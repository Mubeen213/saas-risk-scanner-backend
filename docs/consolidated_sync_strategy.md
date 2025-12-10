# Hybrid Data Sync & Timeline Strategy

## 1. Executive Summary: The Data Integrity Challenge

We are building a system that must provide **100% accurate visibility** into third-party app usage.
This is challenging because:
1.  **Limited History:** Google's Reports API only provides events for the last 180 days. Apps authorized before that are "invisible" to standard event streams.
2.  **State Drift:** Relying solely on event streams is fragile; missed webhooks or API errors cause drift.
3.  **Ghost Apps:** Users may revoke apps we never knew existed (because they were authorized years ago).

### The Solution: "Hybrid Sync"
We will combine two data sources to guarantee accuracy:
1.  **Snapshot (Ground Truth):** Directory API (`tokens.list`) to get the *current* state of every user.
2.  **Stream (Activity Log):** Reports API (`activities.list`) to catch *real-time* changes and build a history timeline.

---

## 2. The Timeline Strategy (The "Life of a Grant")

To show a clear, reliable timeline (e.g., *Authorized -> Accessed -> Revoked -> Re-authorized*), we must separate **Current State** from **Event History**.

### 2.1 The Data Model

*   **`app_grant` (Current State Table):**
    *   Represents the *now*.
    *   One row per User <> App.
    *   Status: `active` or `revoked`.
    *   Columns: `current_scopes`, `last_accessed_at`, `revoked_at`.

*   **`oauth_event` (Immutable Timeline Table):**
    *   Represents the *audit trail*.
    *   Append-only log of every action as a distinct row.
    *   **Crucial:** This is what powers the UI Timeline View.

### 2.2 Reconstructing the Timeline in UI

The UI will fetch `oauth_event` rows for a specific User+App pair, sorted by `event_time ASC`.

**Example Timeline Visualization:**

| Time | Event Type | Description |
| :--- | :--- | :--- |
| **Jan 01, 10:00 AM** | `authorize` | **Authorized** "Zoom" with scopes: `calendar.readonly`. |
| **Jan 15, 02:30 PM** | `activity` | **Accessed API**: `calendar` (via Zoom). |
| **Feb 01, 09:00 AM** | `revoke` | **Revoked** access to "Zoom". |
| **Mar 10, 11:00 AM** | `authorize` | **Re-authorized** "Zoom" with *new* scopes: `calendar.readonly`, `meet.host`. |
| **Mar 10, 11:05 AM** | `activity` | **Accessed API**: `meet` (via Zoom). |

**Note on "Gap" Handling:**
If an app is found via **Snapshot** (active now) but has NO prior events (authorized >180 days ago):
*   System inserts a synthetic "Discovery" event in the timeline:
    *   `event_type`: `imported`
    *   `event_time`: Time of scan
    *   `description`: "Imported from Directory Snapshot (Authorized prior to event log history)"

---

## 3. The Hybrid Sync Workflow

### Phase 1: The "Snapshot" (Initial & Weekly)
*   **Goal:** Establish Ground Truth. Catch "Old Apps".
*   **Source:** Directory API (`tokens.list` for *every* user).
*   **Action:**
    1.  Iterate all active users.
    2.  Fetch their current OAuth tokens.
    3.  **Upsert** to `app_grant` with status `active`.
    4.  *Self-Healing:* If `app_grant` was `revoked` in our DB but appears in this list -> Mark `active` (User re-authorized).

### Phase 2: The "Stream" (Hourly/Daily)
*   **Goal:** Real-time updates and Activity Logs.
*   **Source:** Reports API (`activities.list`).
*   **Action:** Poll for events (`authorize`, `revoke`, `activity`).
    1.  **Authorize Event:** Upsert `app_grant` (`active`). Insert `oauth_event` (`authorize`).
    2.  **Revoke Event:** Update `app_grant` (`revoked`, `revoked_at=NOW`). Insert `oauth_event` (`revoke`).
    3.  **Activity Event:** Update `app_grant` (`last_accessed_at=NOW`). Insert `oauth_event` (`activity`).

---

## 4. Specific Edge Case Handling

### 4.1 The "Ghost Revoke"
*   **Scenario:** We receive a `revoke` event for App X, but we have no record of App X ever being authorized (because it was authorized 2 years ago).
*   **Policy:** **Record it.**
*   **Action:**
    1.  Create `oauth_app` (App X).
    2.  Create `app_grant` (User <> App X) with status `revoked` and `revoked_at` = Event Time.
    3.  Insert `oauth_event` (`revoke`).
*   **Why:** It is valuable intelligence to know a user *was* using a risky app, even if they just stopped.

### 4.2 Scope Expansion
*   **Scenario:** User authorizes App X with "Email Read". Later, authorizes again with "Drive Write".
*   **Policy:** **Union of Scopes.**
*   **Action:**
    1.  `app_grant.scopes` becomes `['email.read', 'drive.write']` (Maximum exposure).
    2.  `oauth_event` for the second authorization records *only* the scopes requested at that moment (for audit granularity).

### 4.3 Google "Noise" Filter
We will maintain a hardcoded **Blocklist** to ignore internal Google OAuth clients that clutter the view.
*   **Ignored Names:** "Android Device Policy", "Google Chrome", "iOS Account Manager", "OS X".
*   **Action:** Filter these *before* database insertion.

---

## 5. Sync Job Tracking (Checkpoints)

To ensure we never miss an event, we track sync state explicitly.

**`crawl_history` Table:**
*   `sync_type`: `snapshot` (Full User Scan) or `stream` (Event Log).
*   `started_at` / `completed_at`.
*   `cursor`: For Stream syncs, we use the `startTime` of the *last successful sync* minus a **10-minute buffer** (to handle eventual consistency / late logs).

---

## 6. Implementation Summary

1.  **Database:** Ensure `oauth_event` table exists and is populated for *every* incoming event.
2.  **Collector Logic:** Implement `SnapshotService` (User Iterator) and `StreamService` (Event Poller).
3.  **Timeline UI:** Query `oauth_event` directly for the "Activity" tab, do not rely on `app_grant` metadata for history.
