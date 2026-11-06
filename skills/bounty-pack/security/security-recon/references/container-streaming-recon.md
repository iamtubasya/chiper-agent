# Container-streaming / disposable-browser / VDI recon (noVNC · Kasm · jsmpeg)

Class of target: "cloud browser", "browser isolation", "disposable browser/file viewer/email",
"VDI replacement". Vendor spins up a container per user session and streams its screen over
VNC/WebSocket. Programs in this class pay big for **multitenancy break** (view/control another
user's session) and **container breakout**, because the streaming surface is where isolation is
enforced. Worked example: SquareX / sqrx.com (2026-11-01).

## 1. Detect it from the public surface
- A page that ships **noVNC** (`paths like /display/`, and JS containing `path:"websockify"`,
  `RFB(`, `_rfbCredentials`, `shared:!0`) = remote-browser/VNC streaming client.
- **`jsmpeg.js`** referenced = MPEG video streaming (screen cast) — same family.
- A noVNC HTML head comment mentioning **Kasm** (`kasm-icon.svg`) = built on Kasm Workspaces
  (container streaming platform); its k8s/agent architecture is well-documented, which shortcuts
  your own map.
- The noVNC connect parameters in the stock template (`?host=HOST&port=PORT&encrypt=1` or
  fragment) tell you the transport shape before you even read the custom JS.

## 2. The client JS bundle IS the architecture map
Fetch the streaming client bundle (e.g. `/display/main.<hash>.js`) and extract:
- **session id source** — usually a URL param (`?session=`, `?boxSession=`) or the authorize
  response, e.g. `ve.id = t.get("session")` then `wss://${t.id}/websockify`.
- **all endpoint strings** — `/api/authorize`, `/api/terminate`, `/api/extend`, `/api/launch`,
  `/api/verify_url`, `/api/log`, `/api/org_details/get`, etc. (grep `/api/`).
- **the streaming transport** — `wss://<session>/websockify` (VNC), `wss://<session>-sc/ws`
  (control channel), `wss://<session>-mic` / `-audio`, `https://<session>-sc/list` (file list),
  `https://<session>-sc/` (status probe).
- **region/type enums** — `type` param (`browser` / `file_viewer` / `ext_analysis`) and country
  whitelist (`SG,US,US1,US2,IN,DE,GB,CA,AU,JP,FR,BE,MX,BR,TW`) reveal the fleet layout.
- **internal hostname leaks** — hardcoded `if(["dev.sqrxdevops.com","public.sqrx.com"].includes(...))`
  = a dev/staging apex you didn't enumerate (likely out of scope, different apex — note, don't test).

## 3. The multitenancy primitive to look for
Classic weakness: **the session hostname is the only credential**. If the client connects with
`wss://<session-id>/websockify` and no per-session token/password/cookie is visible in the JS AND
the RFB config has no `credentials:` set and no `credentialsrequired` handler, then the transport
auth reduces to "guess/enumerate the hostname". Escalate when hostnames are:
- **predictable** (`url<NUMBER>.online.<t>` — incrementing integer), and
- **leaked via Certificate Transparency** (crt.sh / certspotter on `%.online.<target>`).
That is the entire input to a potential "view another user's session" Critical. To confirm, you
need one LIVE session hostname (see step 4) and a WebSocket connect that grabs the framebuffer.

## 4. Is the product actually live? (cheap pre-investment check)
Do this BEFORE writing the multitenancy report — a decommissioned product has no live sessions to
prove cross-session access:
- `dig +short url3129.online.<t>` resolves but HTTPS `/` returns 404 = session disposed; DNS
  record left dangling.
- Wildcard check: `dig +short <random-label>.online.<t>` = NXDOMAIN (no wildcard) = each session
  had a real record, now gone.
- Range-scan `url<N>.online.<t>` for N over a few thousand with 20 threads; count statuses.
  Result here: 1399 NXDOMAIN + 1 stale 404 ⇒ **zero active sessions ⇒ surface decommissioned**.
  (Seen on sqrx.com after Zscaler acquisition — consumer auth broke too: redacted Firebase key.)

## 5. Auth gate — the other way this class "dies"
Consumer streaming products usually gate `launch`/`extend`/`terminate` behind a SESSIONID cookie
obtained from `/api/authorize` (POST `{token}` = Firebase ID token). If the SPA's Firebase key is
**redacted in the bundle** (`apiKey:"AIzaSy...LBQk"`), client auth is dead and you cannot
self-provision a session → the engagement is unauth-surface-only. Distinguish real SSRF candidates
(e.g. `/api/verify_url` POST `{url}`) from auth-gated ones: auth-gated return `{"reason":"No Auth"}`
with `SESSIONID=;` cleared in `Set-Cookie`; public ones return JSON or a werkzeug 400.