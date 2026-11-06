# Extracting an MSI on Windows with zero extra tooling

Two problems block the obvious approaches, and both have clean fixes.

## Why the obvious paths fail
- **Grepping the MSI finds nothing.** An MSI is an OLE compound file whose table streams have
  *encoded* names (`䆒䑲㱾䙬䑨䗨…`), so `strings`/regex over the file returns only the Authenticode
  certificate URLs. Extract first, grep the payload.
- **`cabarchive` raises `LZX compression not supported`.** MSI CABs are LZX-compressed, and
  `cabarchive` only handles MSZIP/store.
- **`msilib` may be absent** from a custom Python build (`ModuleNotFoundError: No module named
  'msilib'`).
- **`7z.exe` / `cabextract` / `msiextract` are often not installed.**

## Fix 1 — extract the payload: `msiexec /a` (administrative install)

Plain `msiexec /a … /qn TARGETDIR=…` from git-bash silently succeeds and extracts **nothing**
(it prints the banner and exits 0). It needs elevation:

```bash
mkdir -p msi_extract
powershell -NoProfile -Command "
Start-Process msiexec -ArgumentList '/a','\"D:\path\Hivenet.msi\"','/qn','/norestart',
  'TARGETDIR=\"D:\path\msi_extract\"' -Wait -Verb runAs
'msiexec done'
"
find msi_extract -maxdepth 3 | head -25
du -sh msi_extract
```

`-Verb runAs` triggers the UAC prompt; the run then populates
`msi_extract/LocalApp/<Product>/` (per-user MSIs use the WiX `LocalAppFolder`).

## Fix 2 — read the MSI tables read-only via the Windows Installer COM object

This gives you `Registry`, `CustomAction`, `Property`, `ServiceInstall` **without installing
anything**. Two traps:

1. **`New-Object -ComObject` + `.OpenDatabase()` + `$db.OpenView()` works directly** — do not
   wrap it in `GetType().InvokeMember(...)`, which produces
   `Missing expression after ','` parser errors from the quoting.
2. **Write the script to a file with a quoted heredoc** (`cat > x.ps1 <<'PSEOF'`) — inline
   `powershell -Command "…"` with nested double quotes gets mangled.

```powershell
$wi = New-Object -ComObject WindowsInstaller.Installer
$db = $wi.OpenDatabase("D:\path\Hivenet.msi", 0)   # 0 = read-only
foreach ($t in @("Registry","CustomAction","ServiceInstall","Property","IniFile")) {
  $v = $db.OpenView("SELECT * FROM $t")
  $v.Execute()
  $n = 0
  while ($true) {
    $r = $v.Fetch()
    if ($null -eq $r) { break }
    $n++
    if ($n -le 14) {
      $vals = @()
      for ($i=1; $i -le 9; $i++) {
        try { $x = $r.StringData($i); if ($x) { $vals += $x } } catch {}
      }
      $line = ($vals -join " | ")
      if ($line.Length -gt 210) { $line = $line.Substring(0,210) }
      "  [$t] $line"
    }
  }
  "== $t : $n rows"
}
```

Note: a table that does not exist throws a COMException on `OpenView` — wrap per-table or
accept the noise.

## What to look for in the tables
- **`Registry`** — URL protocol registration
  (`Software\Classes\hivenetdev` + `URL:hivenetdev Protocol` +
  `shell\open\command` = `"[INSTALLFOLDER]Hivenet.exe" "%1"`), shell namespace extensions
  (`Software\Classes\CLSID\{…}` + `Explorer\…\NameSpace\{…}`), and per-machine vs per-user hive.
- **`CustomAction`** — anything running `powershell.exe -ExecutionPolicy Bypass -File …`
  (read those scripts in full), silent bootstrapper installs, and a `LaunchApplication` action.
- **`Property`** — `MSIINSTALLPERUSER` (1 = per-user install ⇒ the install dir and any config
  file in it are user-writable), `ProductVersion`, `UpgradeCode`.

## Signature check

```powershell
$s = Get-AuthenticodeSignature 'D:\path\Hivenet.msi'
$s.Status            # Valid / NotSigned / HashMismatch
$s.SignerCertificate # Subject, Issuer, NotAfter, Thumbprint
$s.TimeStamperCertificate
```

An EV cert + a trusted timestamp + `Status: Valid` is a control that **holds** — record it as
such rather than hunting further.

## After extraction
`find <dir> -maxdepth 1 -type f` then, for each binary, run the strings sweep in
`desktop-app-binary-analysis` SKILL.md step 5–7. Tauri apps show `wry`/`WebView2` markers and
no `electron`; .NET apps expose `DotNetRuntimeDebugHeader` and `PublicKeyToken=` strings.
