# SSRF via self-hosted connector "domain validation" (SaaS)

Learned on unito.io (VDP), 2026-11-03. A SaaS that syncs work between tools lets you
connect an on-prem / self-hosted version of a tool (Jira Server/Data Center, Jira Service
Management Server, self-managed GitLab, GitHub Server/Enterprise) by typing a URL. The
"validate domain" and "test connection" steps issue a server-side HTTP request to that
URL on Unito's backend — a classic SSRF.

## Endpoints (the shape to look for, not just Unito)

```
POST /api/v1/authenticate/{provider}/validate_domain     body: { "domain": "<url>" }
POST /api/v1/authenticate/{provider}/test_connection     body: { "domain": "<url>", "selfSignedCertificate": "" }
```

- `{provider}` values for self-hosted connectors: `jira`, `jiraservicedeskserver`, `gitlab`, `ghe`.
- OAuth-only connectors do NOT hit this path — only the on-prem/self-hosted ones that take a URL.

## How to confirm (3-step, minimal)

1. Point `domain` at an out-of-band listener you control (interactsh / Burp Collaborator).
2. Observe inbound DNS + HTTP. The backend fetches a provider-specific version probe:
   - `jira`  -> `GET /rest/api/2/serverInfo`
   - `gitlab` -> `GET /api/v4/version`
   - `ghe`   -> `GET /api/v3/`
3. Use the error echo as a scan oracle — it leaks connection state without needing to read a body:
   - `domain=127.0.0.1` -> `connect ECONNREFUSED 127.0.0.1:443` (proves loopback is dialled, not filtered)
   - private IP (192.168.x, 169.254.x) -> request hangs (connection attempted, no quick refusal)
   - `test_connection` with `selfSignedCertificate: ""` -> `{"valid": true}`

## Facts that bound severity (state honestly in the report)

- Scheme is normalised to `https` and port 443: `http://` and `:80` are stripped to `https://`.
- The fetched response BODY is not returned — only diagnostic error strings (`statusCode`, the
  raw connect error). This is a **semi-blind** SSRF, not a read primitive.
- Loopback and RFC1918 addresses are attempted, NOT blocklisted; only DNS-invalid names get
  "domain is invalid". So internal port-scan + egress abuse are real; AWS metadata
  (`169.254.169.254`, HTTP-only on 80) is not directly reachable through the forced https.
- Rate High (not Critical) when semi-blind: AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N ~ 7.7.

## Bonus technique that found it: OpenAPI "required property" oracle

The `POST /authenticate` endpoint returned 400 with
`"identifier":"Maestro OpenAPIValidationError","message":"authenticationTool: must have required property 'authenticationTool'"`.
Feeding the missing key back re-prompted the NEXT missing key — so you can enumerate an endpoint's
full required schema field-by-field by reading the 400 message. Cheap and generally reusable on any
OpenAPI-backed JSON API that echoes validation errors.