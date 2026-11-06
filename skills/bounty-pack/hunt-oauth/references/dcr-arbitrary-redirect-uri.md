# Dynamic Client Registration (RFC 7591) with arbitrary redirect_uri

Case: `api.todoist.com/oauth/register`, found + reported 2026-10-05. Rated Medium
(phishing-assisted account takeover, one consent click required).

## Why this endpoint is worth checking first

OAuth servers increasingly expose unauthenticated DCR so that MCP clients, AI agents and
third-party apps can self-register without a human. That is a deliberate product decision, and it
is easy to get wrong: the registration endpoint gets built, the authorization endpoint keeps its
strict checks, and nobody revisits whether *registration itself* needed a gate.

Grep the target's OAuth discovery document for `registration_endpoint`:

```bash
curl -s https://<target>/.well-known/openid-configuration | jq '{registration_endpoint, scopes_supported, grant_types_supported}'
```

## Is there a gate at all? (the 400-vs-401 test)

Do this **before** creating anything — it proves the missing auth with zero state created:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://api.<target>/oauth/register        # GET -> 405 = POST-only
curl -s -X POST https://api.<target>/oauth/register -H 'Content-Type: application/json' -d '{}'
```

| Response | Meaning |
|---|---|
| `400 "invalid_client_metadata"` (a *validation* error) | No auth gate exists. Continue. |
| `401` / `403` | Gated. Stop — not a finding. |

The reasoning to put in the report: *the endpoint never asks who the caller is, so there is no
authentication step to fail.* A validation error is proof of absence of auth, not proof of a bug —
pair it with the successful registration below.

## The registration that makes it a finding

```bash
curl -s -X POST https://api.<target>/oauth/register \
  -H 'Content-Type: application/json' \
  -d '{"client_name":"poc","redirect_uris":["https://poc.example.com/cb"]}' -D -
```

A finding needs all four of these, so capture them explicitly:

- `HTTP 201 Created` with a live `client_id` + `client_secret`, no API key / session / account.
- An arbitrary `redirect_uri` accepted — and pick a domain you do **not** own (use a reserved one
  such as `poc.example.com` or `attacker.test`) so the proof cannot be mistaken for your own infra.
- `client_secret_expires_at: 0` → the credential never expires.
- The granted `scope` → this sets the impact. `data:read_write` on a task/notes product means one
  consent click hands over the whole account; a read-only scope is a much weaker report.

## Pre-empt the "exact match is already enforced" rebuttal

`/oauth/authorize` usually **does** enforce exact `redirect_uri` matching — an unregistered URI
returns `400 Bad Request`. That control is real and does not help, because the attacker registers
their own URI in the step above. Show both halves in the report:

```
registered redirect_uri    -> 302 ...   (honoured)
unregistered redirect_uri  -> 400 Bad Request   (control exists)
```

Otherwise a triager answers "we validate redirect_uri" and closes it.

## Pitfall: a 302 is NOT the victim's experience — verify the chain renders

This nearly put a false claim in a shipped report. `/oauth/authorize` returned the expected
`302` with a `Location` pointing at a legitimate `/users/showlogin` on the vendor's own domain,
which reads as "the victim is sent to the real login page". It is not enough. The authorize host
and the host that serves the login SPA can differ, and the last hop can 404.

Measured on the real target:

| authorize host | chain | rendered page |
|---|---|---|
| `api.<target>` | 302 → `api.<target>/users/showlogin` → `/auth/login` | **404** |
| `app.<target>` | 302 → `app.<target>/users/showlogin` → `/auth/login` | "Log in to …" — correct |
| `<target>` | 302 → `<target>/users/showlogin` → app login | "Log in to …" — correct |

All three hosts returned the identical `302` and all three returned `400` for an unregistered URI —
the only difference was whether the final page rendered. Fixing this meant changing the host in the
reproduction steps; the vulnerability itself was unaffected.

So: for every claim of the form "the victim will see X", **open it in a real browser and assert X
rendered** — not just that a status code came back.

```python
# headless proof: url + title + DOM text + which inputs exist
page.goto(authorize_url, wait_until="domcontentloaded")
page.wait_for_timeout(7000)
assert "Log in" in page.title() or "log in" in page.inner_text("body").lower()
print(page.url, page.title(), page.eval_on_selector_all("input", "e=>e.map(x=>x.type)"))
```

Check every hostname the endpoint is served from, because a vendor commonly serves the same OAuth
route from `api.`, `app.` and the bare apex — and only some of them are complete.

## Severity framing

Default to **Medium**, not Critical: the primitive (open registration + arbitrary redirect) is
severe, but exploitation requires one victim consent click on a phishing link. State that
explicitly rather than letting the triager discover the caveat and downgrade the report for you.
