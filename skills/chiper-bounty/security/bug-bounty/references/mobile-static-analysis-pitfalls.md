# Mobile static-analysis pitfalls (APK white-box)

Lessons from a full white-box of a production banking APK (cz.moneta.smartbanka 96.1.1, 37 dex,
94 MB). Several of these cost real time and each one is a way to *falsely* conclude "bug" or
"no bug".

---

## 1. `jadx -d` "finished with errors, count: N" is NOT missing classes

A full decompile of one 14.6 MB dex reported `ERROR - finished with errors, count: 4658` out of
6697 classes. That reads like a 70% failure. It is not:

- It counts **per-method** decompilation failures on obfuscated/optimised code.
- **10350 `.java` files were still produced** (inner classes inflate the count above the class count).
- Every security-relevant class was present and readable.

Do:
```bash
jadx --no-res -j 2 -d out_cN dexs/classesN.dex          # full tree, accept the error count
jadx --no-res --single-class <fqn> --single-class-out X.java sb.apk   # targeted, cheap, reliable
```
Targeted `--single-class` runs succeeded every time and took ~20 s each on a 72 MB APK. Use the
full tree for grep-ability, single-class for reading logic. Budget ~1.5–2.5 GB heap; on a 6 GB
host run them in the background, not in the foreground.

## 2. Dex string-pool false positives (the biggest trap)

A method name appearing in a dex string table does **not** mean it is called. Both of these looked
like findings and were not:

- `getExternalStorageDirectory` — appeared in 3 dex. Context dump showed it sitting in an
  alphabetical run with `getExternalCacheDirs`, `getExternalFilesDir`, `getExtensions` … i.e. the
  method-name pool carried by libraries. No caller.
- `setAllowUniversalAccessFromFileURLs` — appeared once, again in a name pool next to
  `setAllowFileAccess`, `setAllowContentAccess` … The only real call site was
  `SecuredWebView.a()` setting it to **false** — a control, not a weakness.

Verification ladder before claiming either direction:
1. Count occurrences across **all** dex concatenated (not one dex).
2. Dump ±160 bytes around each hit and look for the alphabetical-name-pool signature.
3. Resolve the owning class with `androguard` `DEX.get_classes()` and read the method body.
4. Only then claim "called" or "not called".

## 3. "Hidden debug menu in production" — check the layout, not just the listener

A click listener on `R.id.btn_debug_menu` plus ~200 debug items compiled into the release dex looks
like a shipped backdoor. It was not:

- `res/layout/fragment_about.xml` declared `btn_debug_menu` and `btn_developer_mode` with
  `android:visibility="gone"`.
- No code anywhere called `setVisibility(VISIBLE)` on them.
- A `GONE` view cannot be clicked; only `View.performClick()` could reach the listener, which needs
  an already-installed attacker app with accessibility/root.

Always decode the binary layout (`androguard.core.axml.AXMLPrinter` on
`res/layout/<f>.xml`) and grep for every `setVisibility` on that id before reporting. Report the
*absence* of an enabler as the reason it is not a finding.

## 4. Kotlin `defpackage/` obfuscation

App code is under `cz/moneta/...` but a lot of real logic lands in `defpackage/` (e.g. `h52.java`,
`v1.java`, `c0.java`). When an interface's implementor is not obvious, find it by class-membership
scan across all dex:

```python
from androguard.core.dex import DEX
for c in DEX(apk_bytes).get_classes():
    if 'SomeFeature' in c.get_name() and 'Companion' not in c.get_name():
        print(c.get_name(), [m.get_name() for m in c.get_methods()])
```
`Companion` objects that delegate via `ServiceLoader` are a dead end — the real impl is elsewhere.

## 5. Deep-link → WebView: where the chain actually dies

The recurring "in-app WebView loads attacker URL" lead. Check all four gates before scoring it:

1. Is the activity `exported=true` with an intent-filter for the scheme? (reachability)
2. Does the handler pass the URL to `loadUrl()` with JS enabled? (sink)
3. Does it replace a restricting `WebViewClient`? (many apps ship
   `RestrictedDomainsWebViewClient` that only blocks *navigation*, never the initial load — so the
   initial load is the real gap)
4. **Is a JS bridge attached?** `addJavascriptInterface` is usually gated on an
   `arg_script_file`/script argument. If no deep-link path ever sets it, there is no bridge and the
   impact collapses to in-app phishing — which most programmes file under "content spoofing"
   (Hall-of-Fame only).

Verify gate 4 across **all** dex: `arg_script_file` had exactly 1 occurrence in 94 MB, and the
enum mapping fragments had 0 entries for the WebView class. That is what closed the chain.

## 6. Custom-scheme hijacking: check whether the link carries a secret

An unverified custom scheme (`autoVerify=None`) is claimable by any installed app, which sounds
like a finding. It is only a finding if the intercepted link carries something valuable. Grep every
literal `<scheme>://` string in the binary and list what parameters they carry. Here they were
`branches`, `iban`, `cnb`, `clientCenterPhone`, `emailFullWording`, one promo page — no tokens, no
IDs. Conclusion: hijack inherits navigation, not data. Not reportable.

## 7. Controls worth confirming as *verified* (so the next run skips them)

On a mature banking app these were all genuinely healthy; re-checking them from scratch wastes a
day:
- `android:debuggable` absent, `allowBackup=false`, no cleartext flag.
- `network_security_config` pins the API host; server-served pin list
  (`/sb/ssl-pinning.json`) rotates **with overlap** — check the full list before claiming expiry.
- `EncryptedSharedPreferences` + `androidx.security.crypto` + Tink `AndroidKeystoreKmsClient`.
- PowerAuth biometric path uses the real keystore; the SDK's `DummyBiometricKeystore` appears only
  as its own declaration (occurrence count 1 in 94 MB) and `invalidateByBiometricEnrollment` is
  honoured.
- All `provider` entries (incl. `FileProvider`) `exported=false`.
- App Links properly published (`autoVerify=true` + `assetlinks.json` on both hosts).
