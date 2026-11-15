# ISP DNS sinkhole → silent scanner failure (and a fabricated XSS set)

Worked case: `toshi.bet` (crypto casino, Next.js front end + Express API microservices),
2026-10-18, Windows 10 / git-bash, MyRepublic Indonesia (AS63859) egress.

This is the layer-1 shape from §3d of the SKILL.md, but with the **persistent fix** and the
**audit-the-evidence** consequence spelled out. The expensive part was not the block — it was
that a full 0C phase produced output that looked like a clean negative.

## 1. Diagnose in one command

```bash
nslookup <target> 2>/dev/null | tail -8
```

```
Server:  gpon.net
Address: fe80::1
Name:    block.myrepublic.co.id
Address: 158.140.186.3
Aliases: toshi.bet          # <-- sinkhole
```

Corroborate with DoH (the real records) and an IP-owner lookup:

```bash
python - <<'EOF'
import urllib.request, json, ssl
ctx = ssl.create_default_context()
req = urllib.request.Request('https://1.1.1.1/dns-query?name=<target>&type=A',
                             headers={'Accept': 'application/dns-json'})
print([a['data'] for a in json.load(urllib.request.urlopen(req, timeout=15, context=ctx)).get('Answer', [])])
EOF
curl -s https://ipinfo.io/158.140.186.3/json      # org: AS63859 PT. Eka Mas Republik
```

If DoH returns real Cloudflare/CDN IPs while the local resolver returns `block.<isp>.*`, you have
a layer-1 sinkhole and nothing else. (Layer-2 TCP interception is ruled out by the §3d foreign-SNI
cert test.)

## 2. The persistent fix — elevated hosts patch

Per-request workarounds (`curl --resolve`, browser `--host-resolver-rules`) fix only the client
you type them on. Every Go/Rust scanner reads system DNS, so patch `hosts` once:

```powershell
# patch_hosts.ps1 — MUST be elevated
$hosts = "$env:SystemRoot\System32\drivers\etc\hosts"
$backup = "$env:TEMP\hosts.backup.$(Get-Date -Format yyyyMMdd_HHmmss)"
Copy-Item $hosts $backup -Force
$marker = "# TEMP: <target> audit - ISP DNS sinkhole bypass"
if (-not (Select-String -Path $hosts -Pattern $marker -Quiet)) {
    $lines = @"
$marker
104.26.1.49 <target>
104.26.1.49 www.<target>
104.26.1.49 api.<target>
104.26.1.49 user.<target>
104.26.1.49 wallet.<target>
172.64.147.209 docs.<target>
"@
    Add-Content -Path $hosts -Value $lines -Encoding ASCII
}
```

Launch it without an interactive UAC prompt blocking the turn:

```bash
powershell -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\...\Temp\patch_hosts.ps1'"
```

Notes:
- **Backup first, always.** The script above does it on every run.
- **Idempotent by marker** — safe to re-run when the CDN rotates IPs.
- **`Add-Content -Encoding ASCII`** avoids a UTF-16 BOM that makes `hosts` unreadable to the
  resolver.
- Direct `>> /c/Windows/System32/drivers/etc/hosts` from git-bash fails with `Permission denied`
  even when the shell looks privileged — use the elevated PowerShell path.

## 3. Verify with TCP, not with a name lookup

`nslookup` keeps printing the sinkhole after the patch (resolver cache). The proof is a connect:

```bash
curl -s -o /dev/null -w "code=%{http_code} time=%{time_total}s\n" --max-time 20 \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36" \
  "https://<target>/"
# 403 in 0.21s = hosts entry is live and the edge is answering.
# 000 / 20s timeout = still sinkholed.
```

## 4. Audit the evidence BEFORE believing any phase result

This is the part that matters. Every tool that read system DNS during the sinkhole window
produced rc=0 with failure-shaped output. Grep the evidence directory:

```python
import glob, re, os
FAIL = ['context deadline exceeded', 'no such host', 'connection timed out',
        'Client.Timeout', 'i/o timeout', 'dial tcp', 'cannot fetch',
        'ERR_CONNECTION', 'not running', 'Unable to connect to host',
        'Could not open a connection to host']
for f in sorted(glob.glob('tool-evidence/*.txt')):
    t = open(f, encoding='utf-8', errors='replace').read()
    if any(m.lower() in t.lower() for m in FAIL):
        print(f"{f}: SILENT FAIL -> NO RESULT, must re-run")
```

Observed on this target (first pass, all rc=0, all worthless):

| Tool | Output shape | Truth |
|---|---|---|
| dalfox ×3 (reflected/dom/stored) | `[E] not running Get "https://toshi.bet": context deadline exceeded` | no scan ran |
| sslscan | `ERROR: Could not open a connection to host toshi.bet (158.140.186.3)` | no scan ran |
| smuggler | `[+] Error : Unable to connect to host` | no scan ran |
| subjack | empty stdout | no scan ran |
| nuclei | 1 match, `dns-waf-detect` | the only thing it could see was the sinkhole IP |

After the hosts patch, the same tools produced real results: sslscan connected and reported
**TLSv1.0 + TLSv1.1 enabled**; smuggler completed every TECL/CLTE variant (all 403/501/400);
subjack returned a real verdict; nuclei ran 11,143 templates to 64%+ with 2 info matches.

**Ledger wording:** record the first pass as `BLOCKED-dns-sinkhole` (host, window, the raw
timeout line) and the retry as the actual result. Never let the failed run be quoted as a
negative — "dalfox found nothing" here would have been a fabricated coverage claim.

## 5. The sinkhole also FABRICATES findings — challenge-page reflection

The nastiest artefact: with the hosts patch in place but the Cloudflare challenge still
unsolved, dalfox reported reflected parameters on ten names:

```
[I] Reflected lang param => PTYPE: URL  Injected: /inJS-double(3)
    1 line:  ed',cUPMDTk:"/?lang=DalFox&__cf_chl_tk=...
[I] Reflected username param ...
[I] Reflected callback param ...
```

Every hit was inside the **Cloudflare challenge interstitial's own JavaScript**, which echoes the
current URL into `cUPMDTk` / `cOgUHash` and calls `history.replaceState`. The pipeline's
`interesting-responses.json` flagged all three dalfox runs as `interesting: true`.

One check kills it (Marker Discipline + grep):

```bash
MARK=zq7vk3mx9p
curl -s -A "<browser UA>" "https://<target>/?lang=$MARK" -o m.html
grep -c "$MARK" m.html                       # 1  -> present
grep -o "Just a moment\|challenge-platform\|cf_chl_opt\|_cf_chl" m.html | sort -u   # challenge page
grep -o ".\{80\}$MARK.\{80\}" m.html | head -3
# -> cUPMDTk:"/?lang=zq7vk3mx9p&__cf_chl_tk=..."   = the wall, not the app
```

Rule: **a marker that only ever appears adjacent to `__cf_chl_tk` / `cUPMDTk` / `cOgUHash` is
the challenge page reflecting its own URL.** Verified negative, not a finding. This is the
Redirect-Drop Rule's sibling — the sink is the interstitial, so the payload never reached the
application.

## 6. Transferable checklist

1. `nslookup` the target **before** the first automated request; a `block.<isp>.*` alias means
   stop and patch.
2. Patch `hosts` elevated, with a marker and a backup.
3. Verify with a TCP/curl connect, never with a name lookup.
4. Grep every evidence file for timeout markers before reading any phase result.
5. Re-run every failed tool; record the failed pass as `BLOCKED-dns-sinkhole`.
6. For any reflection/XSS hit, confirm the marker is not inside the challenge page's JS.
7. Go GENTLE on API subdomains afterwards — the 429 JSON rate-limit signal is separate and
   arrives fast (see `references/cloudflare-challenge-and-local-dns-failure.md`).
