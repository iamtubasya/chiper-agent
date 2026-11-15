# Anonymous fingerprint of exposed self-hosted dev infra (Step 5b)

Subdomain enumeration on an engineering-heavy target routinely surfaces **internal tooling** rather
than product endpoints: code review, source control, CI, monitoring. These are the interesting hosts
because they are usually less hardened than the product, and several leak version/config to
*anonymous* callers. This is a Step 5/6 companion: verify each one with a single unauthenticated
request before writing a sentence about it.

**Golden rule:** the first pass tells you (a) it is reachable, (b) what product+version it is, (c)
whether it is already behind an identity-aware proxy. Those three decide whether it is a finding.
Confirm the same hosts the *product* protects are actually protected — an IAP/VPN-fronted control
next to an open one is the finding (see "comparison framing" below).

## Product → anonymous fingerprint endpoint

| Product | One-request fingerprint |
|---|---|
| **Gerrit** | `GET /config/server/version` → `)]}' "3.9.11"`; `GET /config/server/info` → full server config anonymously (auth_type, plugin list, clone schemes) |
| **GitLab** | `GET /help` → version string; `GET /users/sign_up` → presence of self-registration; `GET /api/v4/projects` → `[]` (anon) or a real list |
| **Bitbucket Data Center** | `GET /rest/api/latest/application-properties` → `{"version":"9.2.1",…}` (unauthenticated) |
| **GitHub Enterprise (GHES)** | `GET /api/v3/meta` → `{"installed_version":"3.20.3"}`; `GET /setup` → management-console state |
| **Grafana** | `GET /api/health`, `/api/frontend/settings` — but check whether every path returns the *same large login HTML* (see IAP tell) |
| **Perforce P4 Code Review** | `GET /` → `P4 Code Review - Login`; `GET /api/` → 401 JSON |
| **Jira DC** | `GET /rest/api/2/serverInfo`; a 502 from a fronting proxy (Caddy) still confirms the backend route |

```bash
# the four that pay off most often
curl -s "https://gerrit.<t>/config/server/version"
curl -s "https://gitlab.<t>/help" | grep -oE '1[0-9]\.[0-9]+\.[0-9]+' | head -1
curl -s "https://bitbucket.<t>/rest/api/latest/application-properties"
curl -s "https://github-test.<t>/api/v3/meta"
```

## GHES management console — check the state, don't assume takeover

An internet-reachable GHES is worth checking properly:

```bash
curl -s "https://<ghes-host>/api/v3/meta"     # version, unauthenticated
curl -s "https://<ghes-host>/setup"           # management console
curl -s "https://<ghes-host>/setup/api/status"
```

- `/setup` returning a page titled **"Setup GitHub Enterprise"** with *"Authentication Required —
  please enter your password to unlock the management console"* = configured, password-gated.
  **Not a takeover.** Report the exposure, not an exploit.
- A genuinely unconfigured appliance shows the first-run wizard with an admin-creation form and
  `/setup/api/status` answering normally → that *is* admin takeover. Read the body before claiming it.
- `/setup/api/status` returning **410 "Management Console API endpoints have been removed"** is the
  normal post-setup response on modern GHES — a configured-instance signal, not an error to chase.

## The IAP tell (do not report a protected service as exposed)

If *every* path — including nonsense ones — returns ~200 KB of `text/html` with
`Server: ESF` / `Server: Google Frontend`, you are reading the **Google Identity-Aware Proxy login
page** after a followed redirect. Same for `302 → *.cloudflareaccess.com/cdn-cgi/access/login`.
Classify as protected-and-moved-on. On one target `grafana`, `atlantis`, `ops` and `kb-git` were all
correctly behind IAP while their siblings were open — that contrast is the point.

## Comparison framing (this is what makes it reportable)

Version disclosure alone is usually auto-closed. The finding is the **exposure of non-production
systems**, with version disclosure as supporting detail:

- state that the same class of system is correctly IAP/VPN-fronted elsewhere in the estate
  (naming them), so the open ones are demonstrably inconsistent
- give the anonymous evidence for each host (the exact endpoint + response)
- note dev/QA/staging instances lag patches and carry weaker auth
- explicitly record what you did **not** touch: no credentials attempted, no auth content accessed,
  no setup/management flow completed. Anonymous `{}`/`[]` from Gerrit means it is correctly gated —
  say so, it demonstrates you were thorough and not destructive.

## Pitfalls

- `curl` returning `000` on a Cloudflare-fronted host while a scripted client succeeds is an
  **egress/tunnel** symptom, not a target finding — check the tunnel/egress status, then fall back
  to a different HTTP client (raw sockets / a scripted `urllib` client) and move on. Do not record
  it as "target blocks us".
- A 401/403 with a *product-specific* body (JSON error, Apache version banner) still fingerprints the
  product — a 401 is not "nothing there".
- Don't count an SPA catch-all as a hit: if `/`, `/api/`, `/.env` and `/.git/config` all return the
  identical byte size, that is one page, not four exposures.
