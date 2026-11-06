# BaaS backend attack surface — Supabase / PostgREST (and the Firebase parallel)

Companion to `bug-bounty-exhaustive-testing`. Sibling of `wordpress-rest-api-attack-surface.md`:
a platform-specific map of what to probe once recon tells you the backend is a BaaS.

**Trigger:** a static/SPA front end whose CSP `connect-src` or JS bundle references
`https://<20-char-ref>.supabase.co` (or `<project>.firebaseio.com` / `firestore.googleapis.com`).
The front end is the decoy; the BaaS project is the real target surface.

Worked reference: Euredas VDP, 2026-10-06 (Astro static site on Firebase Hosting → Supabase project
`hagvijmtmrhlmexbzxhb`, one table, one Edge Function). Everything below was run there.

---

## 1. Locate the project and its keys from the front end

```bash
# CSP connect-src is the fastest inventory — it names every backend the page is allowed to call
curl -sI https://www.TARGET/ | tr ',' '\n' | grep -iE 'connect-src|supabase|firebase|amazonaws'

# harvest the bundles, then mine them
for f in $(curl -s https://www.TARGET/ | grep -oE '/_astro/[A-Za-z0-9_.-]+\.js|/assets/[^"]+\.js' | sort -u); do
  curl -s "https://www.TARGET$f" >> alljs.txt
done
grep -oiE 'https://[a-z0-9]{20}\.supabase\.co' alljs.txt | sort -u
grep -oiE 'eyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}' alljs.txt | sort -u   # the anon JWT
```

**Always decode the JWT before using it** — the payload tells you which role you hold:

```python
import base64, json
p = key.split('.')[1]; p += '=' * (-len(p) % 4)
print(json.loads(base64.urlsafe_b64decode(p)))    # -> {'role': 'anon', 'ref': '<project>', 'exp': ...}
```

`role: anon` = the public key. If you ever see `service_role` shipped to a browser, **stop and report
immediately** — that key bypasses RLS entirely (Critical, no further testing needed).

A leaked anon key is **not itself a finding** — it is designed to be public. The finding is what it can
still reach.

## 2. THE test: `anon` vs `authenticated` (and vs `service_role`)

Supabase has three principals. Revoking privileges from `anon` is **not** revoking them from
`authenticated` — and a lot of projects do exactly half the job. A self-registered account is a
*different principal* with a fresh set of GRANTs.

```bash
KEY=<anon-jwt>; SB=https://<ref>.supabase.co
# as anon
curl -s -H "apikey: $KEY" -H "Authorization: Bearer $KEY" "$SB/rest/v1/<table>?select=id&limit=1" -w '\n[%{http_code}]\n'
# -> 401 {"code":"42501","message":"permission denied for table <table>", ...}
```

That is the denial **for anon only**. Now register and retry with an `authenticated` token:

```bash
curl -s -X POST "$SB/auth/v1/signup" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
     -H 'Content-Type: application/json' -d '{"email":"<you@real-inbox>","password":"..."}'
curl -s -X POST "$SB/auth/v1/token?grant_type=password" -H "apikey: $KEY" \
     -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
     -d '{"email":"...","password":"..."}'      # -> access_token = an authenticated JWT
# then repeat every /rest/v1/ probe with that token in Authorization:
```

If `authenticated` retains SELECT on the table, you have **mass PII exposure** reachable with a
self-created account — that is the high-value outcome and it is invisible if you only ever test anon.

**Blockers you will hit, and what they mean:**
- `400 email_address_invalid` — GoTrue rejects non-deliverable domains (`@example.com`). Use a real
  disposable inbox (mail.tm API) or an alias you control. Not a block, just validation.
- `429 over_email_send_rate_limit` — the project's **email quota is exhausted**. This is project-wide,
  not per-IP. `mailer_autoconfirm:false` means signup cannot complete without the confirmation mail, so
  **this single quota can make the whole authenticated-role test unreachable**. Record it as an untested
  hypothesis, not a pass — and note that exhausting it is itself a (usually out-of-scope) DoS class.
  With a real inbox: poll the mailbox, extract the verify link, `curl` it, then do the password grant.

## 3. Schema enumeration — the 401-vs-404 table oracle

`/rest/v1/<name>` answers differently for "table exists but you may not read it" vs "no such table".
That is a free schema enumeration primitive:

```bash
for t in waitlist users profiles leads subscribers contacts invites accounts organizations campaigns; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
         "$SB/rest/v1/$t?select=id&limit=1")
  printf '  %-16s %s\n' "$t" "$code"      # 401 = EXISTS (denied) | 404 = absent
done
```

Also probe, in order:
- `GET /rest/v1/` — PostgREST root. Usually `401` (*"Only the `service_role` API key can be used"*),
  which is correct behaviour, not a gap.
- `POST /rest/v1/rpc/<fn>` — anon-callable Postgres functions. `404` = absent. An exposed
  `SECURITY DEFINER` function is a common way past a locked table.
- `Accept-Profile: <schema>` header against `/rest/v1/` — reach into `storage`, `auth`, `vault`,
  `extensions` rather than `public`.
- **The `42501` hint line names the object and even the GRANT to run** — read it, it is documentation.

## 4. Edge Functions — the "server gate"

The interesting server-side logic is usually a Deno Edge Function, not PostgREST.

```bash
# existence: 404 = absent, anything else = exists (405 = exists, wrong method)
for fn in waitlist-submit submit signup invite contact newsletter admin health webhook; do
  curl -s -o /dev/null -w "  %-20s %{http_code}\n" -H "apikey: $KEY" "$SB/functions/v1/$fn"
done
```

Then **read the client bundle for the server's contract** rather than guessing the schema. The submit
function was recovered in full from one minified chunk — the endpoint, the payload shape, and the whole
response contract:

```js
fetch(`${url}/functions/v1/waitlist-submit`, {method:'POST',
  headers:{'Content-Type':'application/json', apikey:k, Authorization:`Bearer ${k}`},
  body: JSON.stringify({...form, captcha_token: t})})
// i.ok -> 'ok' | 409 -> 'duplicate' | 429 -> WaitlistRateLimitError
```

That single block told us: the exact field set (`name,email,country,country_code,phone,company,role,
industry,goals,source,user_agent`), that `captcha_token` is validated server-side, and the two
oracle-bearing status codes. **The bundle is the API spec.**

Probe order on the function: `GET` (expect 405) → `POST {}` (expect payload validation) → `POST` with a
bad token (expect the captcha rejection). Mostly you learn the schema before anything is written.

## 5. Auth surface — `/auth/v1/settings` is public, and it is informative

```bash
curl -s -H "apikey: $KEY" "$SB/auth/v1/settings"
```

Read: `external.{email,google,...}`, `disable_signup`, `mailer_autoconfirm`, `sms_provider`.
On the worked target: `email:true`, `disable_signup:false`, `mailer_autoconfirm:false` → **public
signup was live** even though the site's own security page claimed *"no accounts and no sign-in."*
That is a real, citable contradiction — but *proving* it needs the authenticated-role test above,
so do not report the contradiction alone.

`$SB/auth/v1/health` returns the GoTrue version (`{"version":"v2.197.0",...}`) — version disclosure,
usually informational.

## 6. Storage

```bash
curl -s -H "apikey: $KEY" -H "Authorization: Bearer $KEY" "$SB/storage/v1/bucket"   # needs BOTH headers
# public buckets are readable with no auth at all:
for b in public assets uploads avatars media files documents; do
  curl -s -o /dev/null -w "  public/$b -> %{http_code}\n" "$SB/storage/v1/object/public/$b/"
done
```

An open `public` bucket with user uploads is the classic BaaS leak — check it before anything exotic.

## 7. Firebase / Firestore parallel

```bash
curl -s -o /dev/null -w '%{http_code}\n' "https://<project>.firebaseio.com/.json"        # 404 = RTDB off
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://firestore.googleapis.com/v1/projects/<project>/databases/(default)/documents"
```

`<project>.web.app` / `<project>.firebaseapp.com` are just the hosting site — a `200` there proves
nothing about the data layer. Firebase Hosting estates frequently have **no** database at all; the data
lives in the BaaS project the CSP names. Enumerate hosting *site names* separately
(`<name>.web.app`) — a second site in the same project is another origin to test.

## 8. What is actually reportable

| Observation | Verdict |
|---|---|
| Anon key in the bundle | Not a finding — by design |
| `authenticated` (or worse `service_role`) can read a table the anon key cannot | **High/Critical — prove with one row** |
| Anon can read a table containing PII | **High** |
| Edge Function trusts a client-supplied field that drives a privileged write | Prove impact, then report |
| Public signup enabled while the site claims "no accounts" | Low on its own — needs the role test or a quota/abuse impact |
| Project email quota exhaustible | DoS class — usually **out of scope**; check the brief |
| Membership/enumeration oracle (`409 duplicate` on submit) | Low/Info; gated by captcha + rate limit |
| GoTrue version, `/auth/v1/settings` contents | Informational |

**Read the brief's out-of-scope list first.** The worked target explicitly excluded *"bulk submissions
against the waitlist form"* — the rate-limit-bypass finding was un-reportable before it was tested.

## 9. Pitfalls

- **A `/security` page's claims being TRUE is not an audit result.** See the "VENDOR CLAIMS VERIFIED
  TRUE" anti-pattern in the parent SKILL.md. Test the sibling role and the downstream service instead.
- **Do not insert multiple rows to "prove" an insert.** One marked row (`ZZRES…`) proves it; the rest is
  liability and may violate the program's spam clause. Mark test data so the owner can delete it.
- **Do not spend the email quota on probing.** It is project-wide and it can lock you out of the
  authenticated-role test you actually wanted.
- **`@example.com` is rejected by GoTrue** — a real inbox is required for any confirmation flow.
- **Missing `Authorization:` on storage calls returns `400 headers must have required property
  'authorization'`** — send both `apikey` and `Authorization`.
- **Shell quoting breaks on long JWTs.** Put the key in a file and drive requests from a small Python
  script; the 208-char JWT inside a nested-quoted `curl` is where sessions get lost.
