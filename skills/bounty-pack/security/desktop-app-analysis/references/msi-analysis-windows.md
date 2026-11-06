# MSI analysis on Windows (no 7-Zip, no admin install)

Everything below was run against a real signed MSI on a Windows host with only Python,
PowerShell and the Go toolchain available.

## 1. Authenticode — close the signing class first

```powershell
$s = Get-AuthenticodeSignature '<file>.msi'
$s.Status              # Valid / NotSigned / HashMismatch ...
$s.SignatureType       # Authenticode
$s.SignerCertificate.Subject / .Issuer / .NotAfter / .Thumbprint
$s.TimeStamperCertificate.Subject
```

A valid EV cert with a timestamp closes "insecure code signing". Record the signer
subject verbatim — it is also useful for spotting a different legal entity than the
programme names.

## 2. Read the installer's tables WITHOUT installing

The Windows Installer COM object opens the database read-only:

```powershell
$wi = New-Object -ComObject WindowsInstaller.Installer
$db = $wi.OpenDatabase("<full path>.msi", 0)      # 0 = read-only
$v  = $db.OpenView("SELECT * FROM Registry"); $v.Execute()
while ($r = $v.Fetch()) { ... $r.StringData(1..n) ... }
```

Tables worth reading, in order of value:

| Table | What it gives you |
|---|---|
| `Registry` | custom protocol handlers (`URL:hivenet Protocol` + `shell\open\command`), COM CLSIDs, Explorer namespace extensions |
| `CustomAction` | what runs at install/uninstall — PowerShell with `-ExecutionPolicy Bypass`, bootstrappers, app relaunch |
| `Property` | `MSIINSTALLPERUSER` (per-user install!), `ProductVersion`, `UpgradeCode` |
| `ServiceInstall` | services created |
| `File` | the payload inventory |

`MSIINSTALLPERUSER=1` is the important one: it means the install directory is under
`%LOCALAPPDATA%` and therefore **writable by the user**. Cross-check that against any
config the app reads from its own install directory (see §5).

## 3. Extract the payload

`cabarchive` fails with "LZX compression not supported" on MSI streams — do not carve
CABs by hand. Use an administrative install, which needs elevation:

```powershell
Start-Process msiexec -ArgumentList '/a','"<msi>"','/qn','/norestart',
  'TARGETDIR="<outdir>"' -Wait -Verb runAs
```

Without `-Verb runAs` it exits 0 and extracts nothing — a silent failure that looks like
an empty installer.

## 4. Identify the framework before analysing

Sweep the raw binary for these markers:

| Marker | Framework |
|---|---|
| `wry`, `WRy`, `WebView2`, `WEBVIEW2` | Tauri (Rust + WebView2) |
| `electron`, `nodeIntegration`, `contextIsolation`, `asar`, `preload` | Electron |
| `DotNetRuntimeDebugHeader` export, `WinRT.*` type names, `System.*` | .NET |

Consequences: a Tauri app's web assets are usually served from the binary or a sibling
`assets/` dir; an Electron app has an `app.asar` to unpack; a .NET app can be read with
any IL decompiler and its COM surface is in the tables from §2.

## 5. Updater analysis (NetSparkle / Sparkle)

Search the binary for the updater's own log strings — they tell you exactly what the code
checks:

```
"UpdateService: Ed25519 public key is a stub; auto-updates disabled"
"UpdateService: UPDATE_CHECK_URL not configured; auto-updates disabled"
"UpdateService: downloaded file failed the Ed25519 signature check: {0}"
```

The **public key sits in the user-string heap next to those log strings**. Dump the
UTF-16 strings in a ±3 KB window around the "is a stub" message and look for a 44-char
base64 blob that decodes to 32 bytes:

```python
needle = "UpdateService: Ed25519 public key is a stub".encode("utf-16-le")
i = d.find(needle)
seg = d[i-3000:i+3000]
strs = re.findall(rb"(?:[\x20-\x7e]\x00){4,}", seg)   # -> the key is in here
```

A real key (not `AAAA...`, not a placeholder) plus the "failed the signature check" log
line means both the appcast **and** the downloaded file are verified — the update class
is closed. Say so in the report.

**Then check where the URL comes from.** Hivenet shipped `environment/production.env`
inside the install dir containing `UPDATE_CHECK_URL=...`. With a per-user install that
file is user-writable, so any process running as the user can repoint the updater. The
signature check limits the effect to vendor-signed content, i.e. a forced downgrade to an
older version that is still hosted publicly. Report as hardening unless you demonstrate
the downgrade.

## 6. Local storage

Strings to look for and what they imply:

| String | Meaning |
|---|---|
| `tokens.dat`, `Error storing tokens` | auth tokens on disk |
| `read_key`, `Stored read_key could not be unwrapped` | a wrapped master key |
| `sync.db`, `account.json` | local state DBs |
| `PBKDF2`, `AesCryptoServiceProvider`, `ProtectedData`, `CryptProtectData` | the crypto that is available |
| `SecItem`, `Keychain`, `LocalAuthentication` (macOS) | proper platform storage |

The question that decides reportability: **when no passphrase is set, is the master key
wrapped with something the user knows, or with DPAPI?** DPAPI means any process running
as that user can unwrap it — which is a design choice, not a bypass, unless the vendor
documents a passphrase as protecting the data. Determining the on-disk format needs a
logged-in run; if you cannot do that, record it as an open question, not a finding.

## 7. Local listeners and deep links

Look for loopback ports in the binary (`http://127.0.0.1:8085`, MSAL's
`FindFreeLocalhostRedirectUri`). They usually only open after login — if you cannot get a
logged-in session, say the listener is untested rather than claiming it is absent.

For custom protocol handlers, the installer table gives you the command
(`"[INSTALLFOLDER]App.exe" "%1"`). Then find the parsing code's validation strings:
`appUrl`, `appOpenUrl`, `://open`, `://callback`, `GetWebAppUrl`. If there is no host
allowlist near them, the deep link can likely load arbitrary content in the app's WebView
— that is the RCE-class lead, and it needs a live run to prove.

## 8. Secrets sweep

Run this over the raw binary **and** every extracted file. Zero hits is a real result and
worth stating:

```python
pats = {
 "secret": r"(?i)(api[_-]?key|client[_-]?secret|secret|token|passphrase|private[_-]?key)\s*[:=]\s*[\"']?([A-Za-z0-9._\-/+]{16,})",
 "jwt": r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}",
 "aws": r"AKIA[0-9A-Z]{16}",
 "gh":   r"gh[pousr]_[A-Za-z0-9]{20,}",
}
```

Note that a compressed payload hides everything: if the sweep is clean on the installer,
that proves nothing about the payload — extract first, then sweep again.
