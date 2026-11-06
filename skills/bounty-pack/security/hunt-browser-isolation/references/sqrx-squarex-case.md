# SquareX (sqrx.com) — worked case (2026-11)

## Target
SquareX = Browser Detection & Response vendor. Product: Chrome/Edge extension + "Disposable
Browser" (isolated browser in GCP/GKE container, driven via noVNC), Disposable File Viewer,
Disposable Email. Acquired by Zscaler (closed 2026-02-05); consumer extension DELISTED from
Chrome Web Store.

## Scope (source https://sqrx.com/bugbounty)
In-scope: sqrx.com + sqrxlabs.com (domains+subdomains), Disposable Browser/File Viewer/Email
(extension + web app), container breakout, internet-in-container, multitenancy, k8s attacks,
container lifetime. Excluded: CORS, clickjacking, missing headers, cookie flags, rate-limiting,
email bomb, DoS, TLS, DMARC/SPF, **Firebase config leaks + auth**, server errors (unless
critical), file-restriction bypass, GA/track. Rewards Low $100 / Med $500 / High $1000 / Crit $2000.
Submit security@sqrx.com, subject "[Severity] Vulnerability - sqrx.com".

## Estate map
- sqrx.com = marketing (GCS + Flask on Google Cloud, reCAPTCHA). public.sqrx.com = web app +
  `/display/` noVNC client + Flask `/api/*`. beta.sqrx.com = old GCS React app.
- okta.sqrx.com = custom Okta domain (SaaS). labs.sqrx.com = Cloudflare-challenged blog.
- Dead (NXDOMAIN): enterprise / getstarted / alfasquad / gcp.sqrxlabs.com.
- Session hostnames (from CT via subfinder): `url3129.online.sqrx.com`, `url4045.send.sqrx.com`,
  `url10.auth.sqrx.com`, `o1.ptr2942.online.sqrx.com` → pattern `url<N>.<type>.sqrx.com`.
  All resolve to GCLB 130.211.24.211 then 404 (disposed).

## Disposable-browser client map (from display_main.js)
- `/display/` = noVNC page, static bundle `main.PU2R5ELG.js`.
- Session id from URL query (`session`, `boxSession`, `country`, `type` where
  type ∈ browser|file_viewer|ext_analysis).
- `ve.id = t.session` (URL) or `i.session.session` (authorize response). NO crypto token.
- Connection build: `wss://${id}/websockify` (VNC), `wss://${id}-sc/ws` (control),
  `wss://${id}-meg`/`-audio`, `https://${id}-sc/list`, `https://${id}-sc/` (status).
  noVNC: `path:"websockify"`, `shared:true`, no `credentials` set anywhere in app code.
- Regions: SG, US West/East, IN, DE, GB, CA, AU, JP, FR, BE, MX, BR, TW.
- Internal-dev leak: `["dev.sqrxdevops.com","public.sqrx.com"].includes(hostname)`.

## Flask API surface (public.sqrx.com/api/*)
Public: get_download_link, team_plan, pr_requests (lead-gen), verify_url (400 always),
logout (200). Auth (SESSIONID): authorize, status, launch, log, extend, terminate, subscribe.

## Findings
1. [LEAD, unproven] Multitenancy: session hostname = sole identifier, predictable + CT-leaked,
   no per-session token in client. Could not demo live (sweep url2900–4300 = 1399 NXDOMAIN +
   1 stale 404 → no active infra).
2. [LOW, proven 3x] reCAPTCHA not validated server-side: lead-gen POSTs accept
   `gResponseToken:""`/invalid → `{"status":"success"}`. Overlaps "rate limiting"/"email bomb".
3. [INFO] dev.sqrxdevops.com internal domain in prod JS (OOS apex).
4. [INFO] source map public: `/static/js/main.bcbfa333.js.map` (200) — REACT_APP_* build vars
   only, no secrets in sourcesContent.

## Dead-product indicators observed (all four fired)
- Firebase `apiKey:"AIzaSy...LBQk"` (redacted) in bundle → client auth broken.
- Extension 204 empty from `clients2.google.com/.../crx?id=kapjaoifikajdcdehfdlmojlepfpkpoe`.
- Session DNS removed / all swept hosts 404.
- security.txt `Expires: 2025-09-09` (stale), policy "last updated 2024-01-08".

## Verify-recaPTCHA snippet
```
curl -s -X POST https://public.sqrx.com/api/get_download_link \
  -H "Content-Type: application/json" \
  -d '{"email":"v@example.com","report":"defcon-deck","gResponseToken":"","name":"v"}'  # -> {"status":"success"}
```

## Why nothing higher was reachable
Auth to launch a session = Firebase email-link; key redacted ⇒ cannot self-provision. Extension
delisted. No active disposable sessions to demonstrate cross-session access. Honest result:
surface map + leads, not a forged Critical.