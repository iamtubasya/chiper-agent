# Supabase / PostgREST attack surface (BaaS-backed web apps)

Supabase backs a huge slice of modern SaaS/startup sites: a static front end plus a managed
Postgres behind PostgREST, GoTrue (auth), Storage, and Edge Functions. The whole backend is
reachable from the browser, so **the public key is in the JS bundle by design** — that is not a
finding, it is the entry point. The findings live in what that key (and any *other* principal)
can reach.

## 0. Fingerprint it fast

| Signal | Where |
|---|---|
| `https://<ref>.supabase.co` | `connect-src` in the CSP, or in any XHR in the bundle |
| The public key | a JWT (`eyJ…​.eyJ…​.…`) in the bundle; decode it — `role` is `anon` in production |
| Project ref | the subdomain, and the `iss`/`ref` claim inside that JWT |
| `Server: cloudflare`, `sb-gateway-version`, `sb-project-ref`, `x-sb-edge-region`, `x-deno-execution-id` | Edge Function responses |

Grab the CSP header first — it is a free inventory, and `connect-src` names the backend outright.

Decode the key before using it:

```python
import base64, json
p = key.split(".")[1]; p += "=" * (-len(p) % 4)
print(json.loads(base64.urlsafe_b64decode(p)))   # {"role":"anon","iss":"supabase","ref":"<ref>","exp":...}
```

If `role` is `service_role`, you are done — that key bypasses everything. (It should never ship;
if it does, that is the finding.)

## 1. The PostgREST table-existence ORACLE — enumerate the schema for free

`/rest/v1/<table>` distinguishes **"no such table"** from **"table exists but you may not"**. This
turns table discovery into a status-code comparison:

```bash
for t in users profiles leads subscribers contacts waitlist invites referrals campaigns; do
  printf "  %-14s -> " "$t"
  curl -s -o /dev/null -w "%{http_code}\n" \
    -H "apikey: $KEY" -H "Authorization: $SCH$KEY" "$SB/rest/v1/$t?select=id&limit=1"
done
```

| Response | Meaning |
|---|---|
| `404` (`PGRST205`) | table does not exist |
| `401` `{"code":"42501","message":"permission denied for table X"}` | **table EXISTS**, principal denied |
| `200` + rows | you have read — report immediately |

The `42501` error even names the table and tells you the exact missing grant
(`GRANT SELECT ON public.waitlist TO anon`), which confirms you found a real object.

**Do the same for Edge Functions** (`/functions/v1/<name>`: `404` = absent, anything else = exists)
and for **anon-callable RPC** (`POST /rest/v1/rpc/<fn>`).

## 2. The distinction that decides most of these engagements: GRANT vs RLS, and anon vs authenticated

Supabase has **two** Postgres roles for public traffic: **`anon`** (the shipped key) and
**`authenticated`** (any logged-in user's JWT). Plus `service_role` (never shipped).

**A table can be denied to `anon` while still being readable by `authenticated`.** Devs revoke from
the key they can see in the browser and forget the other role. This is *the* high-value test:

1. Get the auth settings (below) and check whether public signup is enabled.
2. Register a real, disposable account (own mailbox — never a fake identity for a regulated service).
3. Confirm the email, obtain the `authenticated` JWT.
4. Re-run the §1 table probe with **that** token instead of the anon key.

A `200` there is a PII exposure, and it directly refutes the "the public key cannot read our data"
claim (the claim was about `anon`; nobody tested `authenticated`).

Also worth probing: `Accept-Profile: storage` / `auth` / `vault` on `/rest/v1/`, and
`/storage/v1/bucket` + `/storage/v1/object/public/<bucket>/` for public buckets.

## 3. GoTrue (auth) endpoints — publicly readable by design, informative anyway

```bash
curl -s "$SB/auth/v1/health"   -H "apikey: $KEY"   # {"version":"v2.197.0","name":"GoTrue",...}
curl -s "$SB/auth/v1/settings" -H "apikey: $KEY"
```

`/settings` tells you, before you try anything:

- `external.email: true` + `disable_signup: false` → **public signup is open** (test it, don't assume)
- `mailer_autoconfirm: false` → a confirmation email is required before you get a session
- `anonymous_users` → whether you can get a session with no credentials at all (often the fastest route)
- enabled OAuth providers

Signup rate limits are **project-wide**, not per-IP: hammering it earns
`429 {"error_code":"over_email_send_rate_limit"}` and can lock out *legitimate* signups. Create one
account, then stop. If you need a confirmed user and the quota is spent, park the flow and resume
later rather than retrying in a loop.

`email_address_invalid` for `@example.com` is GoTrue rejecting the domain, not signup being closed —
use a real disposable mailbox to learn the truth.

## 4. Response differentials are the finding

The most common real bug on these apps is not a broken permission — it is an **inconsistent
response that leaks state**. Endpoints tend to be carefully generic on validation
(`invalid_payload`, `captcha_failed`, `method_not_allowed`) and then leak through a business
condition:

| Condition | Response | Leak |
|---|---|---|
| record exists | `409 {"status":"duplicate"}` | **membership oracle** |
| record absent | `200 {"status":"ok"}` | — |

Always run the **ordering test** to size it correctly:

```
KNOWN  identifier + INVALID captcha/token -> 403  ┐ identical ⇒ the gate runs FIRST
UNKNOWN identifier + INVALID captcha/token -> 403  ┘ ⇒ oracle is gated  ⇒ LOW
                                                   divergent ⇒ business check first ⇒ bulk-usable ⇒ HIGH
```

Do not guess the severity — one request pair decides it. (Verified on a Supabase waitlist gate:
captcha ran first, so the oracle was genuinely Low; reporting it as Medium would have been wrong.)

## 5. Edge Functions

```bash
curl -X GET  "$SB/functions/v1/<fn>" -H "apikey: $KEY" -H "Authorization: $SCH$KEY"  # 405 = exists
curl -X POST "$SB/functions/v1/<fn>" ... -d '{}'                                      # schema probe
```

- `method_not_allowed` / `invalid_payload` / `captcha_failed` are all *good* — generic, no leak.
- Recover the exact expected body from the client bundle (the object literal passed to `fetch`), then
  replay it yourself. Being able to drive the function from `curl` is what lets you vary one field at
  a time for oracle work.
- Edge Function `console.log` and errors are visible to you **only** if the project leaks them;
  assume they are not.
- If the gate is Turnstile-protected, mint a real token rather than fighting it —
  see `bot-protected-target-testing` §3b-trigger / §3b-noheadless (bogus-token test for a test-secret
  bypass; Camoufox + reading the site's own widget otherwise).

## 6. Scope discipline (this bites harder than the tech)

BaaS-backed marketing sites write their security posture down, and it is worth **reading as a brief**
— then attacking it, not auditing it (see `redteam-mindset` correction #10).

Common policy wording to extract *before* testing:

- **"bulk submissions against the <form>"** / volumetric / spam testing is frequently **explicitly out
  of scope**. This kills the "bypass the rate limit and spam it" idea — check before you write it up.
- Automated-scanner output without a working PoC is often ineligible.
- "Best-practice / missing-header" observations without demonstrated impact are often ineligible.
- The **product application** is frequently a *separate* service — sometimes explicitly in scope, and
  usually far more interesting than the marketing site. Check whether it is even deployed before
  promising a second phase: on one engagement every app route 404'd and the product was pre-launch.

## 7. Quick reference — the order to work

1. CSP `connect-src` → find `<ref>.supabase.co`; decode the shipped key (`role`? `ref`?).
2. `/rest/v1/<candidate>` sweep → the table oracle (§1). Note every `401`.
3. `/auth/v1/settings` → signup open? autoconfirm? anonymous users?
4. Enumerate `/functions/v1/<name>` and `/rest/v1/rpc/<fn>`.
5. Read the policy for out-of-scope classes **before** touching anything state-changing.
6. **Test every principal against the objects that exist** — anon, then `authenticated` (§2).
7. Grep the bundle for other keys, other backends, other envs; check `*.js.map` and `/.env`.
8. Only then start on the application logic itself.
