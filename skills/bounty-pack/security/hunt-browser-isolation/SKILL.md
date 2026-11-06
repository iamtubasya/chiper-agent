---
name: hunt-browser-isolation
description: "Audit browser-isolation / disposable-browser / remote-browser products (SquareX, Kasm Workspaces, Cloudflare Browser Isolation, Silo, enterprise browsers) for multitenancy, session isolation, container breakout, and k8s issues. Use when the target's product is an isolated/disposable/remote browser or file viewer, and the bounty scope names 'container breakout', 'breaking multitenancy', 'extending container lifetime', or 'attacks on Kubernetes'."
metadata:
  hermes:
    tags: [security, bug-bounty, webbrowser, isolation, noVNC, kasm, multitenancy, container, k8s]
    version: 1.0.0
    author: RESEARCHER_NAME
---

# Hunt Browser Isolation / Disposable Browser

The product of a browser-isolation vendor is a **remote browser running in a cloud container**
that the user drives through their own browser. The attack surface is NOT the marketing site —
it is the **streaming/display client plus the per-session hostname** that reaches the container.

## When this triggers
- Scope/product mentions "disposable browser", "isolated browser", "browser isolation",
  "remote browser", "isolated file viewer", "remote browser isolation (RBI)".
- Bounty tiers explicitly name "breaking multitenancy", "container breakout to host",
  "getting internet access inside the container", "extending the lifetime of the container",
  "attacks on Kubernetes". These are the literal Critical categories — they tell you exactly
  where the money is.

## Recon → the display client is the map
1. The web app almost always serves a **streaming client** under a path like `/display/`,
   `/viewer/`, `/browser/`. It is a **noVNC / RFB client** (Kasm Workspaces and forks ship
   a noVNC HTML page) and may also pull `jsmpeg.js` (MPEG-video streaming) for a
   screen/audio stream.
2. `GET /display/` → an HTML page titled after the product, with a noVNC `<div id="noVNC_container">`
   and a script bundle (`main.<hash>.js`). The HTML comments leak the fork origin
   (`kasm-icon.svg`, `noVNC` license header). `jsmpeg.js` = screen-video stream.
3. **Download and statically analyze that JS bundle.** It is the client→backend contract map:
   - API endpoints: `/api/authorize`, `/api/launch`, `/api/extend` (session lifetime!),
     `/api/terminate`, `/api/status`, `/api/verify_url`, `/api/org_details/get`, `/api/log`,
     `/api/error`, plus public lead-gen endpoints.
   - Session-id origin: `new URLSearchParams(location.search)` — the session id is often taken
     **directly from a `?session=` / `?boxSession=` URL parameter**.
   - Connection targets built by string concat from the session id:
     `wss://${session}/websockify` (VNC), `wss://${session}-sc/ws` (control),
     `wss://${session}-mic` / `${session}-audio`, `https://${session}-sc/list` (file download),
     `https://${session}-sc/` (status). noVNC config: `path:"websockify"`, `shared:true`.
   - Internal dev hosts: grep for a `[...].includes(hostname)` allowlist — it names staging/dev
     domains (`dev.<internal>.com`) that are usually OUT of scope but reveal topology.

## The multitenancy question (the critical test)
> **Is the per-session VNC/control/file connection authenticated by anything other than the
> session hostname itself?**

- In the client code, look for a per-session **token/password** passed to the RFB layer
  (`credentials`, `sendCredentials`, a `credentialsrequired` handler). In a weak design there
  is NONE — the session hostname is the only secret.
- Session hostnames are usually **predictable** (`url<NUMBER>.online.<apex>`, incrementing `N`)
  AND **leak via Certificate Transparency** (crt.sh / certspotter) because each session gets a
  real DNS record that a cert once covered.
- If hostnames are enumerable + connections are unauthenticated, an attacker who finds an active
  session hostname can view/control another user's container = multitenancy = Critical.

## Proving it (the honest gate)
1. Enumerate session hostnames: CT logs (crt.sh `%.<apex>`, certspotter) + brute a range of the
   `url<N>` pattern. Sweep `https://<host>/` and record the status distribution.
2. **A 404 = disposed session; NXDOMAIN = record was removed.** A non-404 / 200 on a `.` GET
   (or a live VNC handshake via `wss://<host>/websockify`) is the signal of an ACTIVE session.
3. Only claim multitenancy as a finding if you can demonstrate cross-session access on a LIVE
   session. Otherwise report the architecture honestly as a **lead**, with the enumeration vector
   and the missing-auth observation — do NOT fabricate a Critical.

## Container breakout / k8s angle (scope often allows it)
- Same infra, inside the (legitimate) session: probe cloud metadata (`169.254.169.254`,
  `metadata.google.internal`), reachable k8s API, host filesystem. Scope usually says whether
  "accessing local files inside the container" is excluded (read it — SquareX excludes it).
- `/api/extend` = session-lifetime extension is itself a scoped bug class: test whether a caller
  can extend someone else's session (IDOR) or extend past quota.

## Dead-product detection (avoid wasting a session / over-claiming)
Browser-isolation vendors are a hot M&A space; the consumer product is often deprecated while the
bounty page stays up:
- **Redacted Firebase API key in the JS bundle** (`apiKey:"AIzaSy...LBQk"`) = the client auth is
  broken/ship-halted — you cannot self-provision an account or launch a session.
- Extension **delisted from Chrome Web Store** (`clients2.google.com/.../crx` → HTTP 204 empty).
- Session DNS now NXDOMAIN / all sweep hosts 404 → no active disposable infra.
- stale `security.txt` `Expires:` date far in the past, policy "last updated" years old.
If these all fire, the honest deliverable is the attack-surface map + leads, not a confirmed
Critical. Say so plainly instead of keeping the run burning hours and then inflating.

## Pitfalls
- `?session=` URL param → `ve.id = session` with NO crypto token is the multitenancy tell, but it
  is CLIENT-side; by itself it proves nothing server-side until you hit a live session.
- CT APIs flake (crt.sh 502, certspotter empty, Wayback "temporarily offline") — don't read a
  failed CT query as "no sessions". Retry, and fall back to a DNS brute of the `url<N>` range.
- Session hostname suffix `-sc`/`-mic`/`-audio` on a full hostname is often NXDOMAIN — the code's
  `${session}-sc` concat may imply the session id is a short token, not the full FQDN. Confirm the
  actual FQDN construction before concluding anything about enumeration.
- SameFlask/werkzeug "400 Bad Request" HTML page (not JSON) on a malformed body = Flask backend;
  JSON 401 `{"reason":"No Auth"}` + `set-cookie: SESSIONID=` = server-side session auth.

## Reference
- `references/sqrx-squarex-case.md` — worked case: SquareX disposable browser (noVNC client,
  session-hostname multitenancy lead, dead-product indicators, reCAPTCHA-not-validated lead-gen).