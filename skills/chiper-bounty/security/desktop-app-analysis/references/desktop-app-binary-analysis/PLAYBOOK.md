---
name: desktop-app-binary-analysis
description: Analyze a target's Windows/macOS/Linux desktop app (MSI, DMG, EXE, tar.gz) pulled from its update channel — extract with zero extra tooling, verify code signing and updater integrity, find where the update URL is read from, and hunt local credential/key leakage.
metadata:
  hermes:
    tags: [security, desktop, msi, dmg, binary-analysis, supply-chain, code-signing, tauri, sparkle, netsparkle, electron]
---

# Desktop App Binary Analysis

## When to Use
- The programme's scope table lists a desktop app (Windows / macOS / Linux) or names
  "insecure update or code-signing mechanisms", "local data or credential leakage",
  "keychain or secure storage bypass" as qualifying classes.
- You have a download URL — usually a redirect service (`link.vendor.com/windows`)
  pointing at object storage.
- You need to answer four questions: is it signed, does the updater verify signatures,
  where does the update URL come from, and what is stored locally.

## Pipeline (do these in order)

1. **Resolve the download chain.** Follow the redirect to the object-storage URL. Probe the
   container: is listing public? is writing denied (`PUT`/`POST`/`DELETE`/`MKCOL`/`MOVE` →
   expect 401/412)? Record the appcast, the signature file, and every historical version.
   Old versions staying downloadable is a downgrade surface — note it, but it only matters
   once you control the URL.
2. **Download into the engagement dir**, never onto `C:` (it fills and installs fail silently).
3. **Extract** — see `references/msi-extraction-windows.md` and
   `references/dmg-udif-extraction-python.md`. Both work with zero extra tooling.
3b. **Read the installer's own manifest before extracting anything.** On Windows the MSI
   tables are readable through the COM object, read-only and without elevation:
   `New-Object -ComObject WindowsInstaller.Installer` → `OpenDatabase(path, 0)` →
   `OpenView("SELECT * FROM Registry|CustomAction|Property|...")`. It tells you three things
   that are invisible in the extracted payload:
   - **URL protocol registrations** — `Software\Classes\<scheme>` with a `URL Protocol` value
     and a `shell\open\command` that passes `%1` straight to the binary. That is a deep-link
     surface; whether the app validates the target (`hivenet://open?appUrl=...`) needs a
     logged-in run, so record "validation not determined", never a verdict.
   - **Shell namespace extensions** — CLSIDs under `Software\Classes\CLSID\{...}` plus
     Explorer `...\Desktop\NameSpace\{...}` and `...\MyComputer\NameSpace\{...}`. These load
     into explorer.exe, so a bug in them is a local-privilege surface rather than an app bug.
   - **Custom actions** that spawn `powershell.exe -ExecutionPolicy Bypass -File <script>`
     (read those scripts for path handling), and whether the install is per-user
     (`MSIINSTALLPERUSER` in the Property table).
4. **Verify the signature.** Windows: `Get-AuthenticodeSignature` (check Status, SignerCertificate,
   TimeStamperCertificate). macOS: the Apple OCSP/CRL URLs in the raw bytes prove a code
   signature exists; `LC_CODE_SIGNATURE` superblobs confirm it per-binary.
5. **Find the updater and its key.** Tauri/NetSparkle: search the UTF-16 string heap *around*
   the updater's own log messages — the Ed25519 public key sits adjacent to
   `"…public key is a stub; auto-updates disabled"`. A real 44-char base64 key means
   verification is live; a stub means auto-update is off entirely. Sparkle (macOS):
   `SUFeedURL` + `edSignature` + `SUAllowedURLSchemes`.
6. **Ask where the update URL is read from.** If it comes from a file inside a *per-user*
   install dir (`MSIINSTALLPERUSER=1`, `%LOCALAPPDATA%`), any process running as that user can
   repoint the updater. Signature verification limits the effect to vendor-signed content,
   i.e. a forced downgrade. Record it as hardening unless you demonstrate the downgrade.
7. **Local storage.** Grep for `tokens.dat`, `read_key`, `keychain`, `SecItem`,
   `LocalAuthentication`, `ProtectedData`, `PBKDF2`, `AesCryptoServiceProvider`. Note which
   KDF/wrapper is present; if you cannot determine the on-disk format without a logged-in
   run, say exactly that. On macOS also read the **sandbox entitlements** out of the
   strings — `com.apple.security.app-sandbox`, `com.apple.security.network.client`,
   `com.apple.security.application-groups` — and check for the *absence* of
   `get-task-allow` (a debug entitlement that would weaken the sandbox). Sandbox + Keychain
   + `LocalAuthentication` + `SUAllowedURLSchemes` together is a well-hardened client;
   say so in the table rather than leaving the row blank.
8. **Local listeners.** A loopback port for the OAuth callback (`127.0.0.1:8085` etc.) usually
   only opens after login. If it did not open in your run, record "not tested — needs a
   logged-in session", never "no listener".

## Pitfalls (all hit live)
- **An MSI has no plaintext table names** — its OLE streams are encoded, so grepping the MSI
  for routes or config finds nothing. Extract first, then grep the payload.
- **`cabarchive` cannot decompress LZX**, which is what MSI CABs use. Use `msiexec /a`
  (elevated) instead — recipe in the MSI reference.
- **A 200 with an empty body is not a finding.** Caddy answers `200` / 0 bytes for unknown
  paths on storage nodes; `/health` is the only path with content. A ~60-word ffuf list
  against such a node returns 60 "hits" that are all the same catch-all — read the
  `Content-Length` column, not the status column, before counting anything.
- **`/health` on infrastructure nodes leaks metrics** (RAM, CPU, version, commit hash,
  start_time, peer status). Record as info-level; health endpoints are usually intentional.
- **A raw Postgres error in a 404 body is an injection LEAD, not a finding — and it is
  usually a parameter, not interpolation.** `error while executing query: ERROR: invalid
  input syntax for type uuid: "abc'" (SQLSTATE 22P02)` names the engine and echoes your
  payload, which reads like a sink. Test it before believing it: fire the standard battery
  (`' OR 1=1`, `UNION SELECT NULL--`, `AND SLEEP(5)`, `CAST(version())`) and compare the
  responses. If every payload returns the *identical* cast error with the value echoed
  inside it, the value is bound as a query **parameter** to a `::uuid` cast and the error
  message is what echoes it — not injectable. Only a *changed* error (syntax error, timing
  delta, different SQLSTATE) is a finding. Record the battery as the control either way.
- **Do not report "the app installs per-user" on its own.** The impact must name a privilege
  boundary you can cross.
- **A URL protocol handler that passes `%1` to the binary is a surface, not a finding.**
  Whether `scheme://open?appUrl=<target>` validates its target is only answerable with a
  logged-in run; record "validation not determined" rather than either verdict.
- **A retired price id in an archived URL is a payment finding, not a desktop one.** If the
  update channel or the installer surfaces `?plan_id=price_...`, that belongs to the
  plan/entitlement class — see `saas-plan-entitlement-audit` §2c.
- **`argocd.*`, `*.rabbitmq.*`, `dev-*` hosts are usually out of scope** when the policy
  excludes staging. Fingerprint them, note them, do not exploit them.

## Honesty rule
Anything you could not test (listener needs a login, DMG payload not decompressed, signing
validity unverified for lack of platform tooling) is written as **"not tested"** with the
reason. It is never written as a verified negative.

## Reporting shape
Supply-chain findings are usually *controls that hold*. The deliverable is a short table:
signing → status; updater → key present/absent + what is verified; update URL → source and
who can write it; local storage → what is stored and how it is wrapped; listeners → tested or
not. One observation per row, each with the artefact that proves it.
