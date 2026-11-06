# PoC Techniques Index — Reproduction Recipe (2026-09-26)

Session lesson: executing PoC repos by NAME used ~1% of the 2,223-repo library
(70% are CVE-specific). Fix = extract attack TECHNIQUES from ALL repos and
fire them at any target. This file is the build + fire recipe.

## Build the index (once, ~8 min for 2223 repos)

```bash
PY="C:/Users/WINDOWS10/AppData/Local/Programs/Python/Python314/python.exe"
$PY C:/Users/WINDOWS10/AppData/Local/hermes/scripts/poc-techniques-index.py --limit 2223
```

Output: `~/AppData/Local/hermes/poc-plans/poc-techniques-index.json`

Measured result (2026-09-26):
```
Scanning 2223 PoC repos...
[ scanned 400,  techniques 703]
[ scanned 800,  techniques 1926]
[ scanned 1200, techniques 3248]
[ scanned 1600, techniques 4928]
[ scanned 2000, techniques 6133]
✅ 3014 teknik unik dari 2223 repos
   by type: {generic:2764, lfi:78, admin-config:59, curl-template:42,
             cmdi:33, upload:19, sqli:18, xss:1}
```

Wait — the raw count hits 6133 but dedupe by (type, endpoint|curl) reduces
to 3014 unique. Raw total is fine to log; the unique number is the real
coverage number to report.

## Extraction logic (poc-techniques-index.py)

Per repo (cap 120 files/repo, 30KB/file, skip .git):
1. URL/endpoint regex → find first path with params → classify:
   `sqli` (select/union/' or /sleep/benchmark),
   `xss` (<script/alert(/onerror=),
   `xxe` (<?xml/<!doctype/<!entity/file:///),
   `lfi` (../ /%2e%2e//etc/passwd/file:),
   `ssrf` (169.254.169.254/burp.collaborator/interact.sh),
   `ssti` ({{ / ${ / 7*7),
   `cmdi` (`;` / `|` / `&` / ping -c / cat /etc),
   `auth` (token=/jwt=/authorization:),
   `upload` (upload/file=.php/.php%00),
   `admin-config` (configure/setting/admin/debug/actuator),
   else `generic`.
2. curl command regex → save as curl-template with `-X METHOD` + `-H header`
   extracted for the fire phase.

## Fire techniques at target (execute-poc-techniques.py)

```bash
$PY execute-poc-techniques.py http://TARGET --target-dir <OUT> --max 150
```

Rules per technique:
- Endpoint relativization: `https://target.com/admin` → `root + /admin`
  (strip foreign host, never fire `//target.com/admin`).
- Curl template: pull method (`-X POST`) + first header (`-H "K: V"`).
- Real request via `urllib.request` (never shell curl), timeout 120, rate 0.3s.
- Interesting = status NOT in (404,403,401,405) and size>0.

Measured fire (vuln-app): `150 requests, 2 interesting, 150 evidence files (33KB)`.

## Gate CHECK 11 (verify-tool-usage.py)

```
poc-techniques-usage.json must exist + non-empty
evidence files ≥30% of entries (else FAIL)
→ HARD BLOCK if missing after rework
```

## Why this matters (user framing)

User asked: "Ribuan file itu, udh kamu jadikan sumber cara attack exploit blm?"
The honest audit answer was NO (only 21/2223 repos executed). The fix is the
technique-extraction pattern above — it turns the whole library into usable
attack surface without needing identical product versions.