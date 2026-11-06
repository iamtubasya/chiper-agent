# Mobile Storage & Session Census — where the real finding hides

> Load at **0C-Mobile**, immediately after `mobile-pentest-guide.md` (which covers tooling, pinning
> bypass, exported components and the signer). This file covers the part that produces paid mobile
> findings: **what the client stores, what renews the session, and what other apps can make it do.**

Activate when the target ships an Android/iOS app in scope, ships a mobile SDK embedded in customer
apps (record the scope caveat — never silently assume the library is covered), or handles sessions,
payments, PII, or realtime comms on device.

---

## 1. Entry heuristic — map in this order (highest bounty density first)

1. **Credential storage** — where do session tokens, refresh/renewal secrets, and API keys live?
2. **Session lifecycle** — issue → store → renew → revoke. **The renewal path is the crown jewel:
   whatever renews the session IS the session.**
3. **IPC / deep-link surface** — what can other apps and web pages make this app do?
4. **WebView bridges** — what native powers are exposed to web content?
5. **Transport** — TLS posture, token placement (headers vs URLs vs logs/telemetry).
6. **Server API as seen by the client** — endpoints and fields the client knows that the web docs
   don't show. Feed these straight into the web2 track.

## 2. Storage census — enumerate EVERY persistence mechanism

Do not stop because the first store looked clean. Findings live in the **second** store: the
forgotten HTTP cache, the legacy database kept for migration, the shared app-group container.

```
SharedPreferences / NSUserDefaults      SQLite / Room / CoreData
plain files in app dir                  Keychain / Android Keystore
HTTP disk cache (OkHttp Cache, NSURLCache)
WebView storage (localStorage, IndexedDB, cookies)
app-group / shared containers           pasteboard / clipboard
cloud + device backup (allowBackup, backup exclusion keys)
```

Questions to answer with evidence, not assumption:

- Are credentials encrypted at rest with **platform keystore keys** (EncryptedSharedPreferences /
  Android Keystore / iOS Keychain)?
- What EXACTLY is stored — token only, or token **+ renewal secret + identifiers**? Identifiers alone
  are low value. **A renewable credential is account takeover with a local-read precondition** —
  grade the conversion, not the storage.
- HTTP cache: is a disk cache enabled on the authenticated client? Cached responses persist
  transcripts/PII **and can persist the Authorization header itself** — persistence depends on the
  server's `Cache-Control`. Claim the code-level enablement; mark the per-response part UNKNOWN.
- Backups: does the data ride along in cloud/device backups? Backup extraction is a standard
  forensic path.
- Logout / session-clear: does it wipe **every** store in the census? A partial wipe is a leftover
  credential.

## 3. Transport & session

- **Token placement:** `Authorization` header (good) vs URL query (leaks to logs, proxies, telemetry,
  referrers — check the **WebSocket handshake URL construction in every socket stack** the app ships,
  including KMM / cross-platform layers) vs POST body.
- **Telemetry / logging:** do log pipelines receive URLs or headers verbatim? Trace the attribute
  from log call to exporter — **redaction that exists on one logging path often does not cover the
  telemetry path**. Test the redaction regex against the token formats actually in play (opaque tokens
  and unusual header ordering slip naive patterns).
- **TLS:** platform default validation intact? Search for permissive challenge handlers, empty
  `X509TrustManager`, hostname-verifier overrides. Absence of pinning alone is a design observation,
  not a finding, unless the program says otherwise.
- **Renewal semantics:** can the stored secret renew forever? Is renewal bound to device/key,
  rate-limited, revocable on password change? Client trusting the server blindly is fine; client
  **storing a renewable secret forever** is not.

## 4. IPC / deep links / push / WebView

- **Exported components:** permission checks, caller validation, what a malicious co-resident app can
  invoke or read. **Content providers are the classic silent data leak.**
- **Deep links / app links:** are parameters trusted (IDs, URLs, tokens)? Verified app links vs custom
  schemes — **schemes are claimable by any app, never a trust boundary.**
- **Push notifications:** PII in the notification body = lock-screen disclosure; do action handlers
  validate the session/object they act on?
- **WebView:** which origins/frames can reach the JS bridge; `file://` access;
  `universalAccessFromFileURLs`; remote debugging flags; whether server-supplied URLs load into a
  **bridged** WebView.

## 5. Shipped artifact vs source — the rule that keeps you honest

Record exact version + hash of the shipped artifact (store APK/AAB/IPA, or the published SDK artifact
from Maven Central / CocoaPods / SPM / npm). **The shipped artifact is the target; the source repo is
a map, not the territory.**

Diff the shipped binary against the public repo on the audited behaviors, and audit the binary where
they diverge. Never claim binary behavior from source alone, or source behavior from the binary alone.

## 6. Platform parity

Whatever you find on one platform, check the other. **Divergence is evidence:** the platform that does
it safely proves the unsafe one is a defect, not a design requirement.

## 7. Evidence gate (same ladder as everywhere else)

- A decompiled code path is REPRODUCED only when the shipped code is executed, or the data flow is
  traced end-to-end without gaps. Label static-only traces honestly — CODE-CONFIRMED is a trace grade;
  say what was not executed.
- REACHABILITY applies to local preconditions too: state plainly WHAT local access the attack needs
  (root / forensic / co-resident app / backup) and what it converts to.
- UNKNOWN server-side behavior (revocation, `Cache-Control`, scope enforcement) stays UNKNOWN in the
  report. The client-side evidence stands on its own legs.
- Runtime proof where the lab allows it: execute the shipped code (unit harness / Robolectric-style /
  instrumentation) with **fabricated values only** — on-disk or on-wire output is the receipt.

## 8. Program notes

- Many programs scope "official apps"; an embedded SDK's eligibility can be genuinely ambiguous. Write
  the scope argument INTO the report honestly (whose code, whose users, who can fix it) and let triage
  decide. Never hide the library nature of the component.
- Method rules still bind: no testing against other users' devices or accounts — your device/emulator,
  your accounts, fabricated data for harnesses.
