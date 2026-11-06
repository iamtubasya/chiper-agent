# Jira Cloud REST API — Unauthenticated Endpoint Map

## Target: Jira Cloud (Atlassian-hosted)
**Instance example:** `bugcrowd-test-BC_USERNAME.atlassian.net`
**Version:** 1001.0.0-SNAPSHOT (Cloud, not self-hosted)

## Unauthenticated Endpoints (200 OK — no auth required)

| Endpoint | Response | Notes |
|----------|----------|-------|
| `/rest/api/2/serverInfo` | Version, build, SCM hash, locale, timezone | Full server fingerprint |
| `/rest/api/2/field` | All field definitions (200+ fields) | Custom field names, types, clauseNames |
| `/rest/api/2/issueLinkType` | Link types | Currently empty `{"issueLinkTypes":[]}` |
| `/rest/api/2/issue/createmeta` | Project list for issue creation | Returns `{"projects":[]}` when no visible projects |
| `/rest/api/2/dashboard` | Dashboard list | Returns `{"dashboards":[]}` when empty |
| `/rest/api/2/status` | Status definitions | Returns `[]` when empty |
| `/rest/api/latest/issue/picker` | Issue picker search | Returns `{"sections":[{"label":"History Search",...}]}` |

## Unauthenticated Endpoints (401 — auth required but leaks behavior)

| Endpoint | Behavior |
|----------|----------|
| `/rest/api/2/myself` | "Client must be authenticated to access this resource." |
| `/rest/api/2/application-properties` | Same message |
| `/rest/api/2/priority` | Same message |
| `/rest/api/2/resolution` | Same message |
| `/rest/api/2/screens` | Same message |
| `/rest/api/2/notificationscheme` | Same message |
| `/rest/api/2/permissionscheme` | Same message |

## Unauthenticated Endpoints (404 — not found)

| Endpoint | Status |
|----------|--------|
| `/rest/api/2/issue/KAN-1` | "Issue does not exist or you do not have permission to see it." |
| `/rest/api/3/issue/KAN-1` | Same verbose error |
| `/rest/api/2/user?username=admin` | "Authentication required to perform this operation." |
| `/rest/api/2/user/picker?query=test` | Returns `{"users":[],"total":0}` — user enumeration endpoint |

## Key Findings

### 1. Information Disclosure — Server Fingerprint (LOW)
`/rest/api/2/serverInfo` exposes: version, build number, build date, SCM hash, deployment type, locale, timezone — **all unauthenticated**. Atlassian considers this by-design for Cloud instances.

### 2. Field Schema Enumeration (LOW)
`/rest/api/2/field` exposes all field definitions including custom fields, their types, and JQL clause names — unauthenticated.

### 3. Organization & Site ID Leak (LOW)
Login redirect URL exposes:
- `orgId=5f75a5b7-3bcc-4433-9795-a10fb804e578`
- Site UUID: `ari:cloud:jira::site/113370cf-dc67-43e3-8480-b46a5a6cd859`

### 4. Verbose Error Messages (INFO)
- JQL errors return detailed syntax guidance unauthenticated
- Non-existent endpoints return Spring Boot format: `{"type":"about:blank","title":"Not Found","status":404}`

### 5. User Picker Endpoint (INFO)
`/rest/api/2/user/picker` is accessible without auth but returns empty results — enumeration possible if users exist.

## Testing Methodology

### Step 1: Endpoint Enumeration
```bash
for ep in "application-properties" "configuration" "dashboard" "field" "issue/createmeta" "issueLinkType" "myself" "notificationscheme" "priority" "resolution" "screens" "status" "statuses" "user" "user/picker" "workflows"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://TARGET/rest/api/2/$ep")
  echo "$ep -> $code"
done
```

### Step 2: Authenticated Testing (requires session)
- Use browser session cookies for authenticated endpoint testing
- Check: issue access across projects (IDOR), webhook SSRF, XSS in custom fields
- Note: Chrome cookies are locked while Chrome is running — use browser console injection instead

### Step 3: Version-Specific Checks
- Jira Cloud v2 API deprecated: `/rest/api/2/search` → use `/rest/api/3/search/jql`
- Check API version migration paths for weaker security controls

## Browser Automation Pitfalls for Jira

### SOM Capture Limitation on Jira Modal Views
When Jira displays an issue in a modal overlay (e.g., clicking KAN-1 from list view), the SOM accessibility tree **only captures browser chrome elements** (title bar, buttons), NOT the page content inside the modal. The vision analysis can see the content but interactive elements are not indexed.

**Workaround:** Use `app=Chrome` without `pid`/`window_id` to capture from the frontmost Chrome window, which sometimes captures the full page. If that fails, fall back to REST API probing via curl.

### Chrome Tab Auto-Switching
Chrome may auto-switch to other tabs (X.com, Immunefi) after certain operations. Always:
1. Re-capture after any action to verify the active tab
2. Navigate back to Jira via address bar if tab switched
3. Use `focus_app` with specific `window_id` to target the Jira window

### Cookie Extraction Blocked
Chrome's SQLite cookie database is locked while Chrome is running. Cannot copy for REST API authentication. Alternatives:
- Use browser console injection (if cua_browser is available)
- Use foreground delivery mode to interact with the page directly
- Fall back to unauthenticated API testing
