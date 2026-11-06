# APKCombo acquisition + androguard baseline — worked case (Vinted Android, 2026-10-01)

Target: Vinted Bug Bounty (Bugcrowd `vinted-uab-mbb`), mobile app `fr.vinted` in scope.
Result: APK obtained (v26.38.0), static analysis complete, **no credential/debug finding** —
the useful output of this file is the *acquisition recipe* and the *clean-baseline checklist*.

## 1. Acquisition

| Route | Outcome |
|---|---|
| `curl https://d.apkpure.net/b/APK/fr.vinted?version=latest` | **403**, 5 615 B HTML (`Just a moment...`) |
| `curl https://apkmirror.com/?...&s=vinted` | **403**, Cloudflare challenge |
| Playwright → `apkpure.com/vinted/fr.vinted/download` | page renders, but the direct link stays CF-gated |
| Playwright → `apkcombo.com/vinted/fr.vinted/download/apk` + `expect_download` | **works** — 141 MB `.xapk` |

The only link on the ApkCombo page worth taking is the `apkcombo.com/r2?u=<urlencoded>` redirector.
Read it from the DOM (`element.href`, a property — the raw attribute is HTML-escaped with `&amp;`),
then let the browser download it:

```python
href = await pg.evaluate("""() => {
  const a=[...document.querySelectorAll('a')].find(e=>/r2\\?u=|cloudflarestorage/.test(e.href||''));
  return a ? a.href : null; }""")
async with pg.expect_download(timeout=900000) as di:
    await pg.evaluate("(u)=>{const a=document.createElement('a');a.href=u;a.download='';document.body.appendChild(a);a.click();}", href)
await (await di.value).save_as("app.xapk")
```

**Do not** hand the extracted S3 URL to `curl` or `ctx.request.get`: AWS4 `SignatureDoesNotMatch`
(403, ~3.4 KB XML). Two independent causes — `&amp;` entities surviving into the query string, and
the signature being time-bound (`X-Amz-Expires`) and IP-pinned.

**Always gate on magic bytes.** Every failure above produced a 3-6 KB text/XML file with the right
extension. `head -c 4` must be `PK`; anything else is an error document, not an APK.

## 2. Unpacking the `.xapk`

`.xapk` / `.apks` = ZIP of split APKs + `manifest.json`. The installable payload is the largest
member (base), not the first entry:

```python
import zipfile
z = zipfile.ZipFile("app.xapk")
# fr.vinted.apk 129 MB | config.arm64_v8a.apk 8 MB | config.xxhdpi.apk 3 MB | manifest.json
z.extract("fr.vinted.apk", "extract")
```

`manifest.json` also documents `package_name`, versionCode and the locale list — cheap metadata
before any decompilation.

## 3. Static analysis with androguard 4.x (no JDK needed)

Manifest, exported components, deep links and the string sweep were all done in one script
(`analyze_apk.py`) using:

- `APK.get_android_manifest_xml()` → lxml Element; **`get_elements()` does not exist in 4.x**.
- Attribute lookups are namespaced: `A = "{http://schemas.android.com/apk/res/android}"`.
- Deep links: `mani.findall(".//data")` then `scheme` / `host` / `pathPrefix`.
- Silence the logger first — androguard's DEBUG output produced a 1.8 MB log for one run:
  `from loguru import logger; logger.remove()`.

## 4. Clean baseline observed (useful as a "nothing here" template)

| Check | Vinted 26.38.0 |
|---|---|
| `android:debuggable` | absent |
| `usesCleartextTraffic` / `networkSecurityConfig` | not insecure |
| Hardcoded secrets (`AIza`, `AKIA`, JWT, firebaseio, `sk_live`, `xoxb`) | **0 hits** |
| Distinct hosts in DEX/resources | 283 |
| Non-scope internal hosts leaked (docs only) | `flags.svc.vinted.com`, `metrics-ingress.svc.vinted.com`, `logs-ingress.svc.vinted.com`, `tracking-event-pipeline-grpc.svc.vinted.com`, `localisation-assets.vinted.com`, `images.vinted.net`, `vintedapp.com`, `vinted.org` |

Exported components without a permission, all of them **textbook third-party/tooling noise** —
do not file these as findings on a program that excludes DoS/crashes, anti-debug and third-party
SDK issues:

- `androidx.compose.ui.tooling.PreviewActivity` (test tooling shipped in release; launching crashes the app → DoS)
- `androidx.test.core.app.InstrumentationActivityInvoker$BootstrapActivity | $EmptyActivity | $EmptyFloatingActivity`
- `com.facebook.FacebookContentProvider`
- `com.mbridge.msdk...NetWorkChangeReceiver`, `com.ogury.core.internal.LogEnablerReceiver` (ad SDKs)
- the app's own launcher activity (`com.vinted.feature.shell.MDActivity`) — exported by design

Deep links seen (all expected for a marketplace): `https://www.vinted.<tld>/*` for every country
domain, `fr.vinted://`, `vintedfr://`, `https://clicks.vinted.org/f/a/`, `fbconnect://cct.fr.vinted`,
`adyen3ds2://`, `market://`, `sms://`.

**Scope discipline:** every internal host above is a subdomain the program's brief does not list.
They were recorded and never contacted — the same rule as the web-side recon. A host referenced by
an in-scope app is not thereby in scope.
