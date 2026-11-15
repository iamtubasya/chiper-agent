# Atlassian Marketplace Bug Bounty Pattern

## Program Type
Atlassian Marketplace bounties are part of the **Marketplace Security Bug Bounty Program**.
Target: third-party plugins/apps sold on the Atlassian Marketplace.
Scope is NARROW — typically one plugin URL, NOT the entire vendor's infrastructure.

## Instance Creation (CRITICAL — Blocking Step)
Unlike standard Bugcrowd programs where you get test creds, Atlassian Marketplace bounties require creating your OWN Jira Cloud instance.

### Namespace Rule
- WAJIB: `bugcrowd-test-<bugcrowd-username>.atlassian.net`
- JANGAN buat instance di luar namespace ini
- Plugin diinstall di instance sendiri untuk testing

### Setup Flow
1. Navigate: `https://www.atlassian.com/try` (redirects to products page → click "Try now" on Jira)
   - ⚠️ URL `https://www.atlassian.com/try/cloud` returns 404 (verified 2026-08-27)
   - ⚠️ URL `https://start.atlassian.com/` requires login first → redirects to `id.atlassian.com`
2. Sign up (email atau Google/Microsoft login) — **USER ACTION REQUIRED**
3. Create site with namespace `bugcrowd-test-<username>` (contoh: `bugcrowd-test-BC_USERNAME`)
4. Wait for site to be ready (~2-5 min)
5. Go to Apps → Explore more apps → Search for target plugin
6. Install plugin (free trial)
7. Create test data: issues with links/dependencies, multiple users (admin + regular)

### Browserbase Auth Handoff Pattern (CRITICAL)
Browserbase session ≠ user's local browser. They DON'T share cookies/login state.
When program requires creating an instance on a third-party platform (Atlassian, etc.):

1. **Render signup page** → identify exact form fields + namespace format
2. **Tell user to create instance themselves** — give exact steps + URLs
3. **While user creates instance → run passive recon in parallel:**
   - Marketplace listing, docs, release notes, tech stack
   - GitHub repos, writeups, CVEs
   - Plugin descriptor (`atlassian-connect.json`)
4. **User provides instance URL → immediately start testing**

This handoff is FASTER than trying to authenticate through Browserbase (which may trigger CAPTCHA, email verification, 2FA, etc.). Don't waste time fighting auth — delegate instance creation to user.

### computer_use vs browser_navigate (CRITICAL)
When user provides their instance URL and is already logged in:
- **USE `computer_use`** to drive their actual Chrome desktop — it shares their auth cookies/session
- **DO NOT use `browser_navigate`** — it creates a SEPARATE unauthenticated session (Browserbase headless), so you'll hit login pages
- Exception: if user is NOT logged in, browser_navigate + user login handoff is fine

**Pitfall:** `browser_navigate` to `https://bugcrowd-test-BC_USERNAME.atlassian.net/` → redirects to Atlassian login page. Wasted time. Always ask: "Lo udah login belum?" If yes → `computer_use`.

### Tab Management Pitfall (CRITICAL)
When using `computer_use` on user's Chrome with multiple tabs:
- **DO NOT use address bar navigation** (ctrl+l + type URL + Enter) — it may navigate the WRONG tab or open a new one
- Instead, click in-page navigation elements (links, buttons) within the correct tab
- If you MUST use address bar, first verify which tab is active via `capture` and check the window title / URL
- If user has multiple Atlassian instances in separate tabs, NEVER switch tabs without explicit permission
- `computer_use(action="key", keys="ctrl+l")` requires `delivery_mode="foreground"` on Windows Chrome (background drops keyboard shortcuts)

### Agent Workflow During Setup
While user creates instance, agent proactively:
- Read marketplace listing page (via `browser_navigate`, NOT `web_extract` — Bugcrowd/Atlassian pages 504 on web_extract)
- Extract: plugin key (e.g. `se.findout.plugin.dependency-map`), tech stack, version, release notes
- Check Privacy & Security tab for integration permissions
- Read app documentation (external docs link)
- Check "Known issues" column in scope table
- Search for public repos, writeups, CVEs related to the plugin

## Common Tech Stack
- **Java backend** — risk: XXE, deserialization, SSRF
- **ReactJS frontend** — risk: DOM XSS, hidden API endpoints in bundle, source maps
- **Atlassian Connect/Forge** — plugin framework with specific API patterns

## Attack Surface — Atlassian Plugin Specific

### Cross-Instance Data Leakage (HIGHEST PRIORITY)
Atlassian Marketplace plugins run across many Jira instances. Key test:
- Create 2+ test instances (different namespaces)
- Test if data from instance A leaks to instance B
- Check shared views, export features, API endpoints
- Test plugin's backend servers (if any) for tenant isolation

### Plugin API Endpoints
Atlassian plugins expose REST endpoints under:
- `/rest/devinfo/` — development info
- `/rest/` — plugin-specific REST
- Plugin backend (if Connect app): check app descriptor for endpoints
- Atlassian Connect: check `atlassian-connect.json` for scopes

### Atlassian Cloud Connect URL Patterns (CRITICAL)
Cloud plugins ("Runs on Atlassian") use Connect framework, NOT server/Data Center paths:
- **WRONG:** `/plugins/servlet/dependency-map` → 404 "dead link" (server/Data Center pattern)
- **CORRECT:** Plugin loads as embedded React app (iframe) within Jira interface
- **Access:** Via Jira sidebar (Apps section) or in-page navigation
- **Embedded app container:** `Pane 'Embedded app content for <uuid>'` in accessibility tree
- **Plugin page title pattern:** `"Dependency Map - Available maps - Jira"` (visible in browser tab)
- **Features visible:** Create, Search, Table (Favorite/Name/Layout/Filter/Created by/Created/Changed)
- **React app detection:** `Document 'React App'` role inside the embedded pane

**Recon step:** After plugin loads, capture SOM screenshot → identify all interactive elements (buttons, forms, tables, search fields). These are the primary attack surface for XSS, IDOR, CSRF.

### IDOR in Plugin Features
- Tamper with issue IDs, view IDs, filter IDs
- Test: can user A access user B's dependency maps?
- Check: does the plugin respect Jira's permission model?

### ReactJS Frontend Analysis
- Check for source maps in JS bundles
- Extract hidden API endpoints from React component code
- Look for `dangerouslySetInnerHTML` usage (XSS vector)
- Check client-side authorization logic (easily bypassed)

### SSRF via Plugin Features
- URL import/export features
- Webhook/callback configurations
- External data source connections (Confluence page links, external URLs)

### Java-Specific
- XXE: XML import features (project plans, issue data)
- Deserialization: if plugin deserializes user input
- SSRF: Java URLConnection/HttpClient usage

## Program Rules — Common Exclusions
- **No automated scanners** (nuclei batch, nikto, sqlmap auto-mode) — manual testing only
- **No pivoting/chaining** — one finding = one report
- **No customer data** — test on own instance only
- **Only latest version** eligible for reward
- **No dependency-map.com** or other vendor sites (out of scope)
- **No DoS/DDoS**
- **Missing security headers** auto-reject

## Severity Mapping (Atlassian Marketplace)
- P1 ($1500): Cross-Instance Data Leak, RCE, SQLi, full auth bypass
- P2 ($900): SSRF, Stored XSS, IDOR with data access, XXE
- P3 ($300): CSRF, Reflected XSS, Path Traversal
- P4 ($100): Information disclosure, low-impact logic flaws

## Reporting
- Plain text ONLY (no PDF/DOCX per Bugcrowd rules)
- Include: HTTP requests, reproduction steps, screenshots
- One finding per report (no chaining)
- Submit via Bugcrowd dashboard

## Example: BrizoIT — Atlassian Marketplace Programs (Cloud + Datacenter)
- Apps: Company Calendar for Jira, Work Time Tracking Calendar, Company Calendar Planner, Gantt Suite for Jira
- Both Cloud AND Datacenter deployments in scope
- Gantt Suite Cloud tagged "Website Testing **Javascript**" → JS bundle analysis viable
- Scope rating: 2/4, 31 findings rewarded historically
- CVSS scoring (not VRT) — where discrepancy, CVSS wins
- Specific exclusions: exported calendars/Gantt charts (public by design), admin privileges, admin HTML templates, 15-min JWT cache
- **Cross-Instance Data Leakage = #1 priority target** (explicitly listed as focus area)
- Program transitioned to PUBLIC (from invite-only) — fresh surface, less competition
- Hall of Fame: 11 researchers, top at 100 points
- Key Atlassian-specific exclusions: rate limiting, missing security headers, SSL issues, known library vulns (unless proven exploitable), JWT path/method issues

## Example: FindOut InfoVis — Dependency Map for Jira
- Plugin key: `se.findout.plugin.dependency-map`
- Tech: Java + ReactJS + HTML
- 291 active instances, "Runs on Atlassian" badge
- Version 7.28.0 (Aug 7, 2026) — "Bug fixes and security updates"
- Company: FindOut InfoVis AB (now Prevas InfoVis AB)
- Focus areas explicitly listed: Cross-Instance Data Leakage, RCE, SSRF, XSS, CSRF, SQLi, XXE, IDOR, Path Traversal
- avg payout $100, but P1 = $1500
- Program transitioned to PUBLIC on 2026-08-27 (fresh for new researchers)
- **Privacy & Security (verified by Atlassian, 2026-08-27):**
  - App REST APIs: Claims "does not provide REST APIs" — **VERIFY by testing**, this claim may be inaccurate
  - Integration permissions: Delete issue links, View application roles, View audit logs
  - End-User Data: No data stored outside Atlassian
  - Data residency: Not applicable
  - Compliance: None (no SOC2, ISO27001)
  - GDPR: No (not data controller or processor)
  - Security contact: support@dependency-map.com
  - Hosted on Atlassian infrastructure (Cloud)
