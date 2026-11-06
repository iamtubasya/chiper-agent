# Desktop app binary + auth-surface analysis

Session-proven recipes for the part of an engagement that starts once you have the installer:
Windows MSI, macOS DMG, the updater, the IdP, and the public config endpoint. Everything here was
executed end-to-end on a real target; the pitfalls are the ones that actually cost time.

---

## 1. Windows MSI

### Extract without 7-Zip / msiextract
- `msilib` may simply be absent from the active Python (`ModuleNotFoundError`) — do not build on it.
- `pip install cabarchive` then fails on real MSI payloads with `LZX compression not supported`.
- `cabextract` / `7z` are frequently not installed on the host.
- **Recipe that works** — administrative install with elevation:
```bash
mkdir -p msi_extract
powershell -NoProfile -Command "Start-Process msiexec -ArgumentList '/a','\"<ABS>\Hivenet.msi\"','/qn','/norestart','TARGETDIR=\"<ABS>\msi_extract\"' -Wait -Verb runAs"
```
- **Pitfall:** non-elevated `msiexec /a ... TARGETDIR=...` exits 0 and extracts *nothing*. The empty
  directory looks like a bad path; it is a missing elevation. Use `-Verb runAs`.

### Read MSI tables without installing
Windows Installer COM object, read-only (mode `0`):
```powershell
$wi = New-Object -ComObject WindowsInstaller.Installer
$db = $wi.OpenDatabase("<msi>", 0)
$v  = $db.OpenView("SELECT * FROM Registry"); $v.Execute()
while ($r = $v.Fetch()) { for ($i=1; $i -le 9; $i++) { $r.StringData($i) } }
```
- Tables present in a WiX MSI: `Registry`, `CustomAction`, `Property`, `File`, `Component`.
- **Pitfall:** `ServiceInstall` and `IniFile` throw a COMException when the table does not exist —
  wrap each table in its own try/catch or the loop dies mid-run.
- What to mine from these tables:
  - `Software\Classes\<scheme>` + `URL Protocol` + `shell\open\command` → custom protocol handler
    (note whether the command line passes `"%1"` straight into the executable).
  - `Software\Classes\CLSID\{...}` plus `Explorer\...\NameSpace\{...}` → shell namespace extension,
    and whether it is registered under HKCU (per-user) or HKLM.
  - `CustomAction` rows invoking `powershell.exe -ExecutionPolicy Bypass -File <script>` — read those
    scripts in full; they run during install/uninstall.
  - `Property` → `MSIINSTALLPERUSER`. `1` means a per-user install, so the install directory and any
    config files in it are writable by the user (see §2).

### Signature
```powershell
$s = Get-AuthenticodeSignature "<msi>"
$s.Status                 # Valid / NotSigned / HashMismatch / UnknownError
$s.SignerCertificate.Subject, .Issuer, .NotAfter, .Thumbprint
$s.TimeStamperCertificate.Subject
```
Report the signer, issuer and timestamp presence explicitly — "signed" without the chain is not a result.

### Strings sweep
Pull ASCII **and** UTF-16LE, then bucket by pattern:
`url`, `bucket`, `secret` (`api_key|secret|token|passphrase|private_key` with a value),
`jwt` (`eyJ...`), `aws` (`AKIA[0-9A-Z]{16}`), `slack` (`xox[baprs]-`), `github` (`gh[pousr]_`),
`electron` (`nodeIntegration|contextIsolation|asar|preload`), `tauri` (`wry|WebView2`),
`updater` (`appcast|sparkle|edSignature|latest.yml`).
A Tauri app shows `wry`/`WebView2`; an Electron app shows `nodeIntegration`/`asar`. Say which.

---

## 2. NetSparkle / Sparkle updater analysis

- The feed is signed: `appcast.xml` plus `appcast.xml.signature` (88 bytes), and each enclosure
  carries `sparkle:signature` (Windows/NetSparkle) or `sparkle:edSignature` (macOS/Sparkle).
- **Recovering the embedded Ed25519 public key.** In a .NET binary, user strings are length-prefixed
  and concatenated in the `#US` heap, so the key sits a few strings away from the updater's own log
  messages. Anchor on a unique log string and dump the neighbourhood:
```python
needle = "UpdateService: Ed25519 public key is a stub".encode("utf-16-le")
i  = d.find(needle)
seg = d[max(0,i-3000):i+3000]
for s in re.findall(rb"(?:[\x20-\x7e]\x00){4,}", seg):
    print(s.decode("utf-16-le"))
```
- **The "stub" tell.** Apps that ship a placeholder key log
  `"... public key is a stub; auto-updates disabled"`. If a real 44-char base64 key (decodes to 32
  bytes) is present instead, updates are live — and the code verifies *both* the appcast and the
  downloaded file (`"downloaded file failed the Ed25519 signature check"`). Quote that string as the
  evidence that the control holds.
- **Where the feed URL comes from is the real question.** If it is read from a file inside the install
  directory and the MSI is per-user (`MSIINSTALLPERUSER=1`), any process running as that user can
  repoint the updater. Signature verification limits the effect to vendor-signed content, i.e. a
  forced downgrade — so record it as hardening unless you actually demonstrate the downgrade.
- Check whether previous versions stay downloadable in the same bucket. If they do, the downgrade
  needs no hosting at all: just serve an older, still-valid appcast.

---

## 3. macOS DMG (UDIF) without macOS tooling

- Trailer: the last 512 bytes begin with `koly`.
- The XML plist sits near the end (find `<?xml`); `plistlib.loads` parses it. The chunk map is
  `resource-fork.blkx[]`, each `Data` being base64 of a `mish` block.
- `mish` layout (empirically confirmed): **204-byte header**, then 40-byte chunk entries, terminated
  by an entry whose type field is `0xffffffff`.
  - Chunk = `struct.unpack(">IIQQQQ", ...)` → type, comment, sectorNumber, sectorCount, offset, length.
  - Types seen: `0x00000000`/`0x00000002` raw, `0x00000001` zero-fill, `0x80000005` zlib.
- Assemble a sector-addressed image (`sector * 512`) across all blkx entries, then strings-sweep it.
- Mine the macOS app for: `com.apple.security.app-sandbox` (sandbox on), absence of `get-task-allow`,
  `SecItem`/`Keychain` + `LocalAuthentication` (TouchID) + `CommonCrypto`, Sparkle markers
  (`SUFeedURL`, `edSignature`, `SUAllowedURLSchemes`), and the bundle's custom scheme plus its OAuth
  redirect (e.g. `hivenet://<idp-host>/...`).
- **Pitfall:** a naive `LC_CODE_SIGNATURE` magic scan can miss signatures. Apple OCSP/CRL URLs in the
  image show the bundle is signed, but validity itself needs macOS tooling — state that limit instead
  of claiming a verified signature.

---

## 4. Public client-config endpoints

- Apps frequently bootstrap from `https://env.<vendor>.com/<env>` (`/prod`, `/dev`). Fetch every
  environment you can name. Expect API roots, analytics tokens, IdP client IDs, relay multiaddrs,
  feature flags.
- Decide honestly what is reportable: analytics tokens and public client IDs are public by design.
  The reportable parts are (a) any real secret, and (b) disclosure of dev/preprod/staging hostnames —
  and those are usually **out of scope to test**, so note them and do not probe them.
- Cross-check the same keys against the shipped `environment/*.env` files in the install dir; the
  local file is often the actual source of the update URL and the login redirect.

---

## 5. Zitadel / OIDC battery

- `/.well-known/openid-configuration` first — it lists the grant types and endpoints to aim at.
- `redirect_uri` allowlist: registered URI, attacker origin, suffix trick
  (`app.vendor.com.evil.com`), userinfo trick (`app.vendor.com@evil.com`), path traversal, http
  downgrade, fragment trick. Expect `400 invalid_request` for everything except the registered URI.
- M2M clients whose id is a readable name (e.g. `hivenet-m2m-user`):
  `grant_type=client_credentials` without a secret → `Errors.User.Machine.Secret.Invalid` (control
  holds); `jwt-bearer` → `assertion missing`.
- Device-code flow: start it for client A, then redeem the `device_code` with client B → expect
  `unauthorized_client` ("grant_type ... not allowed"). That is the proof the code is bound to the
  requesting client. Also redeem with no `client_id` → `invalid_request`, and with a truncated code →
  `invalid_grant`.

---

## 6. Auth0-based consoles (register, then capture a token)

- The universal login page uses **`input[name=username]` for login** and **`input[name=email]` for
  signup** — different selectors. Waiting on the wrong one times out after 30–40 s and looks like a
  broken page.
- After submit there is often a consent screen (`/u/consent`) that needs an explicit `Accept` click
  before the SPA is actually logged in.
- Capture the API token from the `https://<tenant>.auth0.com/oauth/token` **response body** rather
  than trying to read it out of the SPA's memory.
- Signup needs e-mail verification; the ticket URL is in the mail
  (`https://auth.<vendor>.com/u/email-verification?ticket=...`) and opening it completes the flow.
- Once authenticated, map the API with `GET /users/self` (it usually carries the org id and role),
  then run the cross-tenant matrix: read another org by id, reuse a chat `thread_id`, list another
  account's API keys, read another account's profile.

---

## 7. Verification pitfall — mailbox search windows

- **Searching "the last N messages" produces false negatives.** When confirming a vendor e-mail was
  delivered, filter by sender instead:
```python
from imap_tools import MailBox, AND
list(mb.fetch(AND(from_="vendor.com"), reverse=True, limit=40, mark_seen=False))
```
- A busy mailbox full of verification codes pushes the target mail outside a small window, and the
  script then reports `mail_sent=False` for something that was delivered. This cost a confusing
  "0 of 2 successful" result on a finding that was actually 4-for-4.
- If a log already contains that misleading negative, write a `<log>_NOTE.txt` beside it stating the
  cause and pointing at the corrected evidence. Never leave a contradictory artefact in the folder.

---

## 8. Object-id-as-capability (the highest-severity pattern from this session)

- When an API takes an id that also functions as a capability — a `shareRecordId`, an invite token, a
  journey id — test the **creation** endpoints for ownership enforcement, not only read/write on the
  object itself. `POST /metadata` accepting a foreign `shareRecordId` turned a "share link" into
  "claim somebody else's transfer".
- Check where identity fields come from. If the sender/owner is derived from the caller's token
  instead of from the object's owner, a caller can attach their own metadata — and trigger vendor-side
  e-mail — to an object they do not own.
- Ask "who learns this id?" If every recipient receives it, the attack precondition is being a
  recipient, which is exactly the population worth attacking from. Say so in the report's
  proved/argued table rather than implying an unauthenticated attacker.
