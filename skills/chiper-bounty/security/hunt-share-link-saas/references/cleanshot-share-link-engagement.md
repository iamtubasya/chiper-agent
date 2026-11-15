# CleanShot engagement — verified state (2026-10-26)

Working record for the `cleanshot.com` bug-bounty run. Read this before re-probing anything;
every negative below has evidence behind it and re-running it wastes the WAF's patience.

**Scope doc:** `poc-plans/cleanshot/PHASE0.md` · **Progress log:** `poc-plans/cleanshot/PROGRESS.md`
**Pipeline workdir:** `poc-plans/orchestrator-cleanshot_com/`

---

## 1. Program facts (verified live)

| Item | Value |
|---|---|
| Policy | `https://cleanshot.com/disclosure` |
| security.txt | `https://cleanshot.com/.well-known/security.txt` — **Expires 2026-12-09** |
| Contact | `security@cleanshot.com` (email only, no portal) |
| Safe harbour | Stated |
| Reward table (published) | **Critical $4,000** · High $1,000–2,000 · Medium $500–1,000 · Low $100–500 · Info $50–150 |
| Duplicate rule | first reporter only; same root cause = one bounty |

**IN:** `cleanshot.com/*` · `*.cleanshot.cloud/*` · `share.cleanshot.com/*` · `cln.sh/*` ·
`updates.getcleanshot.com/*` · `licenses.cleanshot.com/*` · `legit.maketheweb.io/*` ·
custom domain connected on a Pro account · S3/CloudFront assets referenced by the above ·
**CleanShot X macOS app**.

**OUT:** `docs.cleanshot.com` · `status.cleanshot.com` · other customers' custom domains ·
missing best-practices without a working PoC · unlikely user interaction · password policy ·
**session behaviour by design (incl. tokens surviving 2FA changes)** · **rate limiting** ·
simple DoS · intended behaviour · **user enumeration** · unsafe token storage without a
practical attack · reports based on comments under other users' content.

**PROHIBITED:** social engineering · physical · **automated directory/subdomain brute force** ·
posting comments under other users' content.

⇒ Operator resolution: automated but **GENTLE** (nuclei `-rl 3 -c 1`, ffuf `-rate 3/4 -t 1`,
sqlmap `--delay 2`, katana `-rl 2 -c 1`). Never curl-only.

---

## 2. Host map (measured)

| host | status | server | note |
|---|---|---|---|
| cleanshot.com / www / share / cln.sh / go / gift | 200 | AmazonS | same 174,869 B marketing shell |
| `api.cleanshot.cloud` | 200 | AmazonS | **serves the marketing shell** (sha identical to apex) — wildcard catch-all, not an app host |
| `licenses.cleanshot.com` | 200 | **Vercel** | License Manager (email → request access) |
| `legit.maketheweb.io` | 200 | Vercel | MTW corporate site, in scope |
| `link.cleanshot.com` | 200 | — | **Rebrandly** short-link page (3,763 B) |
| `mailing.cleanshot.com` | 200 | — | 1,136 B |
| `updates.getcleanshot.com` | 403 / 200 | AmazonS | root 403; `/v3/appcast.xml` and `/v3/*.dmg` are 200 |
| `docs.` / `status.` | 200 | cloudfl / Vercel | **OUT of scope** |
| dev / sandbox / staging / staging-* | 403 | CloudFr | blocked |

**The real Cloud app** is a Vue SPA at `cleanshot.com/cloud` (2,567 B shell). Its inline
config block is the whole client contract:

```
window.VITE_API_URL                  = '/api/'
window.VITE_APP_URL                  = '/cloud/'
window.VITE_CLOUDFLARE_TURNSTILE_KEY = '0x4AAAAAABd5EOgqgLEfjQgO'
window.VITE_CUSTOM_DOMAINS_CNAME     = 'cname.cleanshot.cloud.'
window.VITE_CUSTOM_DOMAINS_A         = '75.2.85.205'
window.VITE_PADDLE_VENDOR_ID         = '130946'
window.VITE_PADDLE_SANDBOX           = false
```

Assets on `dgiq1y5djewts.cloudfront.net/123720c2-…/build/assets/` — `main-Bn_6mebf.js`
(340 KB) + `utils-Dvls5zr0.js` (962 KB) + `main-DE658tY1.css`. **Source maps stripped**
(`*.js.map` → NoSuchKey, no `sourceMappingURL`).

---

## 3. API surface (extracted from the bundle)

Base is **`https://cleanshot.com/api`** (relative `VITE_API_URL`). 85 unique call sites,
~30 real endpoints after filtering framework noise:

```
auth:   login · register · code · logout · confirm · resend-confirm · sso-token
        reset/validate · verify-first-password-token · otp/initialize
user:   user (GET/POST) · user/tags · user/clients · client/{id}/unlink · user/notifications (PATCH)
media:  media (GET/DELETE) · media/{id} (GET/POST/DELETE) · media/export
team:   team · team/billing · team/billing/transaction · team/sso · team/scim
        team/members/{id} · team/members/{id}/cancel-email-change · team/invite · team/invite/{id}
misc:   notifications · notifications/read · changelog · changelog/drafts · changelog/read
        maintenance · redeem/{code}/paylink · mediaview/authorize
```

SPA routes: `/cloud/login` `/cloud/register/:hash?` `/cloud/forgot` `/cloud/reset`
`/cloud/confirm` `/cloud/setup-password/` `/cloud/account` `/cloud/advanced` `/cloud/team`
`/cloud/billing` `/cloud/changelog[/:id][/drafts]` `/cloud/setapp/migration`
`/cloud/subscription-migration` `/connect/:hash` `/client/activate` `/team/invite`
`/redeem/:code` `/oauth/authorize`.

**Access-control state machine (the core of the product):**
`privacy_settings` ∈ `everyone` · `password` · `team` · `private`;
`comment_settings` ∈ `everyone` · `team` · `disabled`;
`expire_after` = integer days. Set via `POST media/{id}`.

**Second API surface — the desktop client** (found by grepping the app binary for `^/(api|v1|v2|v3)/`):
```
api.cleanshot.cloud/v1/client/{activate, appcast, check, check-for-updates, migrate, unlink}
```
`/v1/client/appcast` → **200 unauth** (57 KB, 78 items — the LIVE feed, see §4).
`/v1/client/check-for-updates` → **422 `version field is required`** (unauth reachable).
The rest → 405 on GET. This host is separate from the web app's same-origin `/api/`.

---

## 4. Verified NEGATIVES — do not re-test

**Unauth API boundary — clean and uniform:**
- `GET /api/{user,team,team/billing,team/sso,team/scim,media,user/tags,user/clients,
  notifications,team/invite/*,redeem/*/paylink}` → **identical `401 {"message":"Unauthenticated."}`**
- `GET /api/changelog` → 200 unauth, 26 items, fields only `id,title,preview,content,
  category,published_at`. No drafts/internal data. `/changelog/drafts` → 401.
  `/changelog/{id}` → 404 (route doesn't exist).
- `GET /api/maintenance` → 200 `ok`.
- `media/{id}` with numeric / uuid / string ids → 401 (no unauth object read).
- `POST /api/mediaview/authorize` with **9 payload shapes** (`hash`, `media`, `media_hash`,
  `id`, `slug`, `code`, `token`, `url`, and the exact `{approved:false, redirect_uri,
  code_challenge}` shape the SPA's `OauthAuthorizePage` sends) → **401 for every shape**.
  No unauth consent bypass; `redirect_uri` validation only reachable authenticated.
- `POST /api/auth/{code,logout,resend-confirm,sso-token,confirm,user/otp/initialize}` → 401.
- `POST /api/auth/register` → 422 `cf_turnstile_response required`.
- `POST /api/auth/login` → 422 field errors; **identical for existing and non-existing
  emails** (no user-enum oracle — and U/E is OOS anyway).
- `POST /api/auth/reset/validate` → unauth reachable, but `token must be 64 characters`
  (fixed length, no format oracle beyond that).
- `POST /api/auth/forgot` → 422 Turnstile required. `/auth/reset` → 422 token required.
- `POST /api/auth/password` → 404 (route absent).

**Cross-tenant authz — CONFIRMED HOLDING (round 2, both directions):**
- `GET/POST/DELETE /api/media/{other-id}` → **403** (empty message) for every verb
- `DELETE /api/team/members/{other-id}?delete_mode=transfer_and_delete` → **403
  "User is not part of your team."** (enum values from the bundle's `DeleteUserModal`:
  `delete`, `transfer_and_delete`)
- `PUT /api/team/members/{other-id}` with `role:member` and `role:admin` → **403** same message
- `POST /api/team/members/{other-id}/cancel-email-change` → **403** same message
- `POST /api/client/{other-id}/unlink` → 404 · `GET /api/team/invite/{other-id}` → 404
- `POST /api/media/export` → 422 "You have no media to export." (fails closed)
- `GET /api/team` → 200 returning **only the caller's own** member
- `GET /api/user/{id}` and `/api/users/{id}` → 404 (no per-user read route exists)

⚠️ **The artefact that looked like a finding:** `DELETE /api/team/members/{id}` with
`delete_mode` in the **JSON body** returned `422 "selected delete mode is invalid"` — which
reads as "authz never ran". It is a request-shape error: the parameter belongs in the
**query string**. With `?delete_mode=transfer_and_delete` the same request returns the
tenant 403. Do not re-derive this; full rule in `api-authz-probe-ordering` §1 corollary.

**S3 `cleanshot-cloud-fra` (referenced by the in-scope changelog) — locked:**
- `?list-type=2` (also `max-keys`, `prefix`, empty prefix) → **403 AccessDenied**
- `?acl` `?cors` `?policy` `?location` `?versions` `?logging` `?lifecycle` `?website`
  `?uploads` → **403 AccessDenied**
- Known public object → 200 `image/png` (by design). Guessed object / `public/` /
  `private/` / root → 403.
- **Anonymous PUT** of a unique marker → **403** (marker never created, nothing to clean up).

**Routing / host confusion:**
- `*.cleanshot.cloud` wildcard: `api.cleanshot.cloud` returns the **marketing shell**
  (byte-identical sha to apex). `app./cloud./upload./cdn./static./assets.cleanshot.cloud`
  → DNS/conn failure. A nonsense label (`zzz-nonexistent-9f3a.cleanshot.cloud`) also fails,
  so the wildcard is selective, not universal.
- `share.cleanshot.com` and `cln.sh` both serve the marketing shell at `/` and **404
  (1,793 B) on every path** including `/robots.txt`, `/.well-known/security.txt`, `/login`,
  `/api`, `/s/`, `/u/`. The real viewer is an SPA route, not a host path.
- `/share/` → 200 shell; `/share/abc`, `/share/abc123` → 404; `/s/abc`, `/v/abc`,
  `/view/abc` → 404 (29,129 B = a different 404 shell). `/cloud/share/abc` → 200 SPA shell.

**License manager (`licenses.cleanshot.com`, Nuxt on Vercel):**
- `/api`, `/api/license`, `/api/licenses`, `/api/key`, `/api/activate`, `/api/verify`
  → 404 `NOT_FOUND` (Vercel's own 404 envelope, with a `sin1::` request id).
- `/download/cleanshotx`, `/activate`, `/verify` → 200 HTML pages.
- Form is a single `#email` input ("enter the email you used to buy") → request-access flow.

**Media creation is app-only — the privacy matrix is BLOCKED:**
- `POST /api/media` → **405** (`Supported methods: GET, HEAD, DELETE`)
- The SPA's only multipart uploads are `avatar` (→ `POST /user`), `logo` and `favicon`
  (→ `POST /team`), all ≤4 MB
- ⇒ No web-API path creates a media item, so `privacy_settings` / `comment_settings` /
  `expire_after` cannot be exercised. Status is `BLOCKED — no media item creatable via web
  API`, **not** "privacy controls hold".

**Update feeds — TWO of them, and the app points at the stale one:**

| | feed A (`SUFeedURL` in Info.plist) | feed B (desktop-client API) |
|---|---|---|
| URL | `updates.getcleanshot.com/v3/appcast.xml` | **`api.cleanshot.cloud/v1/client/appcast`** |
| auth | none | **none — 200 unauth, also with `?access_token=` empty/invalid** |
| items / enclosures | 30 / 74 | **78 / 78** |
| newest | **3.7.1 — 2021-05-27** | **5.0.2 — 2026-10-26** |
| signatures | 14 ed+dsa, 60 dsa-only | **78/78 `edSignature`** |
| contains 5.x | **no** | yes |

- Feed A `PUT` → **403** (not writable). Feed A root/`/v4/`/`/v5/`/`/beta/`/`/v3/beta/`/
  `/v3/appcast-beta.xml`/`/v3/CleanShot-X-latest.xml` → **403**.
- `/v3/CleanShot-X-latest.dmg` → 200, **50,445,640 B**, `Last-Modified: 2026-10-26`,
  sha256 `REDACTED_********`.
  Feed B's 5.0.2 enclosure declares the **same byte length** — so feed B is the live channel
  and `latest.dmg` is the current build.
- **Sparkle signature verification: UNRESOLVED, not a finding.** 0/78 (feed B) and 0/10
  (feed A) enclosures validate against the app's embedded `SUPublicEDKey`
  (`MLQl7kyrMNEw6jAMo2AKycagE3dmeiNxizC2Q6gre+I=`) across 12 message constructions.
  Verifier self-test passed; only one Ed25519-shaped key exists in the whole bundle (the
  Info.plist one), so it is not key rotation. Either Sparkle 2.9.6 uses a construction not
  reproduced, or the feeds are signed with a different key. Full discipline:
  `desktop-app-analysis` §2c.

**macOS app binary (extracted via WSL `7z`, LZFSE UDIF):**
- Bundle `pl.maketheweb.cleanshotx`, **CFBundleShortVersionString 5.0.2**, min macOS 13.0
- **Valid Apple Developer ID signature** — CMS slot `0x10000` present in both arm64 and
  x86_64 slices; chain `Apple Root CA → Developer ID Certification Authority →
  Developer ID Application: Make The Web O… → Apple Timestamp Certification Authority`
- Bundled **Sparkle 2.9.6**; `SUFeedURL` = feed A; `SUEnableAutomaticChecks = false`
- URL scheme **`cleanshot://`** registered to the bundle id
- Binary string: *"CleanShot has received a command request from an external app. Do you
  want to allow third-party apps to execute commands"* — a local command-execution surface
  that is in scope per the policy's macOS-app entry. **Not yet tested.**

---

## 5. Accounts (self-provisioned 2026-10-26, no operator involvement)

Signup is Turnstile-gated but **SeleniumBase Pure CDP solved it automatically** — the
hidden `input[name="cf-turnstile-response"]` was already populated on page load. No
honeypot, no off-screen decoy, no cross-origin challenge iframe.

| account | email | user id | role | storage |
|---|---|---|---|---|
| **A** | `RESEARCHER_USERNAME+cs1@gmail.com` | **185794** | admin | 1 GB Basic |
| **B** | `RESEARCHER_USERNAME+cs2@gmail.com` | **185796** | admin | 1 GB Basic |

Flow: `/cloud/register` → fill `#name #email #password #password_confirmation` + `#terms`
→ submit → "Verify your email" → mail from `account@cleanshot.cloud` with
`https://cleanshot.com/cloud/confirm?token=<36 chars>` → navigate → active + logged in.

**Auth model:** `POST /api/auth/login` → `{"data":{"token":"<JWT ~1000 chars>"}}`, RS256,
claims `aud:1 / sub:<user id> / scopes:["dashboard"]`, ~1-year expiry. **No session cookie**
(`set-cookie` empty). The SPA mirrors it into `localStorage["state.token"]`.

**WAF behaviour — the block is fingerprint-based, not token-based.** A token that is
byte-identical to the one the browser uses still returns **401** from Python/urllib. Every
authenticated probe must run from inside the browser context
(`fetch(..., {credentials:'include'})` with `Authorization: Bearer <token>` read from
`localStorage`). Note also that the MCP `run_javascript` tool returns `{}` for large objects —
write results to `window.__probe` and read it back in a second call.

---

## 6. Round 3 — desktop-client API + URL-scheme (2026-10-26, measured)

### `/v1/client/activate` — unauth license activation, negative with evidence

Seven required fields (enumerated free from a `{}` POST): `code`, `verification`, `serial`,
`app_version`, `os_version`, `hostname`, `nonce`. `code`/`serial`/`nonce` must each be
**exactly 32 characters**.

| probe | result |
|---|---|
| well-formed 32-char values | **404** `{"message":"","nonce":"<echoed verbatim>"}` |
| different `code` values | byte-identical responses — **no validity oracle** |
| 20 well-formed attempts | all 404, **no 429** — no rate limit |
| identical replay | byte-identical |

Nonce is client-controlled and echoed (no server anti-replay), but with no differential and
no state change there is nothing to replay into. **Negative with evidence.** Open angle: a
*valid* code may respond differently — requires purchase, out of scope.

### `/v1/client/check-for-updates` — version oracle + soft-404

GET only (POST → 405). `4.8.11`/`5.0.1`/`5.0`/`5` → `{"new_version_available":true,
"can_update":true}`; `5.0.2` → `{"new_version_available":false}`. Whitespace trimmed
(`" 5.0.2"`, `"5.0.2\n"` → false) so no parser confusion. Invalid versions (`0.0.1`,
`5.0.3`, `6.0.0`, `99.0.0`, `v5.0.2`, `0x5.0.2`, `-1`, `null`, `true`) → **200 + the
174,869 B marketing shell** = soft-404, not acceptance.

### `cleanshot://` URL scheme — consent gate confirmed present

`CFBundleURLSchemes = ["cleanshot"]`, `CFBundleURLName = pl.maketheweb.cleanshotx`.
Binary carries persisted flags **`allowURLSchemesAPI`** + **`didAskAboutURLSchemesAPI`**
(opt-in, off by default) and the dialog *"CleanShot has received a command request from an
external app… Do you want to allow third-party apps to execute commands and access your
screen?"* plus a settings toggle *"Disable this option to prevent external apps from
controlling CleanShot via URL scheme API"*.

**Control holding.** Residual questions (flag pre-set by another local process, dialog
bypass) require a macOS host → `NOT TESTED — requires macOS`. Command verbs are
Swift-symbol-mangled, not extractable as plain strings; the public API docs page 404s.

### Other `/v1/client/*` (unauth)

| endpoint | method | result |
|---|---|---|
| `check-for-updates` | POST | 405 (GET, HEAD only) |
| `appcast` | GET | 200, 57,304 B XML, 78 items — the live feed |
| `migrate` / `unlink` / `check` | POST | **401 Unauthenticated** — auth enforced |

### Pipeline state

Orchestrator deep in 0C: impact verification complete (72 checks, **0 confirmed**), C2e
php2shell timed out at 30 min (partial artefact, continued), then C3 business-logic vectors.

---

## 7. Open queue (priority order)

1. **`cleanshot://` URL-scheme surface** — what commands can an external app trigger? Is the
   confirm gate bypassable? In scope per the macOS-app entry; needs a logged-in macOS run.
2. **`/v1/client/check-for-updates`** — unauth reachable with a `version` param; probe for
   injection and info disclosure.
3. **Privacy / expiry matrix** — still blocked on a media item. Either find the client's
   upload endpoint, or use the `avatar`/`logo`/`favicon` multipart paths to exercise
   file-handling classes (extension/MIME/content-type confusion, filename traversal, SVG).
4. **Custom-domain claim** — `POST /team {custom_domain}`: is the Pro gate server-side? Can a
   free user claim a domain another tenant connected? Prove the missing ownership check
   without touching a live third-party domain.
5. **`/oauth/authorize` + `mediaview/authorize` `redirect_uri` validation** — now testable
   with a real session (unauth was 401 for all 9 shapes).
6. `team/sso` + `team/scim` write paths, `redeem/{code}/paylink` gift-code entropy and
   cross-account redemption, `client/{id}/unlink` cross-tenant.
7. **Update-feed lead** — answer "which feed does the updater actually read" and "does the
   update path verify the signature". Until then: `UNPROVEN-IMPACT`.

---

## 7. Coverage statement

**Tested:** unauth API boundary (30 endpoints × payload shapes), cross-tenant authz matrix
(13 probes × 2 directions with correct request shapes), S3 bucket (13 bucket ops +
object-level + anonymous write), host/wildcard routing (19 hosts), share-path resolution,
auth-flow error surface, license-manager surface, both update feeds (appcast + artifact +
PUT + signature verification), JS bundle endpoint extraction (1.3 MB), desktop-client API
surface, DMG extraction + code-signature parse + Sparkle key analysis, two-account
provisioning.

**NOT yet tested (needs session or platform):** privacy/expiry matrix (blocked on media
item), `cleanshot://` scheme behaviour, `/v1/client/check-for-updates` payloads,
authenticated `redirect_uri` validation, `team/sso` + `team/scim` writes, Paddle webhook
surface.
