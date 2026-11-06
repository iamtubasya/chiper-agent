# SSRF via "self-hosted connector" domain validation (SaaS integration platforms)

Class-level pattern: any SaaS that lets users connect a **self-hosted / on-premise** version of a
third-party tool (Jira Server, self-hosted GitLab, GitHub Enterprise, self-hosted Jenkins, etc.) has
the user type in a base URL. The backend then "validates" that URL by making an outbound request to
it. That outbound request is the SSRF.

Confirmed on Unito (app.unito.io → `POST /api/v1/authenticate/{provider}/validate_domain`,
2026-11-03). The mechanism generalises.

## Endpoints

- `POST /api/v1/authenticate/{provider}/validate_domain`   body `{"domain":"<url>"}`
- `POST /api/v1/authenticate/{provider}/test_connection`   body `{"domain":"<url>","selfSignedCertificate":""}`
- `{provider}` = self-hosted connector slug: `jira`, `jiraservicedeskserver`, `gitlab`, `ghe`.

## What the backend fetches (provider-specific probe paths)

- jira  → `GET /rest/api/2/serverInfo`
- gitlab → `GET /api/v4/version`
- ghe   → `GET /api/v3/`

These show up verbatim in the OOB listener — proof AND fingerprint of each connector.

## Behaviors / oracle

- `domain` is normalised to `https://` (explicit `http://` and `:port` are stripped; target is port 443).
- Response is **semi-blind**: no response body echo, but `internalMessage` leaks `statusCode` and the
  Node.js error (e.g. `connect ECONNREFUSED 127.0.0.1:443 (ECONNREFUSED)`), usable as a reachability oracle.
- Loopback and RFC1918 are NOT filtered: `127.0.0.1`/`localhost` → ECONNREFUSED (host reached),
  `192.168.1.1`/`169.254.169.254` → hang (connection attempted, no listener).
- `metadata.google.internal` → `"domain is invalid"` (DNS-level reject only; not an IP blocklist).
- `@` userinfo trick (`<oob>@169.254.169.254`) can redirect the connection to an internal host — test it.
- `test_connection` with `selfSignedCertificate:""` returns `{"valid":true}` for arbitrary reachable hosts.

## Discovery tip

"Enter your <tool> URL" input + `validate_domain`/`test_connection` in the minified bundle = this bug.
Also enumerate required JSON fields by sending `{}` and reading successive
`"must have required property '<X>'"` OpenAPI validation errors.

## Severity note

Typically High (authenticated-only, semi-blind, https-only). Escalate to Critical only if you can make
the backend read a full response (response echo, `http://` scheme honoured, or a path you can reflect).