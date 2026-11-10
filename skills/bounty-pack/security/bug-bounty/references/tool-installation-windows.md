# Reference: Windows Tool Installation Guide (2026-09-03)

> Complete audit + install workflow for bug bounty security tools on Windows (MSYS/git-bash).
> Covers 30+ tools across Go, Python, npm, cargo, and native categories.

---

## Install Workflow

### Step 1: Audit — Check What's Installed
```bash
export PATH="/c/go/bin:$HOME/go/bin:$PATH"
echo "--- Go Tools ---"
for tool in subfinder nuclei katana ffuf gobuster gau medusa trufflehog; do
  command -v $tool &>/dev/null && echo "✅ $tool" || echo "❌ $tool"
done
echo "--- Python Tools ---"
for tool in sqlmap halmos; do
  command -v $tool &>/dev/null && echo "✅ $tool" || echo "❌ $tool"
done
echo "--- System ---"
for tool in jq node npm curl git; do
  command -v $tool &>/dev/null && echo "✅ $tool" || echo "❌ $tool"
done
echo "--- Solidity ---"
command -v forge &>/dev/null && echo "✅ forge" || echo "❌ forge"
command -v hardhat &>/dev/null && echo "✅ hardhat" || echo "❌ hardhat (check npm)"
```

### Step 2: Install Missing Tools (priority order)

#### Phase A: Go Runtime (prerequisite for Go tools)
```bash
curl -L -o /d/data\ hermes/go.zip "https://go.dev/dl/go1.24.6.windows-amd64.zip"
powershell -Command "Expand-Archive -Path 'D:\data hermes\go.zip' -DestinationPath 'C:\' -Force"
echo 'export PATH="/c/go/bin:$HOME/go/bin:$PATH"' >> ~/.bashrc
echo 'export GOPATH="$HOME/go"' >> ~/.bashrc
```

#### Phase B: Go Tools (ProjectDiscovery + others)
```bash
export PATH="/c/go/bin:$HOME/go/bin:$PATH" && export GOPATH="$HOME/go"
# TIMEOUT: set 300s+ — Go compilation on Windows is SLOW (5-10 min per tool)
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/katana/cmd/katana@latest
go install github.com/projectdiscovery/gau/v2/cmd/gau@latest
go install github.com/projectdiscovery/medusa/cmd/medusa@latest
go install github.com/OJ/gobuster/v3@latest
```

**nuclei (special case):** `go install` often times out. Use pre-built binary via PowerShell (handles GitHub redirects):
```bash
powershell -Command "
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
\$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/projectdiscovery/nuclei/releases/latest'
\$asset = \$release.assets | Where-Object { \$_.name -match 'windows_amd64.zip' } | Select-Object -First 1
Invoke-WebRequest -Uri \$asset.browser_download_url -OutFile 'D:\data hermes\nuclei.zip'
"
unzip /d/data\ hermes/nuclei.zip -d /c/go/bin/ && rm /d/data\ hermes/nuclei.zip
```

**trufflehog (tar.gz, not zip):** Same PowerShell approach, then `tar -xzf`.

#### Phase C: Python Tools
```bash
PIP="~/.local/share/Python/bin/pip.exe"
$PIP install sqlmap

# theHarvester: pip package is v0.0.1 (outdated). Must git clone + editable install:
cd "/d/data hermes"
git clone --depth 1 https://github.com/laramies/theHarvester.git
cd theHarvester && $PIP install -e .
# No CLI entry point — create wrapper:
cat > /c/go/bin/theharvester << 'WRAPPER'
#!/bin/bash
cd "/d/data hermes/theHarvester"
~/.local/share/Python/bin/python.exe -m theHarvester "$@"
WRAPPER
chmod +x /c/go/bin/theharvester
```

#### Phase D: Native/Platform-Specific
```bash
# jq — direct exe download
curl -L -o /c/go/bin/jq.exe "https://github.com/jqlang/jq/releases/latest/download/jq-win64.exe"

# nmap — REQUIRES ADMIN: nmap-setup.exe /S (silent, needs elevation)
```

---

## ⛔ Windows Installation Pitfalls

### 1. GitHub Redirect = 9-Byte File
`curl -L` fails on GitHub releases — downloads 9-byte redirect HTML instead of binary.
**Fix:** Use PowerShell `Invoke-WebRequest` via GitHub API for redirect-safe downloads.

### 2. Go Compilation Timeout
`go install` for large projects (nuclei, trufflehog) takes 5-10+ min. Default timeout 180s.
**Fix:** `timeout=300` in terminal call, OR download pre-built binary (preferred).

### 3. No Windows Binaries Available
Some projects don't ship `windows_amd64` (sslscan, some medusa versions).
**Options:** Build from source, use WSL, or find alternative tool.

### 4. Nmap Needs Admin Elevation
`nmap-setup.exe /S` fails without admin. Use `naabu` (Go, no admin) as alternative.

### 5. Python Version Incompatibility
mythril requires Python 3.11-3.12. Python 3.14 breaks it. Skip until compatible.

### 6. Rust/Cargo: default toolchain is GNU and `dlltool` is missing
Symptom: `error calling dlltool 'dlltool.exe': program not found` → build of any crate that
pulls `windows-sys` (reqwest, tokio, most Rust PoC harnesses) fails.
**Fix (preferred — MinGW is usually NOT needed):** the MSVC toolchains are normally already
installed. Just switch to one:
```bash
rustup toolchain list                     # look for *-pc-windows-msvc
cargo +stable-x86_64-pc-windows-msvc run  # one-off
# or pin it for the project so plain `cargo run` works:
printf '[toolchain]\nchannel = "stable-x86_64-pc-windows-msvc"\n' > rust-toolchain.toml
```
Installing MinGW-w64 is the fallback only if no MSVC toolchain exists. Note the MSVC linker
(`link.exe`) must come from VS Build Tools — if `/usr/bin/link` shadows it, use the
`Developer Command Prompt` env or `vcvars64.bat`.

### 6b. `aderyn` has NO Windows build at all (don't chase it)
`npm i -g @cyfrin/aderyn` aborts: *"Platform with type Windows_NT and architecture x64 is not
supported"* — upstream ships only aarch64/x86_64 for apple-darwin and unknown-linux-gnu, and
there is no Windows release asset. Building from source needs MinGW. **Use slither instead**
(same static-analysis role; see pitfall 1b in `immunefi-recon-workflow.md` for the solc pinning
that makes slither work). `mythril` is the same story on Windows-era Python — use halmos/echidna.

### 7. TheHarvester Has No CLI Entry Point
`pip install -e .` doesn't create `theharvester` command. Create wrapper script.

### 8. PATH Not Persisted Between Calls
Always prepend PATH at start of multi-step operations.

---

## Tool Inventory (verified 2026-09-03)

| Tool | Category | Install | Status |
|------|----------|---------|--------|
| go v1.24.6 | Runtime | zip | ✅ |
| subfinder | Subdomain | go install | ✅ |
| nuclei | Vuln scan | Pre-built binary | ✅ |
| katana | Crawler | go install | ✅ |
| ffuf | Dir fuzz | go install | ✅ |
| gobuster | Dir fuzz | go install | ✅ |
| gau | URL disc | go install | ✅ |
| medusa | Fuzzer | go install | ✅ |
| trufflehog | Secret scan | Pre-built binary | ✅ |
| jq | JSON | exe download | ✅ |
| sqlmap | SQLi | pip | ✅ |
| theHarvester | OSINT | git+pip+wrapper | ✅ |
| halmos | Formal V | pip | ✅ |
| hardhat | Solidity | npm | ✅ |
| forge | Foundry | foundryup | ✅ |
| slither | Static | pip | ✅ |
| echidna | Fuzzing | manual | ✅ |
| nmap | Port scan | installer(admin) | ❌ |
| whatweb | Finger | Ruby gem | ❌ |
| sslscan | SSL | manual | ❌ |
| aderyn | Static | cargo | ❌ |
| mythril | Symbolic | pip | ❌ |
| graphql-map | GraphQL | manual | ❌ |

## Alternatives When Blocked

| Blocked | Alternative | Notes |
|---------|-------------|-------|
| nmap | naabu (Go) | No admin needed |
| whatweb | httpx -tech-detect | Fingerprinting |
| sslscan | testssl.sh, nuclei ssl | SSL testing |
| aderyn | slither | Overlapping coverage |
| mythril | halmos, echidna | Formal + fuzzing |
| graphql-map | graphw00f | GraphQL analysis |

## .NET product audits (decompiling a shipped .NET app)

Verified 2026-10 on Windows 10 during the Octopus Deploy audit (Octopus Server /
Tentacle are closed-source .NET; the Tentacle source is public).

1. Install the SDK user-local (no admin):
   `powershell -ExecutionPolicy Bypass -File dotnet-install.ps1 -Channel 8.0 -InstallDir $HOME/.dotnet`
   (fetch https://dot.net/v1/dotnet-install.ps1)
   - The bash `dotnet-install.sh` FAILS under git-bash:
     `OS name could not be detected: UName = MINGW64_NT-10.0-19045`. Use the .ps1.
   - `ExtractToFile ... There is not enough space on the disk` then a later run throwing
     `Could not load file or assembly 'System.Threading'` = truncated install. Free space
     on C: first, `rm -rf ~/.dotnet`, reinstall.
2. ilspycmd: the CURRENT package fails with
   `Settings file 'DotnetToolSettings.xml' was not found in the package`.
   Pin a version that ships it and add the runtime it wants:
     `dotnet-install.ps1 -Channel 6.0 -Runtime dotnet -InstallDir $HOME/.dotnet`
     `dotnet tool install -g ilspycmd --version 8.2.0.7535`
   Without DOTNET_ROOT+PATH set, the tool reports `You must install or update .NET`
   or `Failed to resolve hostfxr.dll`.
3. ilspycmd 8.2 dies on some assemblies with
   `System.ArgumentException: Argument must be between 0 and 2. (Parameter 'fieldCount')`
   from DecompilerTypeSystem (a `Version.ToString()` bug on non-standard
   AssemblyFileVersion). Newer ILSpy fixes it; a newer ilspycmd wants .NET 9
   (`dotnet-install.ps1 -Channel 9.0 -Runtime dotnet`).
4. Fast triage without a decompiler - grep the DLLs for class names to attribute a
   behaviour to a shipped assembly:
   `python -c "b=open('Octopus.Core.dll','rb').read(); print(b.count(b'SensitiveValueMasker'))"`
   This is how the server was proven to share the Tentacle's masking classes.
