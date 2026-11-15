# Deep-link → WebView / auth-flow chain analysis (Android)

Method for turning "this deep link looks reachable" into either a proven chain or a documented dead end.
Worked example: MONETA Smart Banka 96.1.1 (`cz.moneta.smartbanka`), 5 chains walked, 0 payable.

## 1. Establish reachability from the manifest
- `MainActivity` `exported="true"` + `<intent-filter>` with `android:scheme="smartbanka"` and **no host**
  → any app/browser can fire it. Note `autoVerify`: `true` on the https App-Links filters, **absent** on the
  custom scheme → custom scheme is claimable by another installed app (scheme hijack), but only matters if the
  link carries a secret.
- Inventory every literal `scheme://...` string in the dex. If none carries a token/id/session, scheme
  hijacking has no data primitive — say so and stop.

## 2. Map ACTION → sink in the deep-link parser
Find the helper that turns the URI into an action (here `DeepLinkHelper.d()`), and enumerate the switch:
- `OPENURL` → external browser (`WebUtil.b` → `Intent.ACTION_VIEW`) — safe.
- `WEB` → in-app `WebViewFragment` with the URL taken straight from the link.
- `APPPAGE`/`APP_PAGE` → internal screen by name (`EFragmentLink.valueOf(str)`).

## 3. For a WebView sink, check three things independently
1. **URL allowlist.** A `RestrictedDomainsWebViewClient` only intercepts *navigation*
   (`shouldOverrideUrlLoading`). The **initial `loadUrl()` is not filtered** — so if the fragment replaces the
   restricted client with a plain `WebViewClient` (as `WebViewFragment` did), the first load is unfiltered.
2. **JavaScript.** `setJavaScriptEnabled(true)` is required for anything interesting.
3. **JS bridge.** `addJavascriptInterface(new JavaScriptInterface(), "NativeInterface")` is the real prize.
   Find the exact condition (here: only when `arg_script_file != null`) and then prove whether any reachable
   path can set that argument. Check the builder method (`R0(url,title)` sets only `arg_url`/`arg_title`),
   grep the literal across ALL dex, and check whether any enum entry maps to the WebView fragment class.
   If the count is 1 and it is hardcoded null → the bridge is unreachable. Dead.

## 4. Bundle-passthrough pattern (the subtle one)
Some flows copy **every** URI query parameter into a Bundle and hand it to a fragment
(`setLinkParameters(DeepLinkHelper.a(uri))` → nested `arg_linkParameters`). To score it:
- Enumerate every reader of the nested key (grep the literal).
- Enumerate the keys actually consumed (`entityId`, `contextId`, a generic `getString(key)` helper).
- For each key, find its sink: local settings lookup (`IIdentitySettings.f(String)`), a server call, or
  `loadUrl`. Only the last two matter. Record where each dies.

## 5. QR-login / cross-device login CSRF pattern
Attacker mints an `authenticationId` from an unauthenticated `generate-qr` endpoint, then deep-links the
victim's app with `URL=QRLOGIN&authenticationId=<attacker's>`. Before calling it a bug, walk the flow:
- Does the client send `init(authenticationId)` to the **server first**?
- Does the **server** return the scene the user is about to approve (so the client cannot forge what is shown)?
- Is the final `verify(...)` signed with the **victim's hardware-backed key** (PowerAuth/biometric)?
If yes to all three, this is the intended design and the attacker gains nothing beyond showing their own QR in
public — i.e. the social-engineering step the programme excludes. Document *why* it is not a bug.

## 6. Reporting discipline
Write the chain, the sink, and the exact place it dies into the engagement ledger. A dead chain with a
documented reason is reusable; a discarded lead with no reasoning gets re-investigated from scratch next time.
