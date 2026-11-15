# Target Defense Patterns & Wall-Triage (2026-10, Byte Federal engagement)

Hardened consumer-crypto target: every money path walled, every wall documented honestly.
Distilled from a full 0A–0E run. Read BEFORE declaring any host "clean".

## Program-status gate (Phase 0A — do this FIRST)
- **Paused programs pay nothing.** Zora's policy page banner read: "Program status: paused as of
  August 10, 2026... reports submitted during this period are not eligible for rewards." A paused
  program = switch target immediately, do not invest a full engagement. The pool's `status` field
  (active/retired/expired) comes from a source sheet and can be stale — the live policy banner is
  authoritative. Also note the escape hatch Zora published: funds-at-immediate-risk reports still
  go to the security contact even while paused.

## Cloudflare Bot Management vs scanner UAs
- **Symptom:** every ffuf/nuclei path returns the *identical* status + byte size (observed: uniform
  403, 5863 bytes, 668 words on all 48 probed paths) = CF edge block, NOT an app response. Never
  read a uniform-403 sweep as "endpoint map".
- **Fix:** rerun with a full browser UA header. Confirmation you reached the app: Laravel JSON
  signature `{"message":"The route X could not be found."}` (404 via API) vs CF's HTML 403.
- **nuclei** with default UA stalls indefinitely on CF-challenged hosts (observed: 29 min, 1 result,
  never progressed to the next `-u` target). Run per-host with `-rl 2-3 -c 2-3`, kill any host that
  hangs >10 min, and log it as a coverage limit — not a negative.

## Turnstile-walled flows = coverage limit, never "0 findings"
- KYC/register/OTP flows behind CF Turnstile are usually **server-validated**: dummy token →
  403 `bot verification required`; missing → 400; malformed-but-dotted token → different 400
  (differential reveals the validation ladder). Don't claim bypass without a real token.
- Headless AND headed Chromium both failed token issuance (token input stayed empty; the widget
  renders at submit as a floating bottom-right iframe, then detatches on click). If the Hermes
  `browser_navigate` times out on the camoufox port (9377), drive camoufox directly: `GET /openapi.json`
  documents the REST map (`POST /tabs {userId, sessionKey, url}`; `/tabs/{id}/snapshot|click|type|evaluate`;
  `/stop` may 403, `/start` works). A wedged camoufox (tab-create hangs) = restart via /start.
- Honest ledger wording: "Turnstile wall on <named endpoints>" + "one test phone number breaks it".

## SvelteKit data endpoints (fast app mapping)
- `<route>/__data.json?<params>` returns the server `load()` payload without rendering: report lists,
  turnstile site key, totals, accepted query params (`uses.search_params`). 200 = mapped; CF-challenge
  403 = gated. Check report-detail pages for reporter PII before assuming public-by-design.

## Laravel / Livewire signatures
- JSON `{"message":"The route X could not be found."}` = app reached, route absent.
- `{"message":"Server Error"}` 500 on a legacy route = endpoint exists but broken. **Param-independent
  500s (same body for every input) are not injectable and leak nothing** — prove with 2–3 param
  variants before writing anything.
- Livewire version from `/livewire/livewire.min.js` (`version:"3.x.y"` grep). `wire:snapshot` in HTML
  leaks the component memo (name/id/checksum) plus any public component data (observed: QR-login
  session ids + `bytewallet://` deep links).
- Registration differential: POST valid data twice with the same email — if both 500 identically,
  the crash precedes the duplicate-email check (functionality bug, not security).

## Mobile recon (APK)
- **apkpure "latest" downloads are often split-APK BUNDLES**: unzip the download, then unzip the
  nested `<package>.apk` for `classes*.dex`. The outer zip only has `config.*.apk` splits.
- **RN apps**: `assets/index.android.bundle` is Hermes bytecode — raw ASCII-run extraction yields
  alphabetically-sorted **concatenated** strings (noise). Mine with targeted regex
  (`/u/api/...`, `/web/api/...`, `bytewallet://(scheme|alt)`, host fragments) instead of reading runs.
  Deep-link scheme alternation revealed backend hosts the DNS enum missed.
- dex string mining (plain ASCII runs on `classes*.dex`) still works for URLs.

## DNS leak triage
- Resolve every enumerated subdomain; flag `100.64.0.0/10` (Tailscale/CGNAT) and bare non-CF public
  IPs. Internal hostnames (secmon, netbox, im, status, livepulse) in public DNS = info-disclosure
  candidate; impact is recon-only while the IPs are CGNAT — say that in the report.

## Historical endpoints (gau) — highest ROI recon step
- gau/waybackurls surfaced: legacy API routes (`/web/api/checkfast?sid=<32hex>_<unix_ts>`),
  notary/verification pages (`/web/certified/<sha256>` serving name+document-id), an exposed backup
  path (`/backup_2.sql.tar.gz` → 403 live). Always resolve historical hits live before probing; a
  403/521 on a historical path is a finding-shaped lead, not a dead end.

## Vendor source/docs as free white-box
- Check `github.com/<vendor>` BEFORE live testing: the auth SDK itself was public
  (`byteauth-laravel`, `byteauth-nextjs`) — webhook route names, the verify-session dependency, the
  missing `session()->regenerate()` after `Auth::login()`, and the `if (isset($data['email']))`
  email-binding gap all came free from source. Live probing then only confirms deployment.
- API hosts: try `/openapi.json` + `/docs` first (observed: full "Global Id" spec wide open). An
  exposed spec is not a finding by itself — **test enforcement** (garbage key → 401 = enforced and
  validated; data returned with a dummy key = broken access control).

## 500-endpoint triage rule
- Before claiming error-handling info-disclosure: fetch the full body. Bare `Internal Server Error`
  (no stack trace, debug off) on a param-independent endpoint = note as INFO, not a finding.
