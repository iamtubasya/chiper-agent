---
name: chain-to-impact
description: "Chain a primitive to impact when a hunt returns only Low."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, security, severity, impact, chain, methodology, target-selection]
    related_skills: [bug-bounty, exploit-cookbook, hunt-business-logic, hunt-ato, artifact-backed-claims, triage-validation]
---

# Chain-to-Impact — break the Low-severity ceiling

## When to Use

- A hunt keeps producing Info/Low while comparable researchers get Medium+ on the same target.
- About to write up a primitive and the operator says *"selalu cari apa impact nya"* / *"chain rule sy setuju"*.
- At target-selection time, to pick a target whose severity ceiling is actually reachable.
- Any finding that is still a primitive (SSRF, info-leak, open redirect, CORS reflect, upload,
  public-object IDOR, CSRF-without-impact, mass-assignment-empty-field, verbose error) and has
  not yet been chained to a second bug.

This is a **method** problem, not luck. Three structural reasons findings stay Low, and the
one habit that fixes it.

## Why findings stay Low

**1. We test the unauthenticated perimeter; the money is behind auth.**
Programs cap pre-auth surface in their own rubric. Worked example (FlowCrypt, published
tiers): `$10-200` = "insecure config, open ports, HTML injection without apparent exploit
path"; `$100-3000` = medium/high *with user complicity* (CSRF etc.); `$1000-5000` = ATO /
sensitive-data / private-key exposure *without* user interaction. A `/health/` leaking
internal hostnames is bucket-1 **by the program's own words** — no writeup quality moves
it. Canonical Low-ceiling classes: `/health/`, missing headers, `CORS *`, bare
info-disclosure, open-redirect-no-chain, account-enumeration, public-IP. Several of those
(public IP, account enumeration) are *explicitly out of scope* on some programs, so
reporting them burns credibility.

**2. We stop at the primitive instead of chaining it.**
A primitive is ~Low alone. Medium/High needs a **second bug** that converts it into
account / data / financial impact.

**3. Target selection** — see operator rules at the bottom.

## The chain question (run on EVERY primitive before writing it up)

Force the question *"what second bug converts this into impact?"* and go hunt *that*
specifically. If the chain test is negative, record a **verified negative** (the control
holds) — do not inflate. "Always find the impact" ≠ "always claim impact".

| Primitive | Chain that produces Medium+ |
|---|---|
| Info-leak (hostnames, IPs, versions, stack traces) | fingerprint exact version → CVE on that version; or leak feeds SSRF target list |
| SSRF | → cloud metadata `169.254.169.254` → creds → account/data; or internal admin panel; or internal-only endpoint that trusts loopback |
| Open redirect | → OAuth `redirect_uri` / password-reset token exfil → ATO. No sink = Low. |
| CORS reflect | → only if a *cookie-authenticated* endpoint reflects it. API-key / `ACAO`-only = browser blocks, no impact. Prove which. |
| File upload | → webshell / path traversal / SVG+HTML stored XSS / image-tragick → RCE or ATO |
| IDOR on a *public* object | → enumerate to a *private* object (other user's doc/order/message) → PII/financial. Public-only = Info. |
| Account enumeration | → feeds credential-stuffing / password-spray (but many programs de-scope it) |
| CSRF (no impact shown) | → change victim email / OAuth grant / API key → ATO. "CSRF exists" alone = Low. |
| Verbose error / stack trace | → source-path + framework+version → code-level vuln; or PII in the trace |
| Mass assignment (empty field) | → set a *privileged* field (role, `is_admin`, `verified`, balance) → priv-esc |
| Write endpoint that takes a **foreign object id** *and* triggers vendor e-mail | → vendor sends branded mail (aligned SPF/DKIM) to arbitrary recipients carrying a link to the victim's object, naming the attacker as sender → phishing relay + sender misattribution + redistribution. Worked case (Hivenet 2026-10): `POST /metadata` with somebody else's `shareRecordId` plus a `recipients` list; the third party then read the victim's file. |
| Blob read authorised by **token only**, with no delete route | → "delete" and "expiry" become UI statements; the ciphertext stays retrievable and decryptable forever by anyone who harvested the id and the key → retention / erasure failure. Worked case (Hivenet 2026-10): `GET /p2p/storage/chunk/{cid}` served by any token, `DELETE` on that path 405/404. |
| A **capability id that is also handed to third parties** (a share id embedded in a link) | → treat it as a secret, not a public identifier. Ask "what second factor exists?" — if none, revocation is impossible by construction and every holder can derive the key. Hivenet: `readKey = PBKDF2(share.name, share.rootMid)`, both returned by the share record to any token. |
| Cross-tenant write primitive → DoS via quota | → check **who the quota is charged to** before claiming impact. Hivenet F1 charged the *creator*, so the victim's own writes still returned 201 and the chain died at the accounting step. |
| **Unverified profile e-mail change** | → password-reset mail is delivered to the NEW, unverified address → attacker sets the password → **full ATO**, original owner locked out with no notification. Works even when the app's own config says `force_email_verification: true`. |
| **Vendor-hosted subdomain app** (a `<brand>.tld` host running a third-party SaaS) | → treat as in-scope when the brief says "entire public digital footprint not OOS"; the ATO/IDOR you find there is still the brand's customer data. Check the OOS list before dismissing it. |
| **Version disclosure alone** ("site runs an old version") | → hygiene, earns nothing. **Chain it across siblings**: if `test`/`beta` runs the patched release and `prod` does not, the differential proves a *missed rollout* rather than an intentional pin — that is what lifts it to Medium. Then quote the intervening *security* release notes verbatim. |
| **Public OpenAPI/Swagger spec** | → extract `servers[].url` and every absolute host in the doc, then **RDAP-check ownership**. A base URL on a host that is not the vendor's (retail registrar, redacted registrant, third-party NS) served over plaintext `http://` means clients configured from that spec send credentials to a squatter. |
| **Any third-party host you are about to report** | → **check whether it is already claimed first**: `GET http://<domain>/` and read the body. A researcher PoC announces itself (`{"status":"captured","msg":"PoC - ... owned by researcher"}`). Claimed = duplicate = record it, do not submit. |

## Worked chain: unverified e-mail change → ATO (Kohl's Insider Shop, 2026-10-29)

Target `insidershop.kohls.com` — a Kohl's-branded employee store hosted on a
third-party Rails platform (Brightsites). Not on the programme's OOS list, and the
brief said "entire public digital footprint that is not Out-Of-Scope", so it stayed
in scope. The main estate (`www/mapps/wallet.kohls.com`) was behind an Akamai
IP-range ACL, so this reachable host carried the engagement.

The chain, end to end:

```
CHAIN 1 — session on victim -> change account e-mail (unverified) -> request reset
          -> reset link lands in attacker's mailbox -> set password -> ATO
  Step 1 can attacker reach the profile-update endpoint?   HOLDS  POST /account
                                                                 (_method=put,
                                                                 website_user[email])
  Step 2 does the server verify the new address?           DIES-AS-BUG
                                                                 e-mail changed instantly,
                                                                 no confirmation mail to
                                                                 either address
  Step 3 does reset follow the unverified address?         HOLDS  POST /account/password
                                                                 -> reset token mailed to it
  Step 4 does the token actually work?                     HOLDS  PUT /account/password
                                                                 -> login 302, old pw dead
  => FULL ATO. Validated 3x from two different attacker-controlled addresses.
```

The decisive detail: the page's own embedded config carried
`"force_email_verification":true` while the update endpoint ignored it. **Always
grep the rendered page for the app's own security flags** — a config that
contradicts observed behaviour is the strongest single line in the report.

Test recipe (Rails/Devise-shaped apps, ~5 minutes):

1. Self-provision an account; confirm it via the mailed token.
2. `GET /account/edit` → harvest `authenticity_token` + current field values.
3. `POST /account` with `_method=put`, the **current password** (the form demands
   it, so this is *not* a CSRF-shaped bug — it is a verification-logic bug), and a
   new e-mail you control.
4. `GET /account/edit` again → read back `website_user[email]`. Changed with no
   confirmation step = the primitive.
5. `POST /account/password` with that address → read the reset token out of your
   own mailbox (Gmail API with the stored refresh token).
6. `PUT /account/password` with the token → log in with the new password, and
   confirm the old password is rejected. That last check is what makes it an ATO
   rather than a "profile update" note.

Report framing: severity is **High**, not Medium — the chain ends in persistent
account takeover with the original owner locked out and never notified. State the
`force_email_verification` contradiction verbatim.

## Two chain families worth running on every target (2026-10-29)

Full worked examples, recipes and the honest-scoring framing: `references/patch-lag-and-leaked-host-chains.md`.

**1. Patch-lag differential.** Never report "host runs version X" alone. Enumerate siblings of the same
app (`prod/beta/test/dev/staging/uat`, `-test`/`-dev`/`-preprod`, plus a second region code), pull the
version from each unauthenticated root page, and **diff against the vendor's own GitHub releases API**
(`releases?per_page=8`) rather than from memory. If one sibling is patched and another is not, the
differential is the finding: it proves a missed production rollout with a named owner. Read the
intervening release bodies and quote the security lines verbatim — your inference is not evidence.
Then state plainly which hop you could not prove (usually exploitation needs an authenticated account,
or needs you to mail a crafted payload to staff, which is social engineering and RoE-forbidden).

**2. Leaked-host chain.** Sweep every live root for public specs (`/api-docs`, `/v3/api-docs`,
`/v2/api-docs`, `/openapi.json`, `/swagger.json`, `/api/v1/openapi.json`, `/swagger/v1/swagger.json`)
and require an `openapi`/`swagger` key in the JSON body — a bare `200 application/json` is usually a SPA
bootstrap, not a spec. Extract every absolute host, then **RDAP-check each one** against the vendor's
own domain: a vendor domain shows the vendor as registrar and vendor NS; a squatted one shows a retail
registrar with a redacted registrant. Then check whether it is already claimed (see table above).
RFC1918 answers (`172.16/12`, `10/8`, `192.168/16`) are internal-topology leaks, not pivots.

**The bogus-path control decides "unauth" vs "auth-before-routing".** Request a path that cannot exist
(`/api/zzz-notreal-x4hd2k9pq`) alongside the real ones:

- bogus → **404**, real → 401/403 ⇒ auth is per-route; go hunting for routes that lack it.
- bogus → **401** too ⇒ auth fires before routing; there is no unauthenticated surface, the public
  spec is the only exposure, chain dies. Say so instead of writing up "unauth API".
- write path → **401 while the identifier is bogus** ⇒ auth is checked *before* the identifier lookup;
  no BOLA there, and you must never fire destructive calls with real identifiers to find out.

## Chain family 3: the CVE fix-line sweep — the widest-reach Low→High (2026-10-29)

The patch-lag differential compares *siblings of one app*. This one compares **every host's advertised
version against a fix release**, which scales to the whole estate and routinely converts a `Server:`
banner — the most dismissible Low there is — into a High-severity CVE across dozens of hosts.

Worked: Deutsche Telekom, **34 in-scope hosts below nginx 1.31.0** → **CVE-2026-42945, CVSS 8.1**
(heap overflow in `ngx_http_rewrite_module`, unauthenticated RCE). Versions spanned 1.17.6 (2020) to
1.30.6; the oldest sat on `workplace.telekom.de`, and customer-facing hosts
(`carrierportal.wholesale.telekom.com`, `autoinvoice.dtse.telekom.com`) were in the set.

```
1. COLLECT    httpx -tech-detect over the live-host list -> tech[] strings like "Nginx:1.30.5".
              Parse "product:version" pairs; keep the raw string as the artefact.
2. FIXLINE    take the fixed version from NVD, never from memory:
              https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-...
              -> metrics.cvssMetricV31[0].cvssData.baseScore, .published,
                 descriptions[0].value (quote verbatim in the report)
              Compare version TUPLES, not strings — "1.9.0" < "1.31.0" is a string-lie.
3. ENUMERATE  every host whose tuple is below the fix line; dedupe by host; write
              evidence/<cve>-affected.json as [{host, version, http_status}].
4. VERIFY     re-read each host's LIVE header individually:
              curl -sI https://<host>/ | grep -i '^server:'
              tech-detect is a hint; the header is the artefact you quote. Keep oddities —
              "Caddy,nginx/1.30.0" is two proxies and the nginx hop is still vulnerable.
5. STOP       before firing anything that mutates state — see the `--check` trap below.
6. REPORT     title = the COUNT, not the product: "34 hosts run nginx < 1.31.0 — vulnerable to
              CVE-2026-42945 (CVSS 8.1)". Severity = what you actually proved.
```

**Severity framing that survives triage.** Rate **Medium** when you have proven *affected version at
scale* but not *the config precondition*. State the split explicitly — "proven: 34 in-scope hosts serve
below the fix release; not proven: the `rewrite`+`set` pattern is present" — then add *"if your triage
confirms the precondition I would expect High, and I would not argue with that."* That one sentence is
what makes a Medium land instead of being downgraded for over-claiming.

**Product-edition discrimination kills more CVE matches than any other check.** A PoC-corpus hit is a
lead, not a finding: `CVE-2025-54253` matched "Adobe AEM" and the target ran AEM — but the CVE is **AEM
Forms on JEE** while the target was **AEM Sites on Cloud Service** (`x-vhost
publish.prod.dxp.adobeaemcloud.com`). Different product, precondition structurally absent. Check the
*edition / deployment model*, not the vendor name, before spending a single request.

### A PoC's `--check` mode is not a safe probe — read the source before you fire it

The sharpest trap of this session. The CVE-2026-42945 PoC advertises `--check` / `--probe` /
`--exploit`, and the obvious move is to run `--check` as a harmless fingerprint. Its own body:

```python
def mode_check(host, port):
    """Detect-only — probe for the vulnerable rewrite + set pattern."""
    # 3. Sanity overflow trigger (no exec payload — uses harmless target).
    safe_target = b"\x41\x41\x41\x41\x41\x41"       # unmapped, no exec
    test_uri = (b"A" * 349) + (b"+" * 400) + safe_target
    s.sendall(b"GET /api/" + test_uri + b" HTTP/1.1 ...")
```

That **is** a heap-overflow attempt. "No exec payload" only means it will not achieve code execution —
the corruption still happens, and if it lands the worker dies. On a programme whose RoE says *"do not
limit system availability"*, running it against 34 production hosts (one a wholesale carrier portal) is
a rules violation, not a test.

Rules:
1. **Read the mode function, not the `--help` text**: `grep -n "def mode_check" -A40 exploit.py` and look
   at the actual bytes sent.
2. **Classify by what the packet does, not by the flag's name.** A "detect-only" mode that sends an
   overflow, a crash payload, a huge allocation, or a lock-taking request is destructive.
3. **Destructive + RoE forbids availability impact ⇒ stop at version verification**, and give that
   decision its own report section. A Medium with "here is why I did not fire it" beats a High obtained
   by violating the programme's own terms — vendors read that section favourably.
4. **A flag like `--i-have-tested-this` is a warning, not a checkbox.** If the author felt the need to
   add one, the default path is dangerous.

## Where the Medium+ surface actually is (put testing time here)

- **Multi-tenant data / authz** — cross-account IDOR/BOLA, object- + function-level authz.
  Highest-yield class; only reachable with 2+ accounts.
- **Business / money logic** — price, quantity, coupon stacking, proration, currency/tax
  rounding, refund, credit/wallet, entitlement gates, feature flags.
- **Auth core** — signup → verify → login → MFA → reset → session → logout. Token reuse
  after logout, `redirect_uri` acceptance, OTP brute-force, host-header reset poisoning.
- **Race conditions** on state transitions (double-spend, double-claim, coupon reuse).
- **Webhooks / SSRF / deserialization / SSTI / SQLi / RCE** — direct path to exec or exfil.
- **GraphQL** — introspection, batching, depth/alias abuse, per-field authz.

Perimeter classes (headers, CORS, clickjacking, open-redirect-no-chain, info-leak-no-sink)
are **filler** — report them, never let them be the whole engagement, never let scanning
them substitute for reaching the core.

## DeFi/Web3 severity ceiling — the "no fund loss path" wall

Mature DeFi protocols (7+ audits, active bug bounty, $250k top tier) explicitly N/A
everything that does not move, lock, or steal funds. Verified on LoopScale (2026-10):
all four reported findings — BOLA on user-scoped API, unauth state write, unauth RWA data
read, single-key upgrade authority — were rejected with the same two phrases:

1. **"No path to the locking, loss, or theft of funds"** — the primary filter.
2. **"On-chain discoverable = not confidential"** — kills all raw-chain-data exposure claims.

**Consequence for target selection and time allocation:**
- API access control bugs on DeFi backends (BOLA, missing auth, info disclosure) are
  **worthless** on these programs even when the scope text says "internal API endpoints
  and supporting backend services/infrastructure" are in scope. The scope admits them;
  the reward rubric does not.
- The only paying surface is **economic exploit**: oracle manipulation, liquidation
  gaming, flash-loan abuse, collateral pricing bypass, weight-matrix corruption, NAV
  staleness exploitation — anything that converts a protocol state into fund movement.
- **Before investing hours in API authz on a DeFi target, check whether prior findings of
  that class were rewarded.** If the program's brief says "primary focus is to prevent
  exploits resulting in the locking, loss, or theft of any funds", treat API bugs as
  reconnaissance for an economic chain, not as standalone findings.
- Centralization observations (single-key upgrade authority vs documented multisig) are
  also N/A'd — vendors claim "by design" even when the on-chain state contradicts the docs.

**Escalation-then-drop discipline:** when you find a real API bug on a DeFi target,
spend one focused escalation attempt (can this data/primitive move funds?), and if the
answer is no, **drop it before writing the report**. A verified-negative + documented
vendor-pattern reasoning is a better deliverable than a submitted N/A. Record the drop
reason in findings.json so the next session does not re-litigate it.

## Chain the REJECTED leads too (operator correction 2026-10-26)

The chain question above is usually applied to primitives you are about to *report*. The failure mode the
operator actually caught was the opposite: an engagement closed as "no findings" where **every lead had been
dismissed in isolation**. A lead scored alone is scored wrong — the dismissing sentence ("no data primitive",
"HoF-only", "not reachable") is itself a claim about a chain you never walked. Operator's words:
*"km udh cb lead ny dcek via chain attack?"*

Deliver a **chain table per lead that names the step where it dies**, not a list of dismissals:

```
CHAIN n — <entry primitive> -> <hop> -> <sink>
  Step 1 <entry reachable by attacker?>        HOLDS
  Step 2 <untrusted value propagates?>         HOLDS
  Step 3 <guard / enabling condition>          HOLDS as a condition
  Step 4 <can attacker control the enabler?>
           <the grep / decode that proves it>  => DIES AT STEP 4   (or UNPROVEN — blocked on X)
```

Rules that make the table honest:
- Each **HOLDS** needs an artefact (a decompiled line, a manifest attribute, a live request). Each **DIES**
  needs the single fact that kills it. "DIES" with no fact is the isolation error in disguise.
- The step that kills a scary lead is usually a *third* question, not the obvious one. Worked mobile example:
  exported deep link → `ACTION=WEB` → `WebView.loadUrl(untrusted)` with JS enabled looked like an ATO
  primitive. It died only at step 4: the JS bridge was gated on `arg_script_file`, which had **exactly one
  writer, hardcoded `null`**, and the fragment-link enum had **zero** entries mapping to that fragment.
  Three greps converted a scary lead into a defensible negative.
- A second lead died because the attacker-controlled `entityId` flowed into a **local settings lookup**
  (`IIdentitySettings.f(String):String`), not a server call — proving the sink is the whole job; the
  propagation chain was real and still worthless.
- **A chain that ends at "the server validates it" is UNPROVEN**, never a finding and never a verified
  negative. Name it as *the single unproven hop* of the engagement and state which credential would settle
  it. Do not let it silently join the "verified safe" list.

### Worked web/API example (Hivenet, 2026-10)

Two chains, both killed by a *verbatim server string* rather than by an argument. Quote the
string in the table — it is what makes the negative survive a vendor reply.

```
CHAIN A — anonymous public token -> enumerate the shared machine account's share records
          -> derive every transfer key -> mass disclosure
  Step 1 token mintable by anyone?          HOLDS  GET /auth/download-token, no auth, 24 h
  Step 2 records of that account listable?  HOLDS  GET /mutablerecords/type/{VOLUME,DIRECTORY,FILE}
                                                   -> 93 / 41 / 282 rows
  Step 3 key material obtainable?           DIES   GET /sharerecords (with and without
                                                   ?ownerAccountId=) -> 404 "share records not found".
                                                   The 416 records carry no wrapped key.
  => DIES AT STEP 3. The enumeration is real and still worthless; say so, with the 404.

CHAIN D — cross-tenant record write (a real finding) -> victim storage-quota exhaustion (DoS)
  Step 1 write into a foreign volume?        HOLDS  POST /mutablerecords -> 201
  Step 2 does the size charge the victim?    DIES   403 "adding 3221225472 bytes to the 3091202586 used
                                                   of 3221225472 bytes" — the quota is charged to the
                                                   CREATOR. Victim's own 5 MB writes still 201.
  => DIES AT STEP 2. Report F1 for integrity only; do not claim availability.
```

The transferable habit: when a chain dies, **re-read the error text for who the server thinks you
are**. "used X of Y" told us the accounting key was the caller, not the target — that one phrase
converted a would-be Critical into an honest High.

Cheap greps that terminate most mobile/deep-link chains of this shape: find the writer of the enabling
argument (`grep -rn '<arg_name>'` → count writers; one hardcoded writer = dead), check the enum/route table
for an entry pointing at the sink fragment/activity, and confirm the layout `android:visibility` + whether
anything sets it VISIBLE (a `gone` button with a click listener is unreachable except via
`View.performClick()` from an installed attacker app).

## Multi-Low composition — the Low pool is a parts bin, not a scrap heap (operator, 2026-10-29)

Operator rule, verbatim: *"make sure you chain multiple Low severity vulnerabilities together to
get higher severity ones."* This is a **standing requirement**, not a nice-to-have. It changes the
order of work: **never close a Low before the whole Low pool has been composed.**

### Why this beats "chain one primitive"

A single Low is usually Low *by itself* because it supplies only one of the four things a chain
needs. Four separate Lows often supply all four. Triagers score the **terminal impact**, not the
individual boxes — so the deliverable is one chain report whose severity is what the chain reaches.

### The four parts every chain needs — classify every Low by what it SUPPLIES

| Part | What it gives the attacker | Typical Lows that supply it |
|---|---|---|
| **K — Knowledge** | target/identifier/version/schema you could not otherwise get | info disclosure, verbose error, version leak, `.env`/source leak, GraphQL introspection, directory listing, response-header leak, public bucket listing, sitemap/`gau` artefact, cursor leaking a server-side filter |
| **A — Action** | the ability to make the server do something on your behalf | CSRF (no impact alone), open redirect, self-XSS→stored, HTML/email-template injection, mass-assignment on a harmless field, upload of a benign type, SSRF (blind), webhook config, HTML injection in invite mail |
| **B — Bypass** | removal of a check that blocks the next hop | missing rate limit, account enumeration (unlocks spray), weak/absent OTP throttling, CORS reflect on a cookie endpoint, host-header trust, `redirect_uri` wildcard, unverified email change, captcha bypass, path canonicalization quirk, cache deception |
| **X — Amplifier** | turns a small primitive into many or into another actor's view | IDOR on a public object (→ enumerate to a private one), share-link reuse, impersonation/support-view, export ignoring filters, webhook/email relay using vendor infrastructure, notification to arbitrary recipient, cross-tenant identifier acceptance |

A Low with **no part label is not a Low — it is noise** (missing headers, clickjacking with no
state-changing target, `Server:` banner). Do not pad the ledger with it.

### The composition procedure (run at 0E, before any report is written)

```
1. INVENTORY   dump every L0/L1 signal into LOW_LEDGER.md — one row per signal:
               id | endpoint | observed | part(K/A/B/X) | what it would unlock | verified?
2. LABEL       assign each row exactly one primary part. Unlabelled → drop.
3. EDGES       for every pair, ask: does A's output feed B's requirement?
               (K → anything that needs an identifier; B → anything that needs volume/another
                actor; A → anything that needs a victim action or a server-side fetch; X → count)
4. SINK        find the terminal impact the graph reaches: ATO, cross-tenant data, fund movement,
               RCE, mass PII, privilege escalation. If no sink is reachable, the pool is honestly
               negative — record the graph and say which edge is missing.
5. PROVE       walk the composite end-to-end from a CLEAN session, 3×. Each hop gets its own
               artifact (request/response + state diff per redteam-mindset 3.4).
6. REPORT      ONE chain report. Title = terminal impact. Severity = terminal impact.
               Individual Lows appear as numbered steps, not as separate submissions.
```

### Composition patterns that reliably reach High/Critical

```
K + B + A + X   info-leak (K) → unthrottled enumeration (B) → unverified email change (A)
                → IDOR/export amplification (X)  =  mass ATO
A + B           CSRF (A) on a form whose only guard is a captcha you can skip (B) = state change at scale
K + A           version/stack leak (K) → CVE on that exact version (A) = RCE
A + X           open redirect (A) + share-link identifier reuse (X) = token exfil to attacker origin
B + X           missing rate limit (B) + account enumeration (B) + spray (A) = credential-stuffing ATO
A + K           self-XSS (A) + stored-unsanitised profile field (K = where it renders) = stored XSS
K + K + A       two leaks that together reconstruct a secret (key id + key material, tenant + token)
```

### Hard rules (this is where honesty lives)

1. **Severity = terminal impact, never the sum.** Three Lows do not "add up" to a Critical. If the
   chain only reaches Medium, it is Medium. Inflating is the fastest way to get a program to
   distrust every future report.
2. **Every hop needs an artifact.** A hop that is "probably possible" makes the whole chain
   UNPROVEN. Name it as the single unproven hop and say which credential/account would settle it.
3. **One dead hop kills that chain, not the pool.** Re-route through a different part; only after
   the re-route fails do you record the negative — with the fact that killed it.
4. **Do not report the parts as filler while the composition is unfinished.** A pile of Low
   submissions spends the program's patience and hides the High you were about to assemble.
5. **Composition must survive the vendor's own rubric.** Check the programme's severity table: if
   the terminal impact class is explicitly out of scope or N/A'd (e.g. DeFi "no fund-loss path"),
   the composition does not change that. Verify eligibility before investing in the proof.
6. **Same-root Lows collapse into one finding** (see `redteam-mindset` 3.3): if five Lows share one
   missing guard, that is one root cause with five proofs — a stronger single report, not five.

### Anti-patterns

| Wrong | Why |
|---|---|
| "I have 3 Lows, therefore High" | severity math without a sink |
| Chaining by assumption (no artifact per hop) | UNPROVEN, bounces at triage |
| Reporting each Low separately "to be safe" | fragments the chain, invites five duplicates |
| Building a chain that needs the victim to install malware / click twice with warnings | user-complicity caps severity on most programmes |
| Chaining across scope boundaries | the hop outside scope ends the chain — check scope first |

---

## Chain rule (operator-endorsed 2026-10-16)

Every finding must state its impact path. "X is exposed" without "and therefore an attacker
can Y" is unfinished. No impact path = hardening note, not a finding.

## Recon that leaks the attack surface itself (djangoeurope 2026-10-24)

The highest-value info-leak is not versions — it is an unauthenticated endpoint that hands the
attacker the **URLs of exposed services**. Chain it; never report the leak alone. Worked
example: `GET /server/` (no token) returned every shared server's hostname, exact stack
(Debian/Python/PHP/MariaDB/PostgreSQL versions), SSH host-key fingerprints, **and the DB-admin
panel URLs** (`phpmyadmin-sNN.wservices.ch`, `adminer-sNN...`). Those panels answered HTTP 200
to anyone, ran known-vulnerable versions (Adminer 5.2.1 < 5.4.3 → CVE-2026-56703 RCE +
CVE-2026-25892 unauthenticated DoS; phpMyAdmin 5.2.2 outdated), and I logged into one with
customer DB creds. So a "Low info disclosure" became **recon → exposed vulnerable service →
version/CVE → RCE/DoS**. Rule: when recon leaks a *service URL*, immediately fingerprint that
service (status + version + login reachability) and check its version against the CVE feed —
the leak's value is the target list it hands the attacker, and that IS the impact path. Then
drive to the ceiling and record what blocks the last hop (here: RCE needs DB creds on a server
you cannot reach; DB-user + shared-server isolation verified proper) as a proved/argued table.

## By-design skepticism for business-logic primitives (operator correction 2026-10-24)

Before claiming a "quota / limit bypass," answer TWO questions, not one:
1. **Capability-gain** (see authed-webapp-audit): does it let the attacker do something new?
2. **Is the field a security control or a config/allocation input?** A limit field that is
   *completely unvalidated* (no cap at all — `limit_ram=1000` accepted on a 2 GB plan) reads as
   a **per-user allocation input**, i.e. the group `limit_*` are defaults/hints, not hard quotas
   — that is by-design, not a broken control. A real bypass shows the server *tries* to enforce
   a hard entitlement and fails (clamps to a plan-derived ceiling you then exceed via race or
   override). Operator's tell: *"kan kuota nya 5 user, bisa jadi plan awalnya antara dibagi k 5
   user, atau 1 user dpt 5x kuota plan."* When intent is unprovable black-box, DOWNGRADE to a
   soft vendor question ("is this intended? if the group limits are hard quotas, this allows
   over-allocation") rather than submitting a "Medium bypass" that bounces as informative.

## Target-selection rules (operator standing rules, 2026-10-16)

1. **Self-hosted / self-disclosure targets only** (web2 + web3). Avoid platform-mediated
   programs (HackerOne / Bugcrowd / Intigriti / Immunefi forms) — operator finds submission
   friction high. Prefer `security.txt` / direct security e-mail / own disclosure form.
2. **Skip auth-core targets behind a paid subscription.** If the interesting surface needs a
   paywall, it is not worth the engagement.
3. **Get-past-gates is the agent's job** — do not ask the operator to solve egress / WAF /
   geo / account blockers. Solve them (WARP toggle, egress rotation, headful CDP,
   disposable accounts) and report what was done.
4. **Stay inside the declared scope mid-hunt — don't wander to sibling/tenant domains.**
   A SaaS bounty scope is often the marketing/support domain (`*.vendor.com`) while the
   data-rich product runs on tenant subdomains (`*.vendor.app`, `*.product.io`,
   `*.customer.<vendor>.tld`) that are OUT of scope. Operator correction (2026-10, Zenya):
   "pokus d <scope> aja, gkush kemana2." Map the scope boundary BEFORE hunting. A platform
   bug found on an out-of-scope tenant is still the vendor's code (report via their CVD)
   but flag the scope nuance — and NEVER treat a customer tenant as an authorized test
   target: you cannot self-provision there and it is a third party's production system
   (a hospital, a bank). If authenticated impact needs an account you can't legitimately
   create in-scope, say so; do not fabricate the breach.

## White-box beats black-box for our stack

Proven High/Critical findings came from **source review** (Hedera BLS no-op, TrustLend
insolvency, DeXe double-reward), not scanning. When a target has a public repo, SDK, or
auditable contract, weight white-box: `semgrep`, `gosec`, `bandit`, `gitleaks`,
`trufflehog`, `slither`/`aderyn`/`mythril` (web3), plus reading the auth / payment / webhook
paths by hand. Scanning a hardened SaaS perimeter is the lowest-yield activity available.

## Retired identifiers still accepted (the recon-leak → money chain)

The highest-yield chain that does **not** need a second bug: a historical URL leaks an
identifier the backend still honours after it was removed from the public catalogue.
`gau` / `waybackurls` on the target routinely surface `plan_id`, `price_id`,
`referral_code`, `coupon`, `feature_flag` and `variant` parameters in archived URLs.
Those ids are usually still live in the vendor's payment/entitlement system even when the
UI no longer offers them.

Worked example (Hivenet, 2026-10-26): `gau` on app.hivenet.com returned an archived URL
carrying `?plan_id=price_1OyEzIHCnr9Hivhnd4kjZ7nw`. That id was absent from
`GET /plans/stripe/public` (9 plans), yet `POST /subscriptions/stripe` accepted it and
returned a live Stripe checkout session. Rendering that session showed the product was
"1000GB Easter Offer" at EUR 1.00/month, against a published EUR 699/month for the same
1024 GB — a 99.86% discount with a publicly discoverable id. Three separate accounts
reproduced it. Full recipe, the checkout-verification steps and the honesty framing:
`references/retired-identifier-chains.md`.

The general shape to run on every target:
```
gau/waybackurls <host>  ->  collect every ?param=value that looks like an identifier
  -> is that id still in the public catalogue?      (usually NOT — that is the point)
  -> does the write/checkout endpoint still accept it?   (existence check vs entitlement check)
  -> what does the vendor actually sell for it?    (render the checkout / read the response)
  -> repeat from 2-3 separate accounts              (3x rule)
```
The root cause is almost always the same: the backend validates that the identifier
*exists* (a Stripe lookup, a DB row) but never that it is *currently offered*. Say that
sentence in the report — it is what makes the finding land.

## Measurement artefacts that fake a negative

Two ways a chain gets wrongly closed this session, both worth a pre-flight check:

1. **A count read off `ls -la`.** `ls -la | awk '{print $5,$9}'` prints *bytes* then name.
   I reported "792 URLs crawled" from that output when the file held 16 lines. Always
   `wc -l` before quoting a count, and re-read the number from the command that counts.
2. **A mailbox search with a fixed window.** A verification script that fetched "the last
   8 messages" reported `mail to third party: False` and `successful trials: 0 of 2` while
   the e-mails were in fact delivered — the inbox was full of unrelated verification codes
   and the target mail sat outside the window. Search by criteria
   (`AND(from_="vendor.com")`, subject fragment), never by recency, and if a negative
   depends on "I did not find X", re-run the search a second way before recording it.

Both are the same failure the section above warns about: an artefact that *looks* like a
verified negative but is a measurement error. If a negative rests on "not found", name the
search that was run and its window.

## Automation — `chain_builder.py` now speaks K/A/B/X (2026-10-30)

The part labels above are not just prose. `scripts/chain_builder.py` (Phase 0C-C7) carries the same
model so the composition step is mechanical, not vibes:

- `KABX_PARTS` — regex sets for K / A / B / X, applied to each finding's text.
- `KABX_PATTERNS` — the eight proven composition patterns, each with the parts it needs.
- `classify()` now returns `parts` and `reachable_patterns` per finding.
- Output shows `part:K/B/A/X` and `pattern:<name>` per finding, so a Low with **no part label is
  visibly NOISE** instead of silently padding the ledger.

Run it at 0C-C7:

```bash
python scripts/chain_builder.py findings.json            # console
python scripts/chain_builder.py findings.json --goal account_takeover --json out.json
```

**Regression fixture (run after any classifier edit):**
`scripts/check_chain_builder_fixture.py` — 6 findings with known-correct labels, asserts
present/absent + goal + part + dead per row. Found all three bugs below in ~2 minutes. Use it
instead of debugging the classifier against a live engagement, where a script bug is
indistinguishable from a target behaviour.

**Two bugs fixed while wiring this in (recorded as lesson 216) — check they stay fixed:**

1. **`dead` regex matched the bare word `unverified`.** A real primitive — *"unverified email
   change"*, i.e. the address was never verified — was flagged DEAD and silently dropped from every
   chain. Only `unverified finding` / `finding is unverified` should mark dead. **Symptom to watch
   for: a known-good ATO primitive vanishing from the chain output.**
2. **`GOALS` had no pattern for the ATO sink.** `unverified email change`, `password reset →
   arbitrary`, and `credential stuffing` produced no `account_takeover` goal, so chains that should
   terminate in ATO terminated nowhere. If a chain ends in `pii` when you expected `account_takeover`,
   check the goal patterns first.

### The silent-drop class — automation that deletes valid findings without erroring

The two bugs above are instances of a **failure class**, not one-off typos. It generalises to every
regex/classifier/gate in the pipeline (`chain_builder.py`, `weaponize-gate.py`, `triage_gate.py`,
`aggregate-findings.py`), and it is more dangerous than a crash:

> **A crash is visible. A silent drop is not.** A regex that over-matches removes a real finding
> from the output, the run exits 0, and the report is quietly short one Critical.

The shape: a **lexical collision** between the word that marks a finding as dead and the same word
appearing inside a *live primitive's name*.

| Marker intent | Live primitive that contains the same word |
|---|---|
| `unverified` → finding not proven | **"unverified email change"** = the address was never verified → the ATO primitive itself |
| `theoretical` → no PoC | "theoretical" appearing in a quoted vendor reply or a doc citation |
| `could not confirm` → dead | a finding whose *description* quotes a negative control ("could not confirm on v2, confirmed on v3") |

**Rules that prevent it:**

1. **Dead markers must be phrases about the FINDING, never bare adjectives.** `unverified finding`,
   `finding is unverified`, `not reproducible`, `no repro` — not `unverified`, not `theoretical`.
2. **A known-good primitive must appear in every regression fixture.** Keep a fixture file of
   primitives you have personally proven (unverified-email-change ATO, IDOR read, missing rate
   limit, session-not-invalidated). If any of them ever vanishes from the output, the classifier
   regressed — fix the classifier, do not re-hunt the bug.
3. **Diff the finding COUNT in vs out, every run.** `chain_builder.py` prints
   `# CHAIN BUILDER — N finding(s)`. If N < the number of rows you fed it, something was dropped.
   Print the dropped titles, not just the count.
4. **Test the classifier with a fixture BEFORE trusting it on a live engagement.** See below.

### Regression-test the pipeline with a synthetic fixture (the technique that found all three bugs)

Do not debug a pipeline script against a live engagement — you cannot tell a script bug from a
target behaviour. Build a small fixture whose correct answer you already know, run the script on it,
and assert the expected output. This took ~2 minutes and found three real bugs.

Fixture design (6 findings, each with a known-correct expected label):

```json
[
 {"id":"F1","title":"User enumeration via differential login error","severity":"low",
  "description":"Existing user returns 'incorrect password', unknown user returns 'invalid request'."},
 {"id":"F2","title":"No rate limit on /api/v1/auth/login","severity":"low",
  "description":"30 concurrent requests all returned 200, no 429."},
 {"id":"F3","title":"Unverified email change","severity":"medium",
  "description":"POST /api/account/email changes the address without verification token."},
 {"id":"F4","title":"IDOR on /api/users/{id}/export","severity":"medium",
  "description":"Export ignores tenant filter; cross-tenant identifier acceptance."},
 {"id":"F5","title":"Missing X-Frame-Options header","severity":"info",
  "description":"Header absent on login page."},
 {"id":"F6","title":"Theoretical SSRF","severity":"low",
  "description":"Could not confirm; precondition not met."}
]
```

Expected, and what the broken script actually did:

| # | Expected | Broken behaviour | Bug |
|---|---|---|---|
| F1 | `part:K`, in a chain | `part:K` ✓ | — |
| F2 | `part:B`, in a chain | `part:B` ✓ | — |
| F3 | `GOAL:account_takeover`, `part:A`, **in a chain** | `DEAD`, **dropped** | dead-regex collision |
| F4 | `GOAL:pii`, `part:X` | ✓ | — |
| F5 | **absent** (noise) | absent ✓ | — |
| F6 | `DEAD`, excluded from chains | `DEAD` ✓ | — |

Assert on all four axes per finding: **present/absent**, **goal**, **part**, **dead**. A fixture that
only checks "did it run" catches nothing.

Keep the fixture next to the script (`scripts/fixtures/`) and re-run it after any edit to the
classifier. Same discipline as the positive control in `fuzzing-false-negative-pitfalls`: a tool that
produces no output is not proven correct until you have shown it *can* produce output.

## Related

- `exploit-cookbook` — proven per-bug playbooks (the *how* of a specific chain).
- `references/patch-lag-and-leaked-host-chains.md` — **the two chain families that beat the Low
  ceiling on a hardened estate**: (1) the *patch-lag differential* — enumerate prod/beta/test siblings,
  diff versions against the vendor's GitHub release feed, and use "test is patched, prod is not" to
  prove a missed rollout rather than an intentional pin; (2) the *leaked-host chain* — sweep every live
  root for public OpenAPI specs, extract `servers[].url` and every absolute host, RDAP-check ownership
  against the vendor's own domain, and check whether the host is already claimed by another researcher
  before drafting. Also carries the **bogus-path control** that decides "unauth" vs "auth-before-routing"
  in one request, and the 7-primitive/1-completion result distribution that keeps the ledger honest.
- `references/authz-gap-sibling-and-consumer-chaining.md` — **the two moves that turn a Low
  authorisation primitive into High**: (1) enumerate the sibling API generations and same-shaped
  endpoints, because the legacy route usually lacks the ACL the rewrite added; (2) chain the
  identifier you control to a *consumer* that amplifies it (vendor e-mail, webhook, notification).
  Worked Hivenet chain: missing ownership check on `POST /metadata` → vendor mails an arbitrary
  third party → third party derives the key and decrypts the victim's file. Includes the named
  patterns (claim-then-lock, public-identifier-as-capability, vendor-infrastructure amplification,
  key-derivation-from-public-metadata), the correct way to verify an async mail hop, and the chain
  tables for the two chains that died with the verbatim fact that killed each.
- `triage-validation` — 7-question gate before any finding is reported (**user-owned**).
- `bug-bounty` — the 0A-0F pipeline router (**user-owned**; adopt via
  `hermes curator adopt bug-bounty` to edit it directly).
- `api-authz-probe-ordering` §4 — the full DeFi vendor-N/A pattern with verbatim vendor replies,
  the "on-chain discoverable" rebuttal, and the read-the-reply-email-first rule. Read it before
  any API authz work on a fund-loss-scoped protocol.
- `references/cve-fixline-sweep.md` — **chain family 3**: compare every host's advertised version
  against a CVE fix release and enumerate the affected set. Carries the `httpx -tech-detect` parse,
  the version-tuple comparison (string compare lies: `"1.9.0" < "1.31.0"`), the NVD API query for
  fix-line + CVSS + verbatim description, the live-header verification step, the report table shape
  that reads as urgent rather than as a scanner dump, and the RoE stop. Worked: 34 Telekom hosts
  below nginx 1.31.0 → CVE-2026-42945 (CVSS 8.1). Also the product-edition trap (AEM Forms on JEE
  ≠ AEM Sites on Cloud Service) and the `--check`-mode-is-destructive rule.
