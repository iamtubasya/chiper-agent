# Hardcoded-credential PoC + Android tooling pitfalls (proven 2026-10, FreeAgent Android)

Hard-won operational detail from a mobile engagement that ended in a **High** finding
(hardcoded production client credentials). Reuse the recipes, avoid the traps.

## 1. Getting the APK (the split trap)

* `https://d.apkpure.com/b/APK/<package>?version=latest` often returns a **split base APK**.
  `adb install` then fails with `INSTALL_FAILED_MISSING_SPLIT: Missing split for <pkg>`.
* Use the bundle instead: `https://d.apkpure.com/b/XAPK/<package>?version=latest` (~2x size).
  Send a mobile UA + `Referer: https://apkpure.com/`.
* **Verify the download before trusting it:** `unzip -l file.xapk | tail`. A truncated download
  looks fine with `file` ("Zip archive data") but lists **zero entries** — re-download.
* Install the splits: extract, then `adb install-multiple -r *.apk` (20 splits was normal).
* Sanity-check what is actually installed: `adb shell dumpsys package <pkg> | grep -E "versionName|versionCode"`.
  APKPure's "4.41.0" label and the device's `versionName 4.42.0` disagreed — only the pulled
  `base.apk` sha256 settles whether the analysed binary is the distributed one
  (`adb pull $(adb shell pm path <pkg> | grep base.apk)` → compare sha256).

## 2. jadx without the GUI

* `java -jar jadx-*-all.jar -d out app.apk` starts the **GUI** (AWT stack trace, a window opens —
  violates the user's "no visible window during automation" rule). Use the CLI wrapper:
  `bash tools/jadx/bin/jadx -d out -j 4 --deobf app.apk`.
* Full decompile of a 53 MB / 15-dex app is slow (~56% in ~10 min). Prefer targeted decompiles:
  `bash tools/jadx/bin/jadx --single-class <fully.qualified.Class> --single-class-output C.java app.apk`
  (each invocation still reloads the APK, so batch by intent, not one-per-turn).
* **Do not grep a partially written source tree** to find which class owns a method — it is slow and
  racy. Get the owner from the DEX method tables instead:
  `androguard` → `DEX(dex_bytes).get_methods()` → match `get_name()`, print `get_class_name()`.
  Seconds, exact, works before any decompile finishes.

## 3. Android SDK + headless emulator on Windows

* **SDK path must not contain spaces.** `sdkmanager.bat` splits its arguments:
  `'D:\data' is not recognized as an internal or external command`. Put the SDK somewhere like
  `C:\Android\sdk`.
* **`cmdline-tools` must live INSIDE the SDK root** (`C:\Android\sdk\cmdline-tools\latest\bin`).
  If it sits under a different root, `avdmanager` reports `Package path is not valid. Valid system
  image paths are: null` even though the system image is installed.
* Invoke the `.bat` files via `cmd.exe /c "C:\...\sdkmanager.bat" ...` and pass `--sdk_root=` to
  **sdkmanager** (it accepts it); **avdmanager does not** — give it `ANDROID_SDK_ROOT`, `ANDROID_HOME`
  and `ANDROID_AVD_HOME` as environment variables instead.
* Run the emulator **headless**: `-no-window -no-audio -no-boot-anim -no-snapshot -gpu swiftshader_indirect`.
  `HypervisorPresent=True` (from Win32_ComputerSystem) is a good signal that WHPX will work.
* `sys.boot_completed` can come back empty on some images — `getprop ro.build.version.release` +
  `adb devices` showing `device` is enough; just try the install.
* **`adb root` succeeds on `google_apis` (not `google_play`) images** and returns uid=0 — that is the
  enabler for installing a system-level CA for TLS interception.
* Always `adb emu kill` and verify `Get-Process emulator,qemu-system-x86_64` is empty afterwards,
  so nothing is left running.

## 4. Proving a hardcoded-credential finding end-to-end

Reading `BuildConfig` is not enough — reproduce the request the server accepts:

1. **JSON key names come from the Kotlin `@Metadata` `d2` array**, not from the field names:
   `@SerializedName` entries appear as `Lcom/google/gson/annotations/SerializedName;`, `value`,
   then the literal (`two_fa_code`, `user_id`, `client_id`, `client_secret`).
2. **Percent-encoding must match Android's `Uri.encode()`**, not Python's `quote()`:
   only `[A-Za-z0-9 _ - ! . ~ ' ( ) *]` pass through; everything else (including `@` and `.`)
   becomes **uppercase** `%XX`. Getting this wrong produces a signature error and looks like a dead
   end. The HMAC key order also matters (`secret + "&" + shared`, not the reverse).
3. **Read the error transition as the oracle:** `400 "Signature could not be verified"` = bad
   canonicalisation/key. `401 "…incorrect credentials"` (with a deliberately wrong password) =
   **signature accepted**. Then one run with the operator's own real credentials → `200` +
   `access_token`/`refresh_token`, and use the token in-process against a couple of API endpoints to
   complete the impact chain.
4. **Never persist the resulting tokens.** Print only status + key names; if a token already landed in
   an evidence file, rewrite that file with the value replaced by `<REDACTED>` and store a hash prefix.

## 5. Guarded scanner volley (vendor forbids scanning, operator insists)

When the disclosure policy forbids automated scanners but the operator orders a scan anyway:

* Ship one script with a **hard guard** (`FA_SCANNER_APPROVED=1` or it exits 2), a **scope allow-list**
  (refuse any host not explicitly in scope), low rate limits, and a `tools-usage.json` writer so the
  pipeline gate has its artifact.
* Monitor while it runs; watch for `302 → …/Preventing-fraud` style abuse redirects and **kill the
  volley the moment they appear** (kill the wrapper *and* the orphaned bash/child processes — the
  tracked session PID is not enough: check `Get-CimInstance Win32_Process`).
* Record the authorization basis (who said what, when) in PHASE_LOG, and note that such a flag was
  observed **temporary (~15 min)** — it is still not a reason to retry or to evade it via proxies.

## 6. Report/handover hygiene

* Evidence bundle: manifest analysis, decoded resources, decompiled sources, the PoC scripts, and a
  finding write-up with **explicit "verified / not verified" columns** — the honest split is what
  makes the report credible (a signature accepted is proof; an unreproduced forgery is not).
* Vendor e-mail drafts (**English**) need a real introduction — name, role, which channel/why now,
  what was and was not touched, short summary — before the technical sections. The operator sends it;
  drafts live in `[Gmail]/Draf` only.
