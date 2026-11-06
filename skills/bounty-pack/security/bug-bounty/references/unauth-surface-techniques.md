# Unauth-surface techniques — cross-session playbook

Distilled from 2026-10 engagements (Byte Federal, Fastmail). All verified live. Use at Phase 0B/0C.

## 1. Subdomain wildcard-artifact classification (do this FIRST after subfinder)
Subfinder routinely returns hundreds of wildcard artifacts (Byte Federal 90 subs, Fastmail 533 subs
where 529 were wildcard). Resolve ALL subs, classify by IP:
- Cloudflare ranges (104.16-28.*, 172.64-67.*, 188.114.*, 173.245.*) → proxied
- 100.x → Tailscale/internal leak (reportable as info if in public DNS)
- BARE IPs → group them: if N subs share 1-2 IPs = wildcard catch-all (fake surface);
  the REAL surface = the few subs with UNIQUE IPs. Fastmail: 529 fake → real clusters were
  api/app/DAV/mail/non-prod each on distinct IPs. Saves hours of probing ghost hosts.

## 2. Origin-access + geo-gate provenance test
When DNS shows bare origin IPs (no CF), test direct-origin access with Host header routing:
`requests.get(f"https://{ip}/", headers={"Host": host}, verify=False)`.
If the origin serves the app → CF is skippable at network level. THEN test whether any
IP-based control (geo-gate, rate limit) is enforced at CF or origin:
- Replay the gated request straight to the origin. If the gate persists → server-side
  (Fastmail: createAccount still returned countryCode:ID at origin = geo-IP at app layer, no bypass).
- Gate disappears at origin → CF-header-based → header-spoof candidate (X-Forwarded-For /
  CF-Connecting-IP / True-Client-IP battery, one per request, watch for differential).
Note: rate limits often follow to origin (per-IP at app layer), so probe slowly.

## 3. CORS reflection triage
Reflected ACAO (evil origin echoed) is NOT a finding by itself. Exploitable ONLY if BOTH:
(a) Access-Control-Allow-Credentials: true, AND (b) the API authenticates via COOKIES.
Bearer-token APIs (JMAP, most DRF/FastAPI) → non-exploitable, document as negative.
Check the full header set (grep access-control + vary) before scoring.

## 4. JMAP / DRF / FastAPI-style API discovery
- Look for `x-trustedclient`-style custom headers the SPA sets (capture via Playwright request
  headers; the "trusted source" 401 usually names the mechanism).
- JMAP wire format: POST JSON {"using":[...namespaces],"methodCalls":[[name,args,callId],...]} —
  methodCalls entries are 3-element arrays; missing callId → "method N array not 3 elements".
- Schema discovery by error differential: the phone-verify style endpoint leaks exact field names
  ("[body.phoneNumber] Invalid input: expected string"); generic "invalid request" = opaque
  validation (stop guessing bodies).
- unknownMethod errors enumerate the real method surface cheaply.

## 5. SPA bootstrap module-map white-box
For Cappuccino/React-style SPAs with versioned static paths: fetch the bootstrap JS and extract
the module map (logical path → file + dependency list). Modules then load from predictable paths
(Fastmail: /static/jmapui/{ver}/app/module/desktop/{Module}.mod.js). Grep module names against the
program's hall-of-fame bug classes (Fastmail: OAuthToken/sudo/defangHTML modules = paid classes).
Also grep worker bundles (offline/SSE workers) — they often embed the full client data model.

## 6. Livewire (Laravel) action driving
- /livewire/update requires the PLAIN csrf-token (meta tag) or XSRF-TOKEN cookie value, PLUS the
  exact LIVE snapshot (stale snapshot → 404). Scripted replay with an initial snapshot fails;
  drive via browser (Playwright fill + real keystrokes — fill() alone may not sync wire:model).
- Magic-link components reveal rate limits in-band ("Too many requests... 57 minutes").

## 7. SvelteKit __data.json
SvelteKit apps expose server data at /route/__data.json (and ?query variants) WITHOUT the SPA
shell — use for cheap recon of listings/params. Form actions are CSRF-protected
("Cross-site POST form submissions are forbidden" on cross-origin POST) — same-origin cookie jar
required, and CF challenge on the action route is a hard wall.

## 8. Cloudflare Turnstile wall (target defense, not tool failure)
Headless AND headed Chromium both fail CF Turnstile consistently (widget renders, token never
mints). Camoufox REST server may wedge on tab creation. Treat Turnstile-gated flows as blocked
coverage — document the gate, pivot to unauth surface or request a solving path; do NOT log it as
"browser tools broken".

## 9. Target-switch cleanup pattern
On "hapus/ganti target": move the engagement dir to
`<parent>/_QUARANTINE/<target>_<YYYYMMDD_HHMMSS>/` + write MANIFEST.json (reason, summary, recovery
steps). Windows gotcha: a killed scanner's zombie exe (tasklist by name) keeps output files busy —
`taskkill //F //PID <pid>` before moving; an empty leftover dir may stay "Device or resource busy"
until handles release (cosmetic, data is safe).

## 10. Signup/anti-abuse gate taxonomy (what "needs an account" usually means)
Seen in the wild: geo-IP → mandatory SMS (Fastmail, server-side), Turnstile on OTP request
(Byte Federal), captcha before SMS send, talon/anti-fraud tokens, per-email rate limits with
in-band cooldown messages, mobile-app-only registration (Byte wallet signup modal says
"create your account in the app"). All are legit defenses — the finding would be a BYPASS
(trial-abuse class, ~$100), not the gate's existence.
