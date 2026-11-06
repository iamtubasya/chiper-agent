# PubNub engagement — 2026-10-31

Worked example for `unauth-surface-discovery`. Target `pubnub.com`; programme is an email-only VDP
(`support@pubnub.com`, no HackerOne/Bugcrowd listing), policy revised 2025-01-13, payout PayPal at
vendor discretion with no published amounts.

**Outcome (final, 2026-10-31):** 8 findings submitted to `support@pubnub.com` — 2 High, 5 Medium, and one
that was **over-claimed and still needs a correction** (see §11). The 255 authenticated routes remain
untested behind the reCAPTCHA-Enterprise signup wall (§9).

| # | finding | severity | message id |
|---|---|---|---|
| F1 | SSO tenant disclosure via `/api/saml?domain=` | Medium 5.3 | `1a18ea93e0311dff` |
| F2 | live DB pool telemetry via `/api/health` | Medium 5.3 | `1a18ea920fb8313f` |
| F3 | unauth OAuth DCR + client-metadata impersonation | Medium 5.3 | `1a18eb51e754830f` |
| F4 | session-middleware presence-check auth bypass (`x-session-token`) | Medium | `1a18ed9c5770407c` |
| F5 | unauth chat history read — **over-claimed, see §11** | ~~7.5~~ | `1a18ee78beef2bc0` |
| F6 | unauth WRITE to the moderation keyset | High 7.5 | `1a1900df483b5018` |
| F7 | unauth internal role-catalogue enumeration | Medium 5.3 | `1a1900df90bad92d` |
| F8 | `/config.json` live Segment + Inkeep key disclosure | High 8.2 | `1a19078e594bd22e` |

The chain-escalation battery (§1l–1m) did not complete to a token — the `redirect_uri` allowlist held —
but it surfaced the DCR/impersonation primitive, and the same "widen the unauth sweep" instinct later
produced F6, F7 and F8. Full battery: `references/oauth-dcr-impersonation.md`.

---

## 1. Scope and policy first

Fetched `https://www.pubnub.com/bug-bounty-policy/` before any probe.

**In scope:** Platform/API infrastructure, real-time messaging infrastructure, Admin Dashboard,
official website, official SDKs and client libraries.

**Out of scope:** third-party applications, test environments and sandbox systems, example code
repositories, demo applications, infrastructure provider systems (AWS, Google Cloud).

**Ineligible classes:** DoS/DDoS, rate-limiting issues, missing security headers, self-XSS,
clickjacking on non-sensitive pages, theoretical vulnerabilities without PoC, test-environment
misconfig, social engineering, physical security.

**Two clauses that shaped the whole run:**

1. *"Testing Guidelines: Avoid automated scanning tools"* — conflicts with the operator's standing
   mandate that automated tooling is mandatory. Resolution: log one line in
   `plans/scope-risk-log.md` quoting the clause and stating the risk is accepted, run automated lanes
   **gentle** (rate-limited, low concurrency, no brute force, honour 429), and do not treat the clause
   as a stop condition.
2. *"Automated and AI-Generated Submissions"* — reports must be human-verified with manual repro, and
   **AI usage must be disclosed**. Both drafts carry an explicit AI-disclosure paragraph plus a
   statement that every finding was manually reproduced 3x and is reproducible with plain `curl`.
   This is a hard requirement on this programme; missing it gets the report closed without response.

`security.txt` is absent (404 at both apex and www) — the policy page is the only disclosure channel.

---

## 2. Estate sweep

`subfinder -d pubnub.com -all` → 101 names; cross-checked against crt.sh (`?q=%.pubnub.com&output=json`)
which added 26 more names. 91/101 resolved.

Resolved and probed every host unauth. Live hosts worth remembering:

| host | what it is |
|---|---|
| `admin.pubnub.com` | **Admin Dashboard (in scope)** — Vite SPA + `/api/*` |
| `dashboard.pubnub.com` | same build, same `/api/*` |
| `demo-admin.pubnub.com` | demo instance, auto-login read-only viewer (**OOS: demo application**) |
| `moderation-dashboard.pubnub.com` | CRA SPA, embeds two PubNub keysets, ships source maps |
| `mcp.pubnub.com` | PubNub MCP server (JSON-RPC, bearer required) |
| `enterpriseenrollment.pubnub.com` | Microsoft Intune enrolment page (CNAME to `manage.microsoft.com`) |
| `it-help.pubnub.com` | Jira Service Management (all REST paths serve the SPA shell) |
| `ps.pndsn.com` | the real-time messaging API (core product) |
| `internal-admin.pubnub.com` | resolves to AWS `34.223.230.224`, all ports filtered |

CNAME sweep across all 101 hosts → 3 dangling (see §6).

---

## 3. Admin Dashboard bundle → 293 (method,path) pairs

`admin.pubnub.com` serves a Vite SPA. `GET /assets/index-BNZWyG36.js` is a **3.6 MB** bundle. One regex
over it recovers the generated API client in full:

```python
blocks = re.findall(r'\{path:\s*[`"]([^`"]+)[`"]\s*,\s*method:\s*"([A-Z]+)"([^{}]{0,300})', js, re.S)
# 293 pairs; 255 marked secure:!0, 38 not
```

The auth model fell out of the same bundle: session is `__Host-PN-2-pnAdminToken` (cookie) **or**
`x-session-token` (header). Registration posts to `POST /api/users` with reCAPTCHA Enterprise
sitekey `6LdxhW8pAAAAAArRGDvcAZBXwP5rJfx0zwRGzbCi`.

**The 38 unmarked routes** were swept against both `/api` and `""` prefixes (586 probes). Notable
route families recovered: `/api/subscription/*` (billing, invoices, payments, refunds, credit notes,
price allocation, pricing exceptions, bill-run), `/api/bizops-dashboards/*` (auto-moderation, word
lists, spaces, uuids), `/api/alerting/*`, `/api/legal-files/*`, `/api/incident-notice`,
`/v1/ui/*` (Functions packages, revisions, kv secrets/jsons), `/subkeys/{id}/{overview,entities,relationships}`.

**The 401-vs-403 split is the free auth-model map:**

| response | meaning |
|---|---|
| `401 {"code":401,"error":"Unauthorized"}` | auth middleware never ran |
| `401 {"statusCode":401,"message":["Authentication required"]}` | different backend (NestJS-style) |
| `403 {"message":"Forbidden resource","error":"Forbidden"}` | middleware ran and refused |
| `400 {"message":"Missing accountId"}` | validation runs **before** auth — a pre-auth oracle |
| `404 {"message":"Cannot GET /api/x"}` | route genuinely absent |

That last one is worth chasing: `/api/subscription/daily-invoice` answered `400 Missing accountId`
with no credentials, i.e. parameter validation executes before the auth check. Supplying
`?accountId=1` / `?accountId=627651` then correctly returned `401` — so the ordering is cosmetic, not
a bypass. Recorded as a negative.

---

## 4. FINDING 1 — SSO tenant disclosure via `/api/saml?domain=`

`GET /api/saml?domain=<domain>` is the login page's "type your corporate domain" lookup. Unauthenticated,
and it discriminates:

```
domain=dazn.com     -> 200 {"redirect_url":"https://login.microsoftonline.com/30459df5-1e53-4d8b-a162-0ad2348546f1/saml2?SAMLRequest=..."}
domain=life360.com  -> 200 {"redirect_url":"https://life360.okta.com/app/life360_pubnub_1/exkc75i38fNmI9GKo4x7/sso/saml?SAMLRequest=..."}
domain=vimeo.com    -> 200 {"redirect_url":"https://vimeo.okta.com/app/vimeo_pubnub_1/exken2mai32EuYCPp5d7/sso/saml?SAMLRequest=..."}
domain=ptc.com      -> 200 {"redirect_url":"https://login.microsoftonline.com/.../saml2?SAMLRequest=..."}
domain=example.com  -> 400 {"error_data":["SSO is not enabled for this domain"]}
```

Decoding the base64+deflate `SAMLRequest` from the dazn.com response:

```python
raw = base64.b64decode(saml)
xml = zlib.decompress(raw, -15).decode()          # raw-deflate, wbits=-15
```

```xml
<samlp:AuthnRequest ID="ONELOGIN_6e5fcfb41f3ed298d28dbe164a22e1cc0a3dfa17" Version="2.0"
  IssueInstant="2026-10-30T20:01:39Z"
  Destination="https://login.microsoftonline.com/30459df5-1e53-4d8b-a162-0ad2348546f1/saml2"
  ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
  AssertionConsumerServiceURL="https://admin.pubnub.com/api/saml/acs?domain=dazn.com"
  AttributeConsumingServiceIndex="1">
  <saml:Issuer>https://admin.pubnub.com/</saml:Issuer>
  <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified" AllowCreate="true"/>
</samlp:AuthnRequest>
```

**3x validation** per domain, 1.5 s apart: IdP host and tenant path identical on all three runs; only
`IssueInstant` changes (expected SAML behaviour). 60 candidate corporate domains swept → 4 matches.

**Input-validation negative (recorded so nobody re-tests it):** `evil.dazn.com`,
`dazn.com.evil.example.com`, `evil-dazn.com`, `dazn.co`, `azn.com`, `dazn`, `sub.dazn.com`,
`dazn.com ` (trailing space), `dazn.com%00.evil.com`, `dazn.com%26x=1`, `dazn.com/../../evil`,
`dazn.com?next=…`, `dazn.com%0d%0aX-Injected:%20yes` — **all 400**. `DAZN.COM` normalises and matches
(correct). So this is horizontal disclosure, not injection.

**Escalation attempt — SAML ACS — and why it failed.** `POST /api/saml/acs?domain=dazn.com` accepts
`SAMLResponse` form-encoded. Progression of errors shows the validation order:

| payload | response |
|---|---|
| garbage / empty | `500 General Error` |
| no `<AuthnStatement>` | `301 → /login?error=The Assertion must include an AuthnStatement element` |
| no `<AttributeStatement>` | `301 → …error=There is no AttributeStatement on the Response` |
| wrong `<Issuer>` | `301 → …error=Invalid issuer … (expected https://sts.windows.net/<tenant>/, got …)` |
| correct issuer, **unsigned** | `301 → …error=No Signature found. SAML Response rejected` |
| correct issuer, **self-signed** RSA-SHA256 signature | `301 → …error=Signature validation failed. SAML Response rejected` |
| XXE `<!DOCTYPE … SYSTEM "file:///etc/passwd">` | `500 General Error`, no file content reflected |

The self-signed test needed `signxml` (`pip install signxml`) plus correct SAML child ordering —
`ds:Signature` must be inserted at **index 1** inside `<saml:Assertion>` (right after `<saml:Issuer>`),
otherwise the schema check fires first and you never reach the signature check:

```python
signed = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha256",
                   digest_algorithm="sha256",
                   c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#").sign(root, key=key, cert=[cert])
sig = signed.find("{http://www.w3.org/2000/09/xmldsig#}Signature")
signed.remove(sig); signed.insert(1, sig)
```

**Verdict: signature validation is strict.** Filed as Medium information disclosure, explicitly *not*
as account takeover, with the negatives documented so the triager does not have to ask.

**CVSS:** `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` = 5.3.

---

## 5. FINDING 2 — live DB pool telemetry via `/api/health`

```
$ curl -s https://admin.pubnub.com/api/health
{"status":{"database":"Pool size: 40  Connections in pool: 10 Current Overflow: -30 Current Checked out connections: 0"}}
```

Three consecutive calls ~2 s apart gave `10/10/8`; further sampling over ~30 s produced 6, 8, 9, 10 with
matching overflow values. **The values move, so this is live instrumentation, not a cached string.**

Same endpoint live on `dashboard.pubnub.com` and `demo-admin.pubnub.com` — a product-wide exposure,
not one host's misconfiguration.

Three checks that make it a real finding rather than a false positive:
1. Values change between requests (live).
2. SPA-catch-all control: this path returns `application/json` while `GET /api/zzz-nope-x4hd2k9pq`
   returns a genuine `404` — so the route really exists and really is unauthenticated.
3. Credential-insensitivity: `Authorization: Bearer <garbage>`, empty
   `Cookie: __Host-PN-2-pnAdminToken=`, and `x-session-token: junk` all return the identical body.

Injection negative: `?id=1'`, `?id=1%27`, `?id=1' OR '1'='1`, `?id=1 AND SLEEP(3)`, `?host=x`,
`?callback=…` — no body or timing differential. No parameters are meaningfully consumed.

**CVSS:** `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` = 5.3.

---

## 6. Subdomain takeover — investigated and correctly rejected

Three dangling CNAMEs:

| host | CNAME target |
|---|---|
| `integration-pubnub-developer-onboard-education.pubnub.com` | `fluffy-gallimimus-4imrytaqhpwkrouwbrv2ainq.herokudns.com` |
| `pubnub-developer-onboard-education.pubnub.com` | `obscure-lilac-myxj1b6v76ctudsnq6x62826.herokudns.com` |
| `chat-engine-setup.pubnub.com` | `chat-engine-setup.public.k-aws-pdx-1.ps.pn` (vendor-owned zone, not claimable) |

Both Heroku targets returned `404 "No such app"` from `heroku-router`, and crt.sh showed Let's Encrypt
certs for both hosts running Feb 2019 → Oct 2019 then stopping — the apps really were deleted seven
years ago.

**Why it is not a finding.** Querying Heroku's authoritative NS directly:

```
dig @dns1.p05.nsone.net fluffy-gallimimus-4imrytaqhpwkrouwbrv2ainq.herokudns.com A
-> status: NOERROR, ANSWER: 0, AUTHORITY: 1 (SOA present)      # NODATA, not NXDOMAIN
dig @dns1.p05.nsone.net zzx4hd2k9pq-ctrl-91827364.herokudns.com A
-> status: NOERROR, ANSWER: 0, AUTHORITY: 1 (SOA present)      # IDENTICAL
```

A random never-registered control name returns the **same** answer, so the response carries no
claimability information. Heroku's own help page then settled it: *"On June 14, 2023, Heroku will start
appending 12-character random identifiers to subdomains to prevent domains from being taken over after
renaming or deleting apps."*

Cross-checked with Google DoH and Cloudflare DoH (both agreed), and with `subzy` — which reported
`admin-dev.pubnub.com` as `[VULNERABLE] [Cargo Collective]`. That was a **tool false positive**: the
host returns `301 → https://admin-dev.pubnub.com:443/` then a plain nginx `404`, with no Cargo
Collective content anywhere. Two independent tools disagreed; the direct evidence won.

**Wildcard caveat that nearly invalidated the sweep:** `*.pubnub.com` resolves every nonsense name to
`pubsub.pubnub.com` (`zzxbgttm66jy80vx.pubnub.com` → `204.57.245.8`). So "no A record" is only
meaningful for hosts with an *explicit* CNAME; the wildcard's catch-all must be excluded from the
dangling list.

---

## 7. Verified negatives (do not re-test)

| surface | result |
|---|---|
| SAML signature validation | strict — unsigned and self-signed both rejected |
| XXE on `/api/saml/acs` | rejected, no file read, no OOB |
| `/api/saml` domain validation | strict — all suffix/prefix/NUL/CRLF tricks rejected |
| `/api/saml/metadata` | 500, not exposed |
| OAuth `/api/services/google/auth` | `state` present with CSRF token; `redirect_uri` not manipulable |
| OIDC `/.well-known/openid-configuration` | exposed (standard); `/oauth/jwks` exposed (standard) |
| **OIDC `/oauth/reg` dynamic client registration** | **SUPERSEDED 2026-10-31 — see note below.** Originally recorded as "rejects non-allowlisted `redirect_uris`"; that was true only of the `redirect_uris` sub-check. The endpoint is in fact **open to unauthenticated callers**, issues a `registration_access_token` to anonymous callers, has no rate limit (6/6 in <3 s), and performs **no verification of client identity metadata** — full PubNub branding accepted and persisted server-side. Reported as a separate Medium. Full playbook: `references/oauth-dcr-impersonation.md` |
| Payment webhook `/api/subscription/payment/webhook/invoice-payment` | `401 Webhook signature verification failed` when a valid `type` is supplied |
| MCP `mcp.pubnub.com` | bearer required; `Bearer null`/`undefined`/`alg:none` JWT all rejected with distinct errors |
| 293 admin API routes unauth | all 401/403. No bypass via `X-Original-URL`, `X-Rewrite-URL`, `X-HTTP-Method-Override`, `X-Forwarded-For`, `X-Real-IP`, `X-Forwarded-Host`, `X-Forwarded-User`, `X-Authenticated-User`, `X-Remote-User`, `X-Client-IP`, `X-Originating-IP`, double-slash, dot-segment, semicolon, `%2e`, uppercase, trailing dot |
| `/api/zendesk-authenticator` | 422 unauth with every header/param combination tried; no token leak |
| `/api/services/forgot-password` | uniform `{"result":true}` for existent and non-existent — no oracle |
| `/api/users/confirmation-email` | uniform `204` — no oracle (note: rate-limits to 503 after ~10 rapid calls) |
| Host-header injection on reset flow | rejected |
| Cache poisoning (`X-Forwarded-Host`, `X-Host`) on www | no body differential |
| Heroku subdomain takeover | not claimable (see §6) |
| App Context unauth CRUD | **by design** — see §8 |
| `/api/roles/validate/{a}/{u}/{t}` | uniform `400 {"code":400,"error":""}` — no oracle |
| `/api/invite/confirm/{token}` | uniform 404 — no oracle |
| AWS Marketplace API `uauyyzmf36.execute-api.us-east-1.amazonaws.com/Prod/subscriber` | validates `regToken` server-side; bogus token → `400 Registration data not valid` |
| `cdn.pubnub.com` (S3) | `403 AccessDenied` on `/`, `/index.html`, `/?list-type=2` — not public |
| `pubnub.center` (help/wiki/it-help) | live AWS-hosted zone, not dangling |
| `internal-admin.pubnub.com` | resolves to `34.223.230.224`; ports 80/443/8080/8443 all filtered |

Fleet-wide unauth sweep: **3,131 host × path combinations across 101 hosts** → 83 unauthenticated JSON
responses, of which the only non-trivial ones were the two findings plus `/api/me` on the OOS demo host
and `status.pubnub.com`'s Statuspage payload (by design).

---

## 8. App Context unauth CRUD — a by-design near-miss

`moderation-dashboard.pubnub.com`'s bundle embeds two keysets. On
`sub-c-a15882e8-3185-11ec-bb3f-f27e7ede0273`, App Context (Objects v2) allowed **full unauthenticated
CRUD**, verified 3x with fresh random IDs and read-back:

```
GET    /v2/objects/{sub}/uuids/{fresh}      -> 404 (does not exist)
PATCH  /v2/objects/{sub}/uuids/{fresh}      -> 200 created
GET    /v2/objects/{sub}/uuids/{fresh}      -> 200 (read-back confirms)
DELETE /v2/objects/{sub}/uuids/{fresh}      -> 200
GET    /v2/objects/{sub}/uuids/{fresh}      -> 404 (gone)
```

Also demonstrated unauth modification of a **pre-existing** object's name, then restored the original
value. And unauth enumeration of 598 channel objects (293 of them 1:1 DM channels encoding both
participants' user IDs and display names) plus 36 user objects.

**This is not a vulnerability.** PubNub's docs state it plainly:

> *"Access Manager is an optional add-on… Without it, any client that holds your subscribe and publish
> keys has unrestricted access to every resource on that keyset."*

> *"App Context currently doesn't support authorization using Access Manager."*

The keyset is also embedded in a **demo application**, which the policy excludes. Two independent
reasons it is out of scope. The lesson is in the skill's Pitfalls: grep the vendor docs for the feature
name plus "Access Manager"/"authorization" **before** building the PoC.

The second keyset (`sub-c-6c30d752-…`) returned `400 Invalid Subscribe Key` on every call — a stale
bundle reference, not a live keyset.

---

## 9. The signup blocker (what remains untested)

`POST /api/users` requires a valid reCAPTCHA Enterprise token. Five engines attempted:

| engine | result |
|---|---|
| SeleniumBase Pure CDP (real Chrome) | token minted (3090 chars) → `400 Score too low` |
| Playwright Chromium, persistent profile, humanised typing, warm-up on `/pricing/` | token minted (2318 chars) → `400 Score too low` |
| Playwright Firefox, persistent profile, `Asia/Jakarta` timezone | navigation timeout |
| Playwright Chrome **headed** (`channel="chrome"`), persistent profile, warmed on google.com + pubnub.com, per-character typing, mouse movement before submit | token minted (2425 chars) → `400 Score too low` |
| Camoufox (Firefox anti-detect) | tab-open hung 120 s+ repeatedly; server restart did not help |

Also confirmed the WARP VPN was the original cause of the low score — disconnecting moved egress from
`104.28.226.245` (datacenter) to `103.129.150.87` (residential Indonesian ISP) — but the residential IP
still scored too low. **No test account was obtained.**

**Consequence, stated honestly in the session report:** the **255 routes marked `secure:!0`** — billing,
invoices, payments, refunds, credit notes, keysets, Functions packages and kv secrets, audit logs,
bizops dashboards — remain untested for authenticated IDOR/BOLA. That is the highest-value remaining
surface on this target and the first thing to attack once a credential exists.

`nuclei` full-severity sweep over 6 hosts produced a **0-byte output file** — the lane did not
complete, so the coverage gate is not green and the report says so explicitly rather than claiming
"nuclei: 0 findings".

**What the blocker session produced instead.** Mapping the signup cost one session and yielded the
validation-order table (§1s) plus, from widening the unauth sweep in the same session, **two High
findings on other surfaces** (F6 the keyset write, F8 the `/config.json` key disclosure). A blocked
signup is a reason to widen the sweep, not to grind the captcha.

---

## 10. Deliverables produced

All 8 findings were built the same way and all 8 were **sent** by the agent after the operator said
"kirim". Convention: `findings/F<N>_<slug>.{md,pdf}` + `F<N>_email.txt` + `draft_f<N>.py`.

- PDFs generated with `report-writing/reportlab-security-pdf/scripts/md_to_report_pdf.py` and verified
  with `pdf_layout_check.py` (0 problems each). **Watch the layout checker's false positive:** it flags
  the literal word "sample" as a watermark, so a report containing "Sample entries:" fails. Reword to
  "Excerpt of the entries returned:".
- Drafts built as one MIME message (`multipart/mixed` → `multipart/alternative` text+html →
  `application/pdf`) and created with `drafts().create()`. **Do not `drafts().update()` in place** — F1
  and F2 drafts vanished after repeated update cycles (see SKILL.md Pitfalls).
- **The send step has a trap that cost two failed attempts.** `python gmail_ops.py send-draft <id>`
  runs against the *default* account, not the bounty account, and answers
  `404 Message not a draft` even though `drafts().list()` on the right account shows the draft sitting
  there. Send with the account resolved explicitly:

```python
import gmail_ops as G
label, svc = G.pick_service('RESEARCHER_USERNAME')          # NOT the default account
r = svc.users().drafts().send(userId='me', body={'id': draft_id}).execute()
print(r['id'], r.get('labelIds'))                 # -> message id, ['SENT']
```

  Then verify by re-reading the sent message: To, Subject, Date, `labelIds == ['SENT']`, and walk the
  MIME tree to confirm the `application/pdf` part is attached. Never report a send as done without that
  read-back.

---

## 11. FINDING 5 — the over-claim, and what it teaches

`GET https://ps.pndsn.com/v3/history/sub-key/sub-c-a15882e8-…/channel/default` returned ~60 messages
with sender UUIDs and no authentication. It was reported as **"real user chat history", CVSS 7.5 High,
sent** (`1a18ee78beef2bc0`).

**Every available signal had said demo keyset** — the full fingerprint table is in SKILL.md §1n. The
operator caught it with one question: *"Ini bukannya data public?"*

The correction draft was prepared (retract the "real user" claim, drop to Low/Informational, ask the
vendor to confirm whether the keyset is production or demo) but **was never sent** — the operator moved
on to other surfaces. **That is the open item on this engagement.** The lesson is not "be more careful";
the lesson is that the check takes under a minute and must run *before* the report goes out:

1. UUID/identifier format vs the vendor SDK's documented default.
2. Message envelope vs the SDK's documented demo envelope.
3. Content entropy (keyboard mash / single emoji / `"test"` = public playground).
4. Host + channel naming (`<feature>-demo.<vendor>.com`, channel `default` with `type:"default"`).
5. The vendor's out-of-scope list for "demo" / "sample" / "sandbox" / "test".

**And the write was reportable where the read was not.** The same run found the publish primitive
(F6, High) and the discriminator was a configuration asymmetry, not provenance: keyset
`sub-c-95fe09e0-…` returns **403 on history read** (Access Manager *is* enforcing) but **200 on
publish**. A vendor that made an authorisation decision and then failed to apply it to one operation
has a bug, not a demo default. That finding survived every "public subscribe key" argument.

**Corollary that also held:** sweeping all three harvested keysets × 14 channels showed exactly one
keyset with readable history and `occupancy: 0` on every channel — the blast radius was one isolated
demo keyset, not a fleet. A narrow, isolated read is a weaker signal than a wide one, and that too was
visible before the report went out.

---

## 12. Second round — what the deep-dive actually produced

After F5 the operator asked for chain escalation, then IDOR, then "high-value bugs". The order of
operations that worked, and the honest negatives:

**a) Chain battery (F4 × OAuth, F1 × F3, F2 × F5) — all negative.** The `x-session-token` bypass has
**zero effect on OAuth endpoints** (identical 404/400/401 with and without the header) because the IdP
runs on separate infrastructure with different middleware. A middleware bypass on one app is not a
bypass on the estate. F1 (tenant list) + F3 (bait client) is a credible phishing narrative but not a
CVSS upgrade. Recorded so the next session does not re-walk them.

**b) IDOR — negative, and the negative is the deliverable.** Swept every ID-bearing route under the
bypass, plus App Context by UUID, channel/membership metadata, message actions, files, push devices,
and cross-keyset history. Results: App Context 400 (PAM active), push device `200 []` (empty),
cross-keyset history 403 on the PAM-enabled keyset. **The horizontal control is mandatory** — for each
bypass-opened endpoint, vary the account ID and hash the responses; identical bodies across
`627651/1/2/100/999999/0` means the endpoint is not account-scoped, so there is no IDOR to claim.
Saying that explicitly is what stops the triager asking.

**c) The DataSync API is a bypass-opened surface with no reachable data.** `GET /api/datasync/ui`
answers `401` without the header and `400 {"errorCode":"DS-0002","message":"Invalid request path"}`
with it — 25 sub-paths opened the same way, all `DS-0100 Resource not found` because no numeric keyset
ID was obtainable. **One oracle was tested and rejected:** the two real sub-key strings returned
`503 DS-0009` while random strings returned `404 DS-0100`, which looked like an existence oracle — but
the literal string `demo` also returned 503 while a genuinely real keyset returned 404, so the split
tracks *string format forwarded to the backend*, not keyset existence. Not an oracle, not a finding.
Worth knowing so it is not re-derived.

**d) F6 — the write.** Publish key `pub-c-e087e539-…` sits in the moderation bundle next to the
subscribe key. The request-shape trap is the whole finding: form-encoded `message=<json>` returns
`[0,"Invalid JSON",...]` and reads as a block; a **raw JSON body** returns `200 [1,"Sent",...]`.
Measured: arbitrary channel names accepted (including `admin` and invented channels), a second keyset
also writable, 10/10 publishes in 10 s with no rate limit, HTML/JSON payloads stored verbatim, fake
`SYSTEM:` notices accepted. Controls that held: 32 KB → 413, history delete → 403, and publishing with
another user's UUID stores an empty `uuid` so impersonation does not persist.
**Verify by timetoken, not by grepping your marker:** require
`history.timetoken == publish.timetoken`. The read-back also returned `uuid: ""` and
`createdAt: null` — record that honestly rather than presenting a cleaner verification than you have.

**e) F7 — role enumeration.** `GET /api/roles/list` with **no token at all** returns HTTP 200 and the
full internal role catalogue (15 roles with numeric IDs: `Account Admin`, `Key Admin`,
`Bizops Objects Operator`, `Functions Developer`, …). Sibling routes `/api/roles/all` and
`/api/roles/1` return 401, so this is an omission rather than by-design. Note the **inverted polarity
trap on the same path**: with a garbage token the same endpoint returns 500, so a naive
"200 vs 500" differential reads as an auth oracle in the wrong direction. The finding is the
no-token 200; the 500 is a broken code path. Validated 3x byte-identical (MD5 `98c43f72e8bd…`).

**f) F8 — `/config.json`.** Found by sweeping the bundle for never-tested routes after the captcha
blocker. Full triage method in SKILL.md §1r. The framing that matters: **lead with the server-side
credential (Inkeep), cite the client-side one (Segment) as demonstrated impact**, and invite
reassessment on the Segment portion. Leading with the Segment key invites a by-design close.

**g) Third bundle migration.** The admin dashboard moved CRA → Vite mid-engagement and re-emitted 148
routes against the 146 previously mapped. A regex keyed to `/static/js/` silently returns zero assets
against a Vite host — grep for `(?:src|href)="(/[^"]+\.js[^"]*)"` instead. All 45 previously-untested
routes were closed, which is a publishable negative.

**h) Webhook signature check holds.** With a valid event type the endpoint flips from
`400 Invalid event type` to `401 Webhook signature verification failed`; 18 bypass shapes (no header,
empty, `t=` only, `v1=` empty, `X-Signature`, `X-Hub-Signature-256`, signature in body, signature in
query, `Content-Type: text/plain`, form-encoded) all returned 401. Cheap, strong negative.
