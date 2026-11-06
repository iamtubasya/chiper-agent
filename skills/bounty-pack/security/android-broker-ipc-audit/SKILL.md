---
name: android-broker-ipc-audit
description: Audit an Android APK's exported IPC surface (services/activities/receivers) for missing caller validation. Use when a bug-bounty scope includes a mobile app (MSAL/ADAL brokers, Authenticator, SSO agents, token-sharing services) and you need to find unauthorized token/account access. Covers the per-operation validateCallingApp coverage technique, manifest permission checks, and the false-positive traps.
metadata:
  hermes:
    tags: [android, mobile, ipc, broker, msal, adal, aidl, caller-validation, bug-bounty]
---

# Android Broker IPC Audit — missing caller validation

## When to use
Bug-bounty scope includes an Android app that acts as an **identity broker / SSO agent /
token provider** (Microsoft Authenticator, MSAL/ADAL broker hosts, any app exposing
`IBrokerAccountService`-style AIDL). Goal: prove that an unprivileged third-party app can
enumerate accounts, mint tokens, or remove accounts.

## Step 0 — get the real artifact
- Download the **latest** APK (programs require latest version). APKPure direct:
  `curl -sL -A "<chrome UA>" "https://d.apkpure.com/b/APK/<package>?version=latest" -o app.apk`
  Verify with `file app.apk` (must say "Android package (APK)"), not just HTTP 200.
- Record `versionName` / `versionCode` / `minSdk` / `targetSdk` — the report needs them.

## Step 1 — manifest: exported WITHOUT permission (the entry condition)
Parse the binary manifest (do not read strings):
```python
from androguard.core.apk import APK
apk = APK("app.apk"); raw = apk.get_android_manifest_xml()
AND = "{http://schemas.android.com/apk/res/android}"
for node in raw.iter():
    if node.tag in ("service","activity","receiver","provider"):
        print(node.tag, node.get(AND+"name"), "exported=", node.get(AND+"exported"),
              "permission=", node.get(AND+"permission"))
```
Flag every `exported="true"` with `permission=None`. Also dump every intent-filter
scheme/host (deep-link surface) and app-level `allowBackup` / `usesCleartextTraffic` /
`networkSecurityConfig`.

## Step 2 — decompile
`jadx -d out -j 4 --no-debug-info --no-inline-anonymous app.apk` (63 MB APK ≈ 3-5 min,
~40k files). For single classes use `jadx --single-class <fqcn> --single-class-output f.java -r`.
androguard works for manifest; jadx for logic. `apktool` is not required.

## Step 3 — THE technique: per-operation validation coverage
Do not stop at "there is a validateCallingApp()". Enumerate **every AIDL method** on every
exported service and check whether the validation gate actually fires for that operation.

Pattern to look for (real example, MSAL broker):
```java
public void validateCallingApp(int uid, String operationName, Bundle b) {
    if (operationName.equals("AcquireTokenSilentMsalBrokerOperation")) {   // <-- ONE op only
        MsalSilentCallerValidator.INSTANCE.validate(...);
    }
    // every other operation name falls through = NO VALIDATION
}
```
Then confirm the dispatch chain really reaches it on **both** branches:
- legacy branch (`AbstractRequestDispatcherHelper.execute` -> `service.validateCallingApp(uid, op, bundle)`)
- modern branch (`BrokerOperationRequestDispatcher.dispatch` -> `request.getService().validateCallingApp(request)`
  -> `IBrokerService.DefaultImpls` -> delegates to the `(uid, op, bundle)` overload)
If a path calls `service.getOperationByName(op).execute(bundle, uid)` directly, validation is skipped.

Also check the "policy object" pattern for a **no-op-by-construction** gate:
```kotlin
private final PolicyAction determineAction(boolean shouldEnforce, PolicyResult r) {
    if (r == PolicyResult.ALLOWED) return PolicyAction.ALLOWED;
    return shouldEnforce ? PolicyAction.BLOCKED : PolicyAction.WOULD_BLOCK;   // WOULD_BLOCK != BLOCKED
}
if (action != PolicyAction.BLOCKED) return;    // returns => caller authorized
```
If `approvedCallers` is `emptySet()` and the enforcement **flight defaults to false**, the gate
never blocks. Verify the flight default in the enum's static initializer (`Boolean bool = Boolean.FALSE;`).

## Step 4 — the weak guard that looks like a guard
```java
public static boolean isValidCallerPackage(Context c, String callerPackage, Integer uid) {
    for (String pkg : c.getPackageManager().getPackagesForUid(uid))
        if (callerPackage.equalsIgnoreCase(pkg)) return true;   // package NAME only
    return false;
}
```
This is a confused-deputy guard, **not authentication** — the attacker puts its own package
name in the request bundle. Only `PackageManager` signature / certificate-thumbprint checks count.

## Step 5 — close the negatives (this is what makes the report credible)
Prove the *same app* validates properly elsewhere, so the omission reads as a bug:
- signature check in `onTransact()` + `SecurityException`
- `SignatureVerifier.isCallingUidTrusted(uid, ...)` on every operation
- `CallingAppValidator(ctx, AppRegistry.X).requireAllowedCaller(uid)`
- intent-redirection wrappers that verify target signature + class prefix + reject
  `FLAG_GRANT_READ/WRITE_URI_PERMISSION`
- dead bypasses: `AtomicBoolean(false)` with no setter anywhere in the app = unreachable
Also check WebView hardening (`setAllowFileAccessFromFileURLs(false)`, `addJavascriptInterface`
only in OAuth clients) and app-level flags.

## Step 6 — runtime proof is mandatory before reporting
Operator rule: unreproduced = UNSTABLE = do not report. You need a device/emulator with the
app installed and one signed-in account, plus a PoC app declaring **no permissions**:
```java
Intent i = new Intent("<service action>"); i.setPackage("<target pkg>");
bindService(i, conn, Context.BIND_AUTO_CREATE);
IXxxService svc = IXxxService.Stub.asInterface(binder);
svc.getAccounts(new Bundle());          // expect account list with no auth
```
`adb devices` + no AVD = you cannot prove it; say so explicitly and hand over the PoC plan.

## Pitfalls
- jadx may fail on Kotlin enum classes ("Enum visitor error") — read the `static {}` block
  from the raw output; defaults are usually `Boolean bool = Boolean.FALSE` / `bool2 = TRUE`.
- Large validators may dump as "Unreachable block / Method not decompiled" — do not assume
  they are weak; treat as unknown and say so.
- AIDL methods not declared in the `.aidl` interface are NOT remotely reachable even if
  `public` on the Stub. Check `IBrokerXxxService.java` for the declared method list.
- Pipeline "CONFIRMED" verdicts often mean *response stability*, not exploitation. Always
  re-check raw reflection / console / OOB canary by hand before believing a DOM-XSS hit.
- **SSTI arithmetic probes false-positive on any page containing GUIDs.** A checker that
  tests `{{7*7}}` -> "49" and control `{{7*6}}` -> "56" will "CONFIRM" when BOTH digits are
  already in the static response. Real case: `login.microsoftonline.com/common/oauth2/v2.0/authorize`
  was reported CONFIRMED ssti because `client_id=4765445b-32c6-49b0-...`, the sessionId GUID and
  the instrumentationKey all contain "49"/"56". Verify by requesting the URL with **no payload**
  and checking whether the digits are still present — they were. `control_rewritten:false` and
  identical a/b excerpts are the tell. Always run a no-payload baseline before believing any
  substring-based detector.
