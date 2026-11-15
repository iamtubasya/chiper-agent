# Split-APK bundles + React-Native Hermes bundles: extraction pitfalls

Worked case: ByteWallet (`io.bytewallet.bytewallet`, pulled from apkpure, 2026-10-20).

## 1. apkpure/apkcombo downloads are SPLIT BUNDLES, not base APKs

Symptom: `unzip app.apk -d extracted` yields `config.*.apk`, `icon.png`, `manifest.json`, and a
nested `<package>.apk` — NO `classes*.dex`, NO `assets/`. Dex-strings extraction then silently
produces 0 results (a SUSPECT RUN, not a negative).

Correct sequence:
```bash
unzip -o -q app.apk "io.example.app.apk" -d nested      # the base APK is nested
unzip -o -q nested/io.example.app.apk -d base           # NOW you get classes*.dex + assets/
ls base/*.dex base/assets/
```
Split configs (`config.arm64_v8a.apk` etc.) only matter if you need native libs.

## 2. React Native apps: the JS lives in assets/index.android.bundle

- If `assets/index.android.bundle` exists, the app is RN — the interesting logic (API hosts,
  endpoint paths, deep-link schemes, key-shaped constants) is in the JS bundle, not the dex.
- **Hermes bytecode pitfall**: the bundle is compiled Hermes (magic `\xc6\x1f\xbc\x03...`). Its
  string table is stored SORTED and PACKED, so naive ASCII-run extraction (regex over raw bytes)
  returns long glued concatenations like
  `...bytewallet.bytewallet://fastbyte-checkInIdispatchCommandDefault...` — unusable for
  endpoint grepping and full of false "key-shaped" candidates.
- What still works on the raw bundle:
  - `re.finditer(rb'fastbyte|/api/|/v2/|bytewallet://', data)` with ±120 bytes of context —
    enough to recover endpoint paths and deep-link schemes
  - targeted searches for host fragments (`mobileapi`, `api-register`, `/bank/`, `/u/api/`)
- For a clean string table you need a Hermes disassembler (hbc dump tooling); if unavailable,
  context-window grepping + the live app's network calls are the fallback.
- Third-party SDKs in the dex/bundle are reconnaissance gold: Persona/Onfido (KYC), Plaid
  (bank linking), FaceTec (biometrics), OneSignal (push), Mapbox, Sentry — they tell you which
  flows exist before you touch the app.

## 3. What to extract and where to use it

Harvest: API base paths + version prefixes (`/v2/users/*`, `/bank/tx/send/*`), deep-link schemes
(`app://fastbyte?...`), hardcoded keys (test them against the live API — embedded keys that
unlock PII endpoints are a finding class), then replay the paths against the live backend with
a mobile-ish UA. Note: paths from an old app build may 404 on the current API — record which
host actually answers.
