# Desktop app supply-chain analysis (Windows MSI / macOS DMG)

Worked on Hivenet (2026-10): Windows MSI 97.8 MB (Tauri + WebView2, .NET shell hook),
macOS DMG 43.8 MB. Everything below is the path that actually worked on a Windows host
with git-bash and **no 7-Zip installed**. Companion to `mobile-app-bundle-recon.md` —
same idea, desktop side.

## 1. Map the download / update channel BEFORE touching the binary

- Short links (`link.vendor.com/windows`, `link.vendor.com/macOS`) 302 to object
  storage. Follow them: `curl -sS -L -o /dev/null -D - -w "%{redirect_url}"`.
- Container listing is frequently public and is the single highest-value read:
  `GET https://<swift-host>/v1/AUTH_<tenant>/<container>?format=json`
  returns every object with `bytes`, `hash`, `last_modified`, `content_type`.
  That is the full version history, the appcast, and the signature files.
- Test writes with a canary key, then delete it: `PUT` / `POST` / `DELETE` / `MKCOL` /
  `COPY` / `MOVE`. A 401/412 across all of them is the control that makes
  "update hijack" unreachable — record it as a verified negative, not as "the bucket
  is secure".
- Check whether **old versions stay downloadable**. That is the downgrade surface; it
  only matters once an attacker controls the appcast URL, so pair it with the next item.
- Check the appcast: Sparkle-style `appcast.xml` + `appcast.xml.signature`, or a
  per-enclosure `sparkle:edSignature` / `sparkle:signature`. Note whether the feed is
  served over HTTPS and whether the signature is a raw hash of the XML (compare against
  sha1/sha256/sha512 of the file — if it matches none of them it is an asymmetric
  signature, which is the good case).
- Look for a public bootstrap config: `env.vendor.com/prod`, `apps-version.json`,
  `/config`. Expect hostnames (dev / preprod / staging) and client IDs but usually no
  secrets. Read every `BYPASS_*` / feature flag — a flag that is `true` in prod and
  disables a security check is a finding on its own.

## 2. Windows MSI without 7-Zip

Order that works:

1. **Signature first** (cheap, and it decides how much the rest matters):
   ```powershell
   $s = Get-AuthenticodeSignature 'C:\path\Hivenet.msi'
   $s.Status; $s.SignerCertificate.Subject; $s.SignerCertificate.NotAfter
   ```
   `Valid` + EV + timestamped = the signing control holds; say so and move on.
2. **Extract the payload.** `cabarchive` fails on MSI Cabs ("LZX compression not
   supported") and `msilib` may be missing from the interpreter. Use the installer
   itself, elevated:
   ```powershell
   Start-Process msiexec -ArgumentList '/a','"D:\path\Hivenet.msi"','/qn','/norestart',
     'TARGETDIR="D:\path\out"' -Wait -Verb runAs
   ```
   Non-elevated `msiexec /a` silently produces an empty directory — if the output dir
   is empty, that is why, not a broken MSI.
3. **Read the tables without installing anything** (Registry / CustomAction /
   Property / ServiceInstall) via the Windows Installer COM object. Write the script to
   a `.ps1` file and run it with `-File`; inline `-Command` with
   `$obj.GetType().InvokeMember(...)` trips PowerShell parser errors:
   ```powershell
   $wi = New-Object -ComObject WindowsInstaller.Installer
   $db = $wi.OpenDatabase("D:\path\Hivenet.msi", 0)
   $v = $db.OpenView("SELECT * FROM Registry"); $v.Execute()
   while ($null -ne ($r = $v.Fetch())) { ... $r.StringData($i) ... }
   ```
   What the tables give you that strings never will:
   - `Registry` → URL protocol registration (`Software\Classes\<scheme>` +
     `shell\open\command` = `"<install>\App.exe" "%1"`), shell namespace extension CLSIDs
     under `Explorer\Desktop\NameSpace` / `MyComputer\NameSpace`, per-user vs per-machine.
   - `CustomAction` → anything run at install/uninstall, especially
     `powershell.exe -ExecutionPolicy Bypass -File <script>` (read those scripts in full;
     they run elevated during install).
   - `Property` → `MSIINSTALLPERUSER` (1 = install dir and its config files are
     user-writable), `ProductVersion`, `UpgradeCode`.

## 3. Finding the interesting constants inside a large .NET binary

`Hivenet.exe` was 182 MB with 401k unique strings. What worked:

- Extract both encodings: `re.findall(rb"[\x20-\x7e]{8,}", d)` for ASCII and
  `rb"(?:[\x20-\x7e]\x00){8,}"` decoded as `utf-16-le` for .NET user strings. Write the
  set to a file once and grep it repeatedly instead of rescanning.
- **To find a key that sits next to a known log line**, encode the needle as UTF-16LE,
  locate it in the raw bytes, then dump ±3 KB and decode the UTF-16 strings in that
  window. This is how the updater's Ed25519 public key was found sitting between
  `UPDATE_CHECK_URL` and `"Ed25519 public key is a stub; auto-updates disabled"`.
- Grep the string set for the *behavioural* markers, not just secrets:
  `tokens.dat`, `read_key`, `unwrap`, `passphrase`, `PBKDF2`, `ProtectedData`,
  `CryptProtectData`, `127.0.0.1:<port>`, `://open`, `appUrl`, `NetSparkle`, `edSignature`.
  Each one names a subsystem worth a section in the report.
- A 44-char base64 blob that decodes to exactly 32 bytes next to updater strings is an
  Ed25519 public key. If the code also contains `"... is a stub; auto-updates disabled"`
  then the build distinguishes real keys from placeholders — find which one shipped.

## 4. Updater verdict, stated the way a triager accepts it

Say all four things, in this order:
1. feed URL and transport (HTTPS?),
2. what is signed (appcast only, or appcast **and** the downloaded file — look for a
   "downloaded file failed the signature check" string, that is the enforced one),
3. where the key lives (embedded constant vs config file),
4. where the **URL** comes from. A user-writable config file (`%LOCALAPPDATA%\...\
   environment\production.env` on a per-user MSI install) is the real weakness: any
   process running as the user can repoint the updater. Signature verification caps the
   impact at "serve vendor-signed content", i.e. a forced downgrade to a version that is
   still publicly hosted. If you cannot demonstrate the downgrade end-to-end, report it
   as hardening, not as a finding — the programme's "no theoretical findings" rule bites
   here.

## 5. macOS DMG

A DMG whose first bytes are a zlib header (`x\xda`) is compressed; raw `strings` only
shows the Apple OCSP/CRL URLs and the plist DTD. To analyse the `.app` you must
decompress the blob map first — budget for it, and say plainly in the report that the
payload was not analysed rather than implying it was clean.

## 6. Local storage and the local listener (the paying classes)

Programmes pay for "local data or credential leakage", "keychain / secure storage
bypass", "insecure update", "improper certificate validation". So:

- Find the token/key files (`tokens.dat`, `account.json`, `sync.db`, `read_key`) and the
  wrapping primitives (PBKDF2 / AES / DPAPI). The decisive question is **what wraps the
  master key when the user sets no passphrase** — DPAPI-only means any process running as
  that user can unwrap it, which is a design choice, not a bypass; say which one it is.
- A loopback listener (`127.0.0.1:8085`, `:3050`) for the OAuth callback usually only
  binds **after login**. Running the app without a session proves nothing — record
  "listener not observable without a logged-in session, binding and auth untested"
  rather than "no listener".
- Protocol handlers (`hivenet://open?appUrl=`) are the classic WebView-load-arbitrary-URL
  primitive. Without a decompiler you cannot close the validation question; name it as
  the unproven hop instead of guessing.

## 7. Pitfalls that cost time here

- `msiexec /a` without elevation → empty output dir. Use `-Verb runAs`.
- Inline PowerShell `-Command` with `InvokeMember` → parser errors. Use a `.ps1` file.
- `re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"')` inside a quoted heredoc arrives with
  the backslashes eaten and dies with "unterminated character set". Avoid regex for
  SSE/JSON: split lines and `json.loads(line[6:])` after `line.startswith("data: ")`.
- Patching a generator with `python - <<'PY'` + `s.replace(old, new)` where `new`
  contains `\n` gets mangled by the tool layer and produces
  `SyntaxError: unterminated string literal`. Write the file with a quoted heredoc
  (`cat > gen.py <<'PYEOF'`) or emit it line-by-line, then `ast.parse` before running.
- IMAP: `fetch(reverse=True, limit=8)` misses mail when the inbox is busy. Search by
  sender — `mb.fetch(AND(from_="vendor.com"), reverse=True, limit=40)` — and never read
  "not found in the last N" as a negative.
