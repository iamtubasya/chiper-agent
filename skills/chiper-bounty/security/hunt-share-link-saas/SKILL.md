---
name: hunt-share-link-saas
description: Hunt access-control bugs on share-link/file-sharing SaaS.
metadata:
  hermes:
    tags: [security, bug-bounty, access-control, share-links, saas, idor, privacy]
version: 1.1.0
author: "Qwen (curator)"
license: MIT
---

# Share-Link / File-Sharing SaaS — access-control hunting

For products whose **core CIA surface is a link**: screenshot & screen-recording tools with a
cloud, WeTransfer-alikes, pastebins, document sharing, expiring links, password-protected
shares, and custom-domain sharing.

## When to use

- The product's main feature is "capture/upload something, get a link"
- The policy or bundle mentions `share`, `link`, `expire`, `password protect`, `custom domain`
- You see a short-link host (`cln.sh`, `s.`, `share.`) or a `*.cloud` wildcard in scope
- The API has a per-item `privacy` / `visibility` / `comment` setting

**Why this is its own class:** the object is public-by-default and the product's whole value
is making it selectively private. That means the access-control state machine is the product,
not a side feature — and it is where the money is. A generic IDOR sweep misses it because the
interesting question is not "can I read another user's object" but "does the *gate the owner
set* actually hold".

## The core insight — extract the state machine, then test every state

Do not start by guessing endpoints. The minified bundle contains the **enum literals for every
access-control state the product has**, and each one is a differential you must run.

```bash
grep -oE 'case`[a-z_]+`:return`[^`]+`' bundles/*.js | sort -u
```

Measured on a live screenshot/cloud SaaS (2026-10-26) this yielded, in one pass:

| enum | states | what it gates |
|---|---|---|
| `privacy_settings` | `everyone` · `password` · `team` · `private` | who can view the item |
| `comment_settings` | `everyone` · `team` · `disabled` | who can comment |
| `expire_after` | integer days | when the link dies |

**That table is the test plan.** For each state: owner sets it on their own item, then you
attempt the read as (a) another authenticated user, (b) an anonymous viewer, (c) the owner's
own teammate if `team` is in play. Four states × three viewers = the matrix. Without the enum
extraction you test one thing ("can I read it"); with it you test twelve.

## The differential matrix

Run every cell and record status **and body sha256** — a 200 with an identical body to the
public baseline is not a bypass.

| owner sets ↓ / reader → | anon | other user | teammate | owner |
|---|---|---|---|---|
| `everyone` | 200 (correct) | 200 (correct) | 200 | 200 |
| `password` | **must 401/403** | **must 401/403** | 401 unless password given | 200 |
| `team` | **must 401/403** | **must 401/403** | 200 (correct) | 200 |
| `private` | **must 401/403** | **must 401/403** | **must 401/403** | 200 |
| `everyone` + expired | **must 401/403/410** | same | same | owner may still see |

**The `team` row is the highest-value one and the most commonly wrong.** It requires a second
account that is *not* in the owner's team, plus a third that *is* — or at minimum the second
account plus confirmation that the team roster is server-derived. A `team` gate that any
authenticated user passes is a cross-tenant read.

**The expired row is the second highest.** Expiry is usually enforced at read time by
comparing `expires_at` to now; the classic bug is that the check exists on the *view* path but
not on the *direct asset* path (the CDN/S3 object URL keeps working forever). Always test the
raw asset URL, not just the share page.

## Short-link hosts — entropy and enumeration

Products in this class almost always ship a short-link host (`cln.sh`, `s.<prod>.com`). Two
things to measure:

1. **Is the host actually the app, or a catch-all?** sha256 the body against the apex.
   Measured 2026-10-26: `cln.sh/` returned the 174,869-byte marketing shell and **404'd on
   every path** including `/robots.txt` — the real viewer is an SPA route on the main host,
   not a path on the short host. Don't burn probes on a host that only serves marketing.
2. **Link ID shape.** Request a real link from your own account and measure: length, charset,
   whether it is sequential or random. Sequential/short IDs on a link that gates private
   content is a finding on its own. Random IDs are not enumerable — but see the harvest note
   in `hunt-idor` (published/archived URLs are the supply, not brute force).

## The Vite config block is the app's whole contract — read it before anything else

A Vue/Vite SPA ships its entire client configuration in one inline `<script>` in the
HTML shell. One `curl` of the SPA route gives you the API base, the CAPTCHA site key,
the custom-domain records, and the payment vendor — before you touch a single endpoint.

```bash
curl -s https://<host>/<spa-route> | grep -o 'window\.VITE_[A-Z_]*'
```

Measured on a live screenshot/cloud SaaS (2026-10-26), the shell at `/cloud` carried:

```
window.VITE_API_URL                  = '/api/'                      <- the real API base
window.VITE_APP_URL                  = '/cloud/'
window.VITE_CLOUDFLARE_TURNSTILE_KEY = '0x4AAAAAABd5EOgqgLEfjQgO'   <- Turnstile sitekey
window.VITE_CUSTOM_DOMAINS_CNAME     = 'cname.<prod>.cloud.'
window.VITE_CUSTOM_DOMAINS_A         = '75.2.85.205'
window.VITE_PADDLE_VENDOR_ID         = '130946'                     <- payment vendor
window.VITE_PADDLE_SANDBOX           = false
```

Three things this settles in one request:

1. **The API base is relative** (`/api/`), so the API lives on the *same origin* as the SPA —
   no separate `api.*` host to discover, and every unauth probe is a same-origin request.
2. **The Turnstile sitekey tells you signup is gated** before you waste a round on a bare
   POST (which returns `422 cf_turnstile_response required`).
3. **The custom-domain CNAME/A pair** is exactly what the claim check needs — see the
   custom-domain section below.

Then pull the asset URLs out of the same shell (`<link href>` / `<script src>`) and grep
the chunks for the endpoint surface. These bundles are large (measured: 340 KB main +
962 KB utils) and **source maps are stripped** (`*.js.map` → NoSuchKey, no
`sourceMappingURL`) — so the endpoint map comes from grepping the built code, not from a
map. Pattern that works on minified Vue bundles:

```bash
grep -oE '\.(get|post|put|patch|delete)\(\s*[`"'"'"']([^`"'"'"']{1,70})[`"'"'"']' main-*.js | sort -u
```

Measured yield: 85 unique call sites, ~30 real endpoints after filtering framework noise
(`sentry-trace`, `content-length`, `X-Amz-Expires`, VTT cue fields). The signal is in the
*path shape* — `media/${id}`, `team/members/${id}/cancel-email-change`,
`mediaview/authorize` — not in the verb list.

**The privacy/comment/expiry enums live in the same bundle** (see the core insight above),
and on this target the enum→label map was a single `switch` returning
`Anyone with the link` / `Password protected` / `Team members only` / `Only me`.

## Custom-domain claim — the Pro-tier bypass

Most of these products sell "connect your own domain" as a paid feature. The config block
usually leaks exactly what the claim check needs:

```
VITE_CUSTOM_DOMAINS_CNAME = 'cname.<prod>.cloud.'
VITE_CUSTOM_DOMAINS_A     = '75.2.85.205'
```

Test, in order:
1. **Is the Pro gate server-side?** Submit `custom_domain` from a free account. If accepted,
   that is an entitlement bypass (`saas-plan-entitlement-audit`).
2. **Can you claim a domain another tenant already connected?** The interesting bug is not
   "I connected my own domain" (that's the feature) but "I connected *someone else's* domain"
   — a claim check that only verifies DNS resolution, not ownership. **Do not complete a claim
   on a domain you don't own**; prove the missing ownership check by observing that the
   verification step accepts a domain you control the DNS for but have no rights to, or that
   the API returns the existing tenant's config for a domain you supplied.
3. **Subdomain vs apex handling** — the config distinguishes `CNAME` (subdomain) from `A`
   (apex). Test whether the apex path skips a check the subdomain path enforces.

**Scope note:** the policy usually excludes "custom domains of other customers that you did
not connect yourself" from *testing*, but proving a claim bypass is in scope. Prove the
missing check without touching a live third-party domain.

## Upload / import sinks

These products accept files, and frequently accept **URLs** (import from a link, embed,
screenshot a webpage). That makes every one of them an SSRF and file-handling surface:

- **URL import / webpage capture** → SSRF. Test with `169.254.169.254`, `localhost`, and a
  DNS-rebinding host. See `hunt-ssrf` for the 2026 DNS-rebinding pattern.
- **SVG upload** → XXE *and* stored XSS. SVG is XML.
- **Filename in `Content-Disposition`** → response-header injection; see `hunt-idor` Chain 2.
- **Path traversal in filename** → write outside the upload dir.
- **Content-Type confusion** → an HTML file served from the asset host is stored XSS on the
  product's origin.

## The auth model is a Bearer JWT in localStorage — not a cookie session

Measured on a live share-link SaaS (2026-10-26): `POST /api/auth/login` returns
`{"data":{"token":"<JWT>"}}` and the SPA mirrors it into `localStorage["state.token"]`.
The token is RS256, ~1000 chars, claims `aud:1 / sub:<user id> / scopes:["dashboard"]`,
~1-year expiry. There is **no session cookie** — `set-cookie` is empty on the login response.

Consequences for the hunt:

- **Every authenticated probe is `Authorization: Bearer <token>`**, harvested from the
  browser's `localStorage` after a real login (see `browser-cdp-auth-audit`). A cookie-jar
  replay returns 401 and reads like an authz failure when it is a transport mismatch.
- **`/api/user` is the identity oracle.** It returns `id`, `role`, `team`, `storage`
  (`limit_bytes`, `used_bytes`), `media_count`, and `avatar_url` — one call that both
  confirms which account you are and maps the entitlement surface.
- **The unauth boundary is uniform.** Measured: `GET /api/{user,team,media,team/billing,
  team/sso,team/scim,user/tags,user/clients,notifications,team/invite/*}` all return the
  identical `401 {"message":"Unauthenticated."}` — no oracle, no per-endpoint variance.
  `GET /api/changelog` and `/api/maintenance` are the only unauth 200s, and both are
  public content. Record that uniformity as a verified negative; it is what makes the
  authenticated findings credible.
- **`POST /api/mediaview/authorize` is an OAuth-style consent endpoint** and the SPA's
  `OauthAuthorizePage` posts `{approved:false, redirect_uri, code_challenge}` to it. It
  answers 401 for every payload shape when unauthenticated (tested 9 shapes: `hash`,
  `media`, `media_hash`, `id`, `slug`, `code`, `token`, `url`, and the exact consent
  shape) — so the `redirect_uri` validation is only reachable **with a session**. That is
  where the open-redirect/OAuth-theft test belongs, not on the unauth path.

## The media item is app-only — plan the privacy matrix around it

Measured 2026-10-26: `POST /api/media` returns **405** (`Supported methods: GET, HEAD,
DELETE`). The web SPA uploads only `avatar` (→ `POST /user`), `logo` and `favicon`
(→ `POST /team`), all `multipart/form-data`, all ≤4 MB. **Nothing in the web API can create a
media item** — that path belongs to the desktop client.

Consequence: the differential matrix in the core insight above is **blocked until you have a
media item**, and no amount of authenticated probing will unblock it. Two ways forward, in
order of preference:

1. **Find the client's upload endpoint.** Grep the desktop binary for `/v1/` and for
   `upload`/`media`/`attach` — the client API is usually a separate surface on a separate host
   (measured: `api.<vendor>.cloud/v1/client/{activate,appcast,check,check-for-updates,migrate,unlink}`).
   A `/v1/client/check-for-updates` that answers `422 version field is required` unauthenticated
   is a live, probeable surface the web audit never touches.
2. **Use the multipart endpoints that DO exist** (`avatar`, `logo`, `favicon`) to at least
   exercise the file-handling classes — extension/MIME/content-type confusion, path traversal
   in filename, SVG → XXE/XSS — even though they do not gate the share-link state machine.

Until one of those lands, the honest status for the privacy/expiry matrix is
`BLOCKED — no media item creatable via web API`, with the 405 as evidence. It is **not**
"privacy controls hold" — you have not tested them.

## The desktop-client API is a second surface on a second host

These products ship a Mac/Windows app, and the app talks to its own API — not the SPA's.
Measured 2026-10-26: the app binary's string heap exposed
`/v1/client/{activate,appcast,check,check-for-updates,migrate,unlink}` on
`api.<vendor>.cloud`, a host the web recon never surfaced because the SPA's
`VITE_API_URL` is same-origin (`/api/`).

Grep the binary for `^/(api|v1|v2|v3)/` and for `appcast` before concluding you have mapped
the API. Two of those endpoints were reachable unauthenticated (`check-for-updates` → 422
asking for `version`; `appcast` → 200 with the full feed). That is a legitimate in-scope
surface when the policy names the desktop app, and it is where the update-integrity work
lives — see `desktop-app-analysis` §2 for the two-feed pattern and the Sparkle
verification discipline.

### The license-activation endpoint is the highest-value unauth surface on that host

`POST /v1/client/activate` was reachable **without any authentication** and enumerated its
own schema in one request. Measured 2026-10-26:

```
POST /v1/client/activate  {}
→ 422 {"message":"The code field is required. (and 6 more errors)",
       "errors":{"code":…,"verification":…,"serial":…,"app_version":…,
                 "os_version":…,"hostname":…,"nonce":…}}
```

Seven required fields. `code`, `serial` and `nonce` must each be **exactly 32 characters** —
the validation error says so, which is a free schema disclosure. Then the interesting part:

| probe | result | reading |
|---|---|---|
| well-formed 32-char values | **404 with an empty `message`**, nonce **echoed verbatim** | passes validation, fails lookup with no information |
| different `code` values | **byte-identical** responses | **no license-validity oracle** |
| 20 well-formed attempts | all 404, **no 429** | no rate limit on the activation path |
| identical request replayed | byte-identical response | nothing to replay *into* |

**The nonce is 100% client-controlled and echoed back** — there is no server-issued nonce,
so the endpoint has no replay protection of its own. But because every response is an
undifferentiated 404, there is no oracle and no observed state change: this is a **negative
with evidence**, not a finding. The one angle that remains open is whether a *valid* code
produces a different response — which requires buying a license, i.e. out of scope.

**Generalizable pattern:** a validation-before-lookup endpoint that is unauth-reachable
enumerates its own field schema for free. Run `{}` first, read the `errors` map, then probe
with well-formed values to reach the real logic. Record the differential (or its absence)
as the control. The echoed client nonce is worth stating explicitly — it tells you the
endpoint has no server-side anti-replay, which matters the moment any oracle appears.

### `check-for-updates` — version comparison is a clean oracle, and a soft-404 trap

`GET /v1/client/check-for-updates?version=<v>` (POST → 405, GET only):

| input | response |
|---|---|
| `4.8.11`, `5.0.1`, `5.0`, `5` | `200 {"new_version_available":true,"can_update":true}` |
| `5.0.2` (current) | `200 {"new_version_available":false}` |
| `0.0.1`, `5.0.3`, `6.0.0`, `99.0.0`, `v5.0.2`, `0x5.0.2`, `-1`, `null`, `true` | **200 + the 174,869 B SPA HTML shell** |

Two lessons: (a) **whitespace is trimmed** — `" 5.0.2"`, `"5.0.2 "`, `"5.0.2\n"` all return
`new_version_available:false`, so there is no parser-confusion angle there; (b) an invalid
version returns the **marketing shell**, not a JSON error — that is a soft-404 shape and must
not be read as "the endpoint accepts anything". Compare byte length, not status code.

### The URL-scheme consent gate — map the flags, then say what you could not test

When the app registers a custom scheme (`cleanshot://`), the binary tells you whether the
dangerous capability is opt-in. Grep for the persisted flag names and the dialog strings:

```
allowURLSchemesAPI          <- the opt-in flag (off by default)
didAskAboutURLSchemesAPI    <- consent already asked/remembered
"CleanShot has received a command request from an external app…"
"Disable this option to prevent external apps from controlling CleanShot via URL scheme API"
```

**An explicit consent flag + modal prompt is the correct design — record it as a control
holding.** The residual questions (can the flag be pre-set by another local process? can the
dialog be bypassed?) require a macOS host; write them as `NOT TESTED — requires macOS`,
never as a negative and never as a finding. The scheme's command verbs are usually
Swift-symbol-mangled and not extractable as plain strings, and the public API docs page
often 404s — so the verb list is genuinely unknown without the platform.

## Turnstile-gated signup — SeleniumBase Pure CDP solves it without help

Measured 2026-10-26 on this class of target: the register form renders four genuinely
visible inputs (`#name`, `#email`, `#password`, `#password_confirmation`) plus `#terms`,
and a hidden `input[name="cf-turnstile-response"]` that is **already populated** when the
page finishes loading. No honeypot, no off-screen decoy, no cross-origin challenge iframe.

So the whole account-provisioning problem collapses to: `start_browser` (headed) →
`open_url /cloud/register` → `find_elements "input"` → confirm the token is non-empty →
`type_text` × 4 → `click_element "#terms"` → `click_element "button.action-button.-primary.submit"`
→ wait → read the body text for "Verify your email".

Then the confirmation mail is a **plaintext link**, not a code:
`https://<host>/cloud/confirm?token=<36 chars>`, from `<product> Cloud
<account@<prod>.cloud>`. Navigate it in the same browser and the account is active and
logged in. Pull the token from `localStorage["state.token"]` and you have both accounts
for the cross-account matrix.

**Do not conclude "signup blocked" before checking the hidden field.** A bare
`POST /api/auth/register` returns `422 cf_turnile_response required`, which looks like a
hard gate — it is only a gate for non-browser clients.

## The WAF throttles the *scripted* path, not the browser path

After the browser logins succeeded, plain `urllib` calls to `/api/auth/login` and the SPA
login page began returning **HTTP 429** with
`We detected unusual traffic from your network... Error ID: AWS-WAF-CLOUDFRONT`. This is
edge throttling keyed on request shape/volume, not an application control.

Rules that follow:

- **Harvest tokens from the browser, then probe with browser-identical headers.** The
  earlier failure was header-shape based, not token based. Send `Origin`, `Referer`,
  `Accept-Language`, `sec-ch-ua`, `sec-ch-ua-mobile`, `sec-ch-ua-platform`,
  `Sec-Fetch-Dest/Mode/Site` alongside `Authorization: Bearer <token>`.
- **Treat 429 as REWORK, never N/A** (`bot-protected-target-testing`). Wait out the
  cooldown (~15–30 min, zero requests) and resume from the trusted browser context.
- **Do not read the WAF page as app behaviour.** A 429 body naming the CDN says nothing
  about the API's authz.

## Update-feed integrity — the appcast vs the artifact you actually serve

When scope includes the desktop app (this class of product almost always ships a Mac app),
the update feed is an in-scope supply-chain surface. Measured 2026-10-26:

- `/v3/appcast.xml` → 200, 35 KB, 30 `<item>`, **74 `<enclosure>`**.
- **Every enclosure is signed** — 0 unsigned. 60 carry `sparkle:dsaSignature` (legacy DSA),
  14 carry both `dsaSignature` and `sparkle:edSignature` (Ed25519). That is a control
  holding, and it is worth recording as a verified negative.
- `PUT` to the feed → **403** (not writable). Also a control holding.
- **The discrepancy worth chasing:** the newest appcast item is **3.7.1, dated 27 May
  2021**, while `/v3/CleanShot-X-latest.dmg` returns 200 with
  `Last-Modified: <today>` and **50,445,640 bytes — a size matching no enclosure in the
  feed** (nearest declared length is 27.4 MB, roughly half).

**What that means and what it does not.** It means the feed and the served artifact have
diverged: a client trusting the appcast would never be offered the current build, and the
artifact actually being served has no appcast entry whose signature covers it. It does
**not** yet mean an attacker can serve a malicious update — proving that requires showing
the app resolves updates through a path that skips signature verification.

The two checks that decide it, in order:
1. **Does the app actually consume this feed?** Grep the app binary/bundle for the appcast
   URL and for `SUFeedURL` / Sparkle framework strings. If the app points elsewhere, the
   stale feed is a hygiene issue, not a finding.
2. **Does the update path verify?** If the app fetches `latest.dmg` (or any URL) and
   installs without checking `sparkle:edSignature` against the embedded public key, that
   is the supply-chain finding. If it verifies, the divergence is a maintenance bug.

Report it as `UNPROVEN-IMPACT` until step 2 is answered — see the reporting bar in
`authed-webapp-audit`. Also record the honest negatives you already have: all enclosures
signed, feed not writable, no unsigned-artifact path found.

## Storage bucket — verify the lock, don't assume it

An in-scope page or API response that names an S3/GCS bucket gives you a legitimate asset to
test. Run the full matrix, not one probe: 13 bucket operations (list/ACL/CORS/policy/
location/versions/logging/lifecycle/website/uploads), an object-level differential (known
public object vs guessed vs prefix listing), and an **anonymous PUT with a unique marker that
you then delete**. Full recipe:
`unauth-surface-discovery` → `references/s3-bucket-lock-verification.md`.

**403 AccessDenied ≠ 404 NoSuchBucket.** Record the XML `<Code>`, not just the status line.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Baca blok config Vite (`window.VITE_*`) + grep endpoint dari chunk bundle | Satu request memberi API base, sitekey CAPTCHA, record custom-domain, vendor bayar |
| 2 | Ekstrak enum state machine dari bundle (`case\`…\``) | Tanpa ini kamu cuma tes "bisa baca", bukan semua gate |
| 3 | Matriks differential: tiap state × anon/user/teammate/owner | Inti kelas ini — gate yang di-set pemilik harus berlaku |
| 4 | Expiry: item kedaluwarsa dibaca via halaman share **dan** via URL aset mentah | Cek expiry sering ada di view path, tidak di aset path |
| 5 | Short-link host: sha256 body vs apex + ukur entropy ID link | Host bisa jadi catch-all; ID sekuensial = temuan sendiri |
| 6 | Custom-domain claim dari akun gratis + uji domain yang tidak kamu miliki | Entitlement bypass + cek kepemilikan yang hilang |
| 7 | **Integritas update feed**: bandingkan item terbaru appcast vs `Last-Modified`/ukuran artifact `latest` | Feed basi + artifact tak tercakup tanda tangan = kandidat supply-chain |
| 8 | **Bucket matrix lengkap** (13 operasi + object differential + PUT anonim bertanda) | Satu probe 403 bukan bukti terkunci |
| 9 | **`POST /api/media` — bisa tidak buat item via web API?** | Kalau 405, matriks privacy/expiry TERBLOKIR; cari endpoint upload klien desktop |
| 10 | **Grep biner aplikasi desktop untuk `/v1/` + `appcast`** | Permukaan API klien di host lain; sering unauth-reachable dan punya feed update sendiri |
| 11 | **`POST /v1/client/activate` dengan `{}` lalu nilai 32-karakter** | Endpoint aktivasi lisensi unauth: enumerasi skema gratis, lalu cek oracle validitas + rate limit + echo nonce |
| 12 | **`GET /v1/client/check-for-updates?version=` dengan versi valid & tidak valid** | Oracle perbandingan versi; input invalid sering balik shell HTML (soft-404), bukan error JSON |
| 13 | **Grep biner untuk flag konsen URL-scheme + string dialog** | Menentukan apakah kapabilitas berbahaya opt-in (kontrol bekerja) atau default-on (temuan) |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang dengan akun gratis bisa membaca
   capture milik pengguna lain yang di-set `private`, karena gate hanya memeriksa sesi ada,
   bukan kepemilikan objek" — tunjukkan request dan respons yang memuat data korban.
2. **Apa yang hilang dari korban?** Konten yang di-set privat: screenshot, rekaman, dokumen.
   Sebutkan jenis konten dan bahwa gate yang dipilih pemilik tidak berlaku.
3. **Bisa direproduksi 10 menit dari nol?** Dua akun, satu item, state yang di-set, request
   lintas-akun. Sertakan sha256 body supaya selisihnya terukur.

## Eskalasi wajib

**Primitif:** baca/tulis objek yang gate-nya di-set pemilik tidak berlaku

**Teknik pengembangan:** baca item privat → eksfil konten; tulis/rename/hapus item orang lain
→ integritas; klaim custom domain tenant lain → takeover hosting di domain tepercaya;
URL import → SSRF ke metadata cloud; SVG upload → XXE/stored XSS

**Eskalasi ke:** `hunt-idor` · `hunt-ssrf` · `hunt-xxe` · `hunt-xss` · `saas-plan-entitlement-audit`

**Depth target:** L2 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5).

## Pitfalls

- **A 200 on the share page is not a bypass.** Diff the body against the public baseline; a
  SPA shell or a "password required" interstitial both return 200.
- **The short-link host is often not the app.** sha256 against the apex before probing paths.
- **`team` needs a real second account with real state.** An empty result is
  indistinguishable from an ownership check until the victim owns something — seed it first.
- **Expiry on the view path says nothing about the asset path.** Test the raw object URL.
- **Do not complete a custom-domain claim on a domain you don't own.** Prove the missing
  ownership check; don't take over a live third-party domain.
- **Delete every marker object you create** in a bucket write probe. State you created on
  someone else's infrastructure is not a PoC.
- **Read the program's not-paid list before drafting.** This class of vendor routinely
  excludes rate limiting, user enumeration, missing headers, session behaviour by design, and
  "unsafe token storage without a practical attack" — so a finding that only demonstrates one
  of those is worth $0 no matter how clean the PoC is.
- **A 429 from the CDN is not an app response.** `AWS-WAF-CLOUDFRONT` / "unusual traffic"
  bodies say nothing about API authz. Wait out the cooldown and resume from the browser
  context; never downgrade to curl-only because of it, and never record it as N/A.
- **A stale appcast is not automatically a supply-chain finding.** Signed enclosures + a
  non-writable feed + a divergent `latest` artifact is a *lead*. Close it by answering "does
  the app consume this feed" and "does the update path verify the signature" before claiming
  anything — otherwise ship it as `UNPROVEN-IMPACT`.
- **Don't assume a cookie session.** If `/api/auth/login` returns a token in the JSON body
  and `set-cookie` is empty, the session is a Bearer header mirrored into `localStorage`.
  Cookie-jar replays will 401 and look like an authz bug.
- **A 422 on a cross-tenant probe is a request-shape artefact, not an authz bypass.** Send the
  parameter where the bundle actually puts it and with a real enum value before reading
  anything into it. Measured: `DELETE /team/members/{id}` with `delete_mode` in the **body**
  returned `422 selected delete mode is invalid` (looks like authz never ran); with
  `?delete_mode=transfer_and_delete` in the **query string** it returned
  `403 User is not part of your team.` The enum values (`delete`, `transfer_and_delete`) came
  from the bundle's `DeleteUserModal`, not from guessing. Full rule:
  `api-authz-probe-ordering` §1 corollary.
- **`POST /api/media` returning 405 blocks the whole privacy matrix.** Media items are
  client-created only. Record it as `BLOCKED` with the 405 as evidence, never as
  "privacy controls hold" — see the dedicated section above.
- **A bare `POST /api/auth/register` returning `422 cf_turnstile_response required` is not a
  blocked signup.** It is a gate for non-browser clients. Drive the real form in a browser
  and the widget self-solves.
- **A 404 with an empty message on a validation-gated endpoint is a lookup failure, not an
  authz result.** `POST /v1/client/activate` with well-formed 32-char `code`/`serial`/`nonce`
  returns `404 {"message":"","nonce":"<your own value echoed>"}`. The empty message means no
  stack trace and no SQL error; the echoed nonce means the endpoint has no server-side
  anti-replay. Neither is a finding on its own — but do not read the 404 as "authz held"
  either, because no authorization was ever evaluated. Record it as a **negative with
  evidence** (no differential across codes, no rate limit in 20 tries, no state change).
- **An invalid version on `check-for-updates` returns the marketing shell, not JSON.** A 200
  with 174,869 bytes of HTML is a soft-404. Compare byte length before concluding the
  endpoint "accepts anything".

## Support files

- `references/cleanshot-share-link-engagement.md` — full working record for the
  `cleanshot.com` run (2026-10-26, rounds 1 + 2): program facts, host map, the Vite config
  block, the ~30-endpoint web API surface **plus the desktop-client `/v1/client/*` surface on
  a second host**, the access-control state machine, every verified negative with its
  evidence (including the cross-tenant matrix in both directions and the 422 request-shape
  artefact), the two provisioned accounts + auth model, the WAF fingerprint bridge, the
  two-feed update-integrity lead, the DMG/code-signature analysis, and the open queue.
  **Read this before re-probing anything on that target** — it is the verified-control
  ledger for this class.

- `desktop-app-analysis` — when scope includes the desktop client (this class of product
  almost always ships a Mac app): the two-feed pattern, Sparkle Ed25519 verification
  discipline, LZFSE DMG extraction via WSL `7z`, and reading a macOS code signature without
  `codesign`.
- `hunt-idor` — the object-level differential and the two-account harness this class builds on.
- `hunt-ssrf` — URL-import / webpage-capture sinks; 2026 DNS-rebinding pattern.
- `hunt-xxe` / `hunt-xss` — SVG upload is both.
- `saas-plan-entitlement-audit` — the Pro/custom-domain gate.
- `unauth-surface-discovery` — Vite config extraction, catch-all detection, and the S3
  bucket-lock verification recipe.
- `api-authz-probe-ordering` — validation-before-auth ordering and the 422 request-shape
  artefact that fakes an authz bypass.
- `hunt-spa-api` — mapping the API from the bundle (user-owned skill; the technique is
  summarised in `unauth-surface-discovery` §1b).
