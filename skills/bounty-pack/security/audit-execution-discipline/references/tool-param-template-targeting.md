# Tool Parameter & Template Targeting (sqlmap / nuclei)

How to make sqlmap and nuclei test the *right* surface of a target, instead of the bare root URL.

## sqlmap — it has no templates; it needs a PARAMETER (+ cookie)

`sqlmap -u https://target/` → `no parameter(s) found` = tested nothing.
The real surface is `https://target/path?p=v` **plus** the auth cookie.

Priority for finding the parameterized URL:
1. **target already has `?p=v`** → use it.
2. **recon `urls.txt`** (orchestrator 0B) — grep for `?`, keep only the audit host.
3. **`openapi.json` / `swagger.json`** in output dir → every endpoint + query param listed.
4. `katana -u https://target -jc -kf -dep 2` → crawl, extract `?` params from live JS/API.
5. `arjun` (hidden/backup params): `arjun.exe -u https://target/ -t 4 -d 1` — **pip tool, NOT Go**: `pip install arjun` → `Scripts/arjun.exe` (v2.2.7). `go install github.com/s0md3v/Arjun` fails ("does not contain package" — it's a Python project). Pipeline class is `[arjun, sqlmap]`: arjun fires first and its evidence file feeds `_param_url()`.

Always attach auth:
```
--cookie "session=..."        # or
--cookie-from-raw req.txt     # burp raw request
--level=2 --risk=1 --threads=4 --timeout=15 --retries=1 --smart --batch --disable-coloring
```
If a param returns "not injectable", re-test ONCE against a real param URL + cookie before recording NEGATIVE — otherwise you tested nothing.

The pipeline already does steps 1–3 automatically: `_param_url()` in `force-full-execution.py`
picks target → urls.txt → openapi.json (same-host filter) and marks `SKIP_NO_PARAM` when none exists.

## nuclei — templates ARE the payload; target it with the right tag + local mirror

Local template mirror (fast, offline, no GitHub clone):
- `D:\data hermes\nuclei-templates`  (13,754 yaml — mirror of projectdiscovery/nuclei-templates)
- fallback `D:\data hermes\cve-unified\nuclei`

Invocation (pipeline default):
```
nuclei -u "<target>" -silent -timeout 10 -t "D:/data hermes/nuclei-templates/http" -tags tech,exposure,misconfiguration
```
**Pitfall:** `-template-dir` does NOT exist (`flag provided but not defined`). Use `-t` with a template *directory*. Pick tags by vuln class (sqli/lfi/xxe/...) or use `-tc`/`-tags` combos. `-t` with a single file runs just that template.

Source repo (when a template is missing/stale): `github.com/projectdiscovery/nuclei-templates`.

## Custom template for a specific target surface (the "template yang sesuai target")

When the stock templates don't hit your endpoint (auth + specific param), write a 1-off YAML from a real request:

```yaml
id: target-specific-probe
info:
  name: Probe <endpoint> with <param>
  severity: info
  tags: [probe]
http:
  - raw:
      - |
        POST /path/endpoint HTTP/1.1
        Host: target
        Cookie: session=REPLACE
        Content-Type: application/json

      - |
        {"param":"{{payload}}"}
    cookies:
      session: REPLACE
    attack: csv
    payload:
      file: D:/data hermes/nuclei-templates/http/techniques/...  # or inline
    matchers:
      - type: status
        status: [200]
```
Run: `nuclei -t my-template.yaml -u target -o out.txt`. Build a small set of these per target once the surface is understood (auth model + money/data endpoints). This is the "target-specific template" — far more signal than `-tags` on the root URL.

## Install notes (2026-09-29, verified on this box)

| tool | install | result path |
|---|---|---|
| arjun | `python -m pip install arjun` (NOT `go install` — no Go package exists) | `/usr/local/bin/arjun.exe` |
| kxss | `go install github.com/Emoe/kxss@latest` | `/home/agentuser/go/bin/kxss.exe` (reads URL from stdin) |

**MSYS/go env pitfall:** under git-bash, `go env` fails with `GOPATH entry is relative; must be absolute path: "/home/agentuser/go"`. Per-command fix:
```bash
export MSYS_NO_PATHCONV=1
export GOPATH="/home/agentuser/go" GOBIN="/home/agentuser/go/bin"
go install <pkg>@latest
```

## Verifying the scan actually ran (not just launched)

A tool that prints a usage/help banner = did NOT scan. Positive signatures:
- sqlmap: `sqlmap identified the following injection point` or a param-tested line + session.sqlite written.
- nuclei: `[tag:template] [http] [level]` result lines, not just template-load noise.
- ffuf: `Fuzz Faster U Fool` banner + `=> NAME` result lines (JSON via `-of json`).
- dalfox: `Found N testing point(s)`.

> **Full failure-signature table + evidence-body read:** `tool-execution-verification.md`
