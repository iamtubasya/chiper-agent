---
name: hunt-firebase
description: "Hunt Firebase-backed apps — extract Firebase config from the JS bundle, reverse the auth model (email/password, OAuth, email-OTP, custom token), exchange custom→ID tokens, and test Firestore/Storage security rules + App Check. Use when a target uses Firebase Auth, Firestore, or Firebase Storage (kindroid-ai.firebaseapp.com, securetoken.google.com, firestore.googleapis.com, firebasestorage.googleapis.com)."
metadata:
  hermes:
    tags: [bug-bounty, security, firebase, firestore, auth, cloud, idor, web2]
---

# Hunt Firebase-backed apps

Firebase Auth + Firestore + Storage power a huge slice of SaaS/consumer targets. The
whole data layer often lives on Firebase, and the #1 payout is a Firestore rules
miss (direct cross-user read) or an App Check bypass. This skill is the playbook for
mapping that surface and testing it properly.

## When to use

Signals that a target is Firebase-backed:
- `firebase.googleapis.com`, `securetoken.google.com`, `<project>.firebaseapp.com` in JS/network
- `x-powered-by: Express` + a `server: Google Frontend`/`x-cloud-trace-context` API host
- Browser requests to `__/auth/iframe`, `__/firebase/init.json`
- A literal `apiKey:"AIzaSy…"` in a bundle (Firebase web keys are PUBLIC — not a secret)
- `firebasestorage.googleapis.com/v0/b/<project>.appspot.com` or `<project>-<hash>.r2.cloudflarestorage.com`

## 1. Extract the Firebase config from the JS

The config object is usually in the Next.js `_app` bundle (or an `app-vendor` chunk):

```
grep -ohaE 'AIzaSy[A-Za-z0-9_-]{20,}' _app-*.js | head -1
```

Fields you want: `apiKey`, `authDomain`, `projectId`, `storageBucket`, `appId`,
`messagingSenderId`. Also available at `https://<authDomain>/__/firebase/init.json`,
but that endpoint often REDACTS `apiKey` to `"***"`.

**GOTCHA (cost real time this session):** the terminal's output-redaction layer turns
the real key into `AIzaSy...-F1A` in *display*, even though the file holds the full key
(`wc -c` shows the true length). Do NOT copy the key out of tool output and paste it into
a script — the paste will carry the redacted form and your API calls will fail with
`API key not valid`. Fix: extract the key programmatically (regex from the on-disk JS
file) and write it straight to a file, then have your script read that file. Scripts that
grep the bundle themselves and never print the key work fine.

## 2. Reverse the auth model

Probe Firebase Identity Toolkit REST to learn what's enabled (no captcha needed):

```
POST https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=<webKey>  {email,password,returnSecureToken}
  -> 400 OPERATION_NOT_ALLOWED   = email/password signup disabled
POST .../accounts:sendOobCode?key=<webKey>  {requestType:"EMAIL_SIGNIN", email}
  -> 400 OPERATION_NOT_ALLOWED   = email-link/magic-link disabled
POST .../accounts:sendOobCode?key=<webKey>  {requestType:"PASSWORD_RESET", email}
  -> 200                         = (always 200; anti-enumeration, tells you nothing)
```

Common live pattern (Kindroid, many consumer apps): **email OTP sign-in**, not
email/password. Flow is app-backend-mediated, e.g.:

```
POST https://api.<target>/v1/send-otp-code   {"email":"x"}  -> 200 "OTP code sent"
POST https://api.<target>/v1/verify-otp-code {"email":"x","code":"12345678"} -> {"token":"eyJ..."}
```

Rate-limit reality: `send-otp-code` will 429 (`Please wait before requesting another
code`) after a few hits, per-email. Great for self-provisioning a test account; also
confirms the spam-bombing vector is mitigated.

## 3. THE token chain — custom token vs ID token (non-obvious; cost real debug time)

`verify-otp-code` (or equivalent) returns a **Firebase CUSTOM token**, NOT an ID token.
Decode the JWT and check `iss`:

- custom token => `iss = firebase-adminsdk-<id>@<project>.iam.gserviceaccount.com`,
  `sub = <that service account>`, `aud = identitytoolkit.googleapis.com`, plus a `uid` claim = the user id.
- ID token => `iss = https://securetoken.google.com/<project>`, `sub = <user uid>`.

The backend API (`api.<target>`) will 401 `Unauthorized` on a Bearer custom token. You
must exchange it first:

```
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=<webKey>
     {"token":"<custom>","returnSecureToken":true}
  -> {"idToken":"...", "refreshToken":"...", "expiresIn":"3600"}
```

Then use `Authorization: Bearer <idToken>` against the app API. This single exchange is
the difference between "everything 401s, target looks dead" and full authenticated access.

## 4. Test Firestore rules (the CRITICAL path)

**Firestore REST v1 does NOT take Firebase ID tokens.** `GET
firestore.googleapis.com/v1/projects/<p>/databases/(default)/documents/...` with a Bearer
ID token returns `401 "Expected OAuth 2 access token …"`. That endpoint only accepts
Google OAuth2 (service-account) tokens, which would BYPASS rules — useless for testing.

To test rules *as a real client*, use the Node.js `firebase` client SDK (this replicates
the web app exactly, including App Check):

```js
const { initializeApp } = require("firebase/app");
const { getAuth, signInWithCustomToken } = require("firebase/auth");
const { getFirestore, doc, getDoc, collection, getDocs } = require("firebase/firestore");
const app = initializeApp({ apiKey, authDomain, projectId, storageBucket, appId });
const auth = getAuth(app); const db = getFirestore(app);
await signInWithCustomToken(auth, customToken);
await getDoc(doc(db, "Users/<someUid>"));      // own doc = control; cross-user = the test
await getDocs(collection(db, "Users"));        // list collection
```

Install: `npm i firebase@10` in a scratch dir, run with `node`. `signInWithCustomToken`
can be slow (~1 min first hit) — run with a generous timeout / background.

**Diagnostic — App Check is ON (target is locked, NOT a rules bug):** if even `getDoc` of
the user's OWN document throws `permission-denied Missing or insufficient permissions`,
that means Firestore requires an App Check token, not just auth. You cannot forge App
Check from a script; pivot away from direct DB access — the enforcement point is now the
app's own API (which is scoped by uid server-side) and you'll find no Firestore bypass.

## 5. Test Firebase Storage rules

- List: `GET firebasestorage.googleapis.com/v0/b/<project>.appspot.com/o` → 403 = listing denied.
- Custom domain `storage.<target>` / `<project>.<hash>.r2.cloudflarestorage.com` may
  Cloudflare-1010-block curl (browser/IP check) — retry with a real browser UA if needed.
- Presign IDOR test: the app's upload endpoint (`POST /v1/storage-presign {path,method,content_type,content_length}`)
  must reject a cross-user path or traversal. Expect correct behavior to be `400 "Path not allowed"`
  for `users/<otherUid>/...` and `../`. Only a signed URL returned for the OTHER user's path is a finding.

## 5b. Firebase Realtime Database (RTDB) — separate from Firestore

`firebase_database_url` in config (e.g. `<project>.firebaseio.com`) is a Realtime
Database, NOT Firestore. Its security rules are a completely separate check. Probe directly:

- `GET https://<project>.firebaseio.com/.json` = whole-tree read.
  - 200 + JSON data = **PUBLIC READ (critical)** — read everything, then test writes.
  - 401 / `"Permission denied"` = rules locked down (closed).
  - 423 `"The Firebase database '<project>' has been deactivated."` = DB decommissioned (clean — NOT a finding, log and move on).
- `?shallow=true` lists keys without pulling the full tree (do this first before a full read).
- Write test: `PUT /.json` or `POST /.json` with a junk value → 200 = public write.

## 5c. Firebase config can also live in a mobile APK, not just a JS bundle

Native (Android/iOS) apps carry the Firebase config in `res/values/strings.xml`:
`firebase_database_url`, `google_storage_bucket`, `project_id`, `google_app_id`,
`gcm_defaultSenderId` (= messagingSenderId), `default_web_client_id`,
`google_crash_reporting_api_key`. Extract the app, grep `strings.xml`, then run the same
RTDB/Firestore/Storage probes above against those values. Decompile/decode flow lives in
`mobile-pentest` (jadx/apktool) and `apk-redteam-pipeline` (automated APK).

## 6. Mass assignment & admin gate

- Mass assignment: send `{is_subscriber:true}`, `{admin_role:"admin"}` to the profile/update
  endpoint. Correct behavior = joi `"…is not allowed"` (`.forbidden()`).
- Admin endpoints: see the "validation-before-authz" pitfall (linked from
  `autonomous-vuln-researcher`, and `api-authz-probe-ordering`). Don't claim a bypass on a
  400 from an incomplete body.

## 7. Second auth surface: the developer / API-key API

Many Firebase/SaaS targets ALSO expose a developer REST API authenticated by an
app-generated API key (`kn_…`, `pk_…`, `sk_…`) instead of the Firebase ID token —
often the SAME underlying routes (`/send-message`, `/get-chat-messages`, `/update-info`)
but through a different header. It is its OWN IDOR surface and must be probed
separately: the Firebase-token path can be correctly scoped while the API-key path has
a subtly different (weaker) authz check — or vice versa.

- Find it: `/docs/api-documentation`, an OpenAPI/swagger page, or an app endpoint like
  `/v1/api-retrieve-key` that hands the app its own key. Fetch the doc for the exact
  header (`Authorization: Bearer kn_…`), rate limit, and route list.
- Fetch YOUR key via the app endpoint, then replay the SAME cross-account resource-id
  tests (`<id>` = ai_id / group_id / object_id) against the dev API:
  - `get-<resource>` with YOUR key + OTHER user's id → must return empty/404, not their rows.
  - `update-<resource>` / `send-message` with YOUR key + OTHER user's id → must 404 "not found",
    not 2xx. A 2xx write to another user's id = cross-user write IDOR.
- Kindroid worked example: `GET /v1/get-chat-messages?ai_id=<otherUserKin>` with my `kn_` key
  returned `200 {"messages":[]}` (empty for a non-owned id, correct); `POST /v1/update-info
  {"ai_id":"<otherUserKin>"}` → `404 "AI not found"`; mass-assign fields still joi-forbidden.
- The account-management / email-change endpoint often leaks enumeration here too:
  `409 "already in use"` vs `200 success` vs `400 "matches your account"` = user-email enumeration.
  **This is a Low info leak and usually NON-reportable** — its only downstream
  use is targeted phishing (OOS social engineering), so it fails the
  "concrete attacker win" test (`report-gotchas` rule 4). Note it in coverage,
  don't draft a report around it. The operator rejects this class.

## Pitfalls

- **validation-before-authz**: an admin endpoint that returns 400 (validation) on an
  incomplete body is NOT missing authz. Send a COMPLETE valid body; only a 2xx (or a
  non-403) is a real bypass. Always confirm with valid fields before claiming escalation.
- **Plus-alias emails may silently not receive OTP** — some mail providers/targets drop
  `user+tag@gmail.com`. For a second identity, use a separate real inbox you can read
  (e.g. a second Gmail OAuth token).
- **Stale Gmail OAuth token → false "no OTP arrived".** Refresh the access token
  (`POST oauth2.googleapis.com/token` with `refresh_token` + `grant_type=refresh_token`)
  before every mail read, or `list messages` will return nothing and you'll burn OTP attempts.

## Support files

- `references/kindroid-2026-11.md` — worked real-target example (email-OTP → custom→ID
  exchange, App Check confirmed, storage-presign validation, the one Low finding).