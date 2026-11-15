# Vendor scanner prohibition → the guarded-volley pattern

Companion to the `⛔ VENDOR SCANNER PROHIBITION` section in SKILL.md. Written from the FreeAgent
engagement (2026-10-02) where firing scanners got the operator's IP flagged and produced zero findings.

## When this applies

The target's policy (security.txt → disclosure page) contains any of:
- "no automated vulnerability/scanning tools" / "no scanners" / threat of an IP block
- "no mass brute force" / "no account enumeration" / "no DDoS"
- an out-of-scope list that includes IP/port scanning
…while the audit pipeline (0C C1–C6b, 0D gate) is written around scanner evidence.

## The pattern

### 1. Build the volley, don't fire it

`<target>/tools/fire_scanners_<target>.sh`

- **Hard guard** first thing: `[ "${FA_SCANNER_APPROVED:-0}" != "1" ] && exit 2` — verify it actually
  refuses (`bash script.sh; echo $?` → 2) before you ever mention it.
- **Scope guard**: an `IN_SCOPE=(...)` allow-list and an `allow()` that returns non-zero for anything
  else; every `run` is wrapped by it. Out-of-scope host = refused, logged.
- **Rate limits** even with approval: `nuclei -rl 20`, `ffuf -rate 25`, `gobuster --delay 100ms`.
- **Gate artefact**: append one JSON line per tool to `tool-evidence/_usage.jsonl` and assemble
  `tool-evidence/tools-usage.json` so the 0D gate has something truthful to read. Record honest
  statuses (`EXECUTED` / `NO_OUTPUT` / `FAILED_USAGE`) — never "EXECUTED" for a usage dump.
- **No live credentials on disk**: leave the authenticated API leg out of the script (do it manually
  with the token in memory). Writing `auth/token.json` into a shell script also risks the
  secret-tripwire corrupting the file (it rewrites token-looking content to `***`, which silently
  breaks the script — verify with `grep -c '\*\*\*'` and `bash -n` after every write).

### 2. Validate the whole toolchain on a LOCAL target first

Spin up `templates/local-vuln-target.py` from this skill (`bb-audit-launcher/templates/local-vuln-target.py`) (a tiny vulnerable fixture: `/`, `/search?q=` reflected,
`/admin` 403, `/login`, `/api/v1/users?id=`, `/backup.zip`) and run every tool against
`http://127.0.0.1:<port>`. Success criterion per tool: **a real result line**, e.g.
`nuclei` → a matched template; `ffuf`/`gobuster` → discovered paths; `sqlmap` → it names the
parameter and gives a verdict ("not injectable"); `arjun` → extracted parameters.

This is not ceremony — it is where the silent failures show up (see
`audit-execution-discipline/references/msys-path-and-tool-invocation-traps.md`). In this engagement
the first pass had `nuclei`, `ffuf`, `gobuster` and `sqlmap` all failing **while returning rc=0**:
MSYS had rewritten the wordlist/template paths to `D:\d\data hermes\…`. Fired as-is, the volley would
have produced empty evidence that a careless report would have called "all tools executed".

### 3. Record the coverage claim from disk

Missing artefact = phase did not run. State it in the report as its own section, listing what ran,
what did not, and why. Never let "the surfaces I reached were tested manually" imply "all tools ran".

## Block signature — define it BEFORE firing

FreeAgent (2026-10): any app-estate host answering
`302 -> https://support.freeagent.com/hc/en-gb/articles/360002125180-Preventing-fraud`
means the operator IP is flagged. Observed on **all** of: signup, login, `<tenant>.freeagent.com`,
api, api.sandbox, dev — while `www.freeagent.com` (marketing) stayed 200.

Find the target's equivalent before firing: grep the policy/abuse pages, or note the redirect that a
single stray suspicious request produces. Then poll it during the run.

## Kill-switch (Windows / MSYS)

1. `taskkill /F /IM nuclei.exe` (repeat if the wrapper loops).
2. The volley's own bash wrapper **can be orphaned** — killing the tracked session is not enough.
   Find it by command line and kill the tree:
   `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'fire_scanners|nuclei\.exe' }
    | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }`
3. Verify clean with the same CIM query (a `grep`-style command line matches itself — check the
   `Name` column for actual scanner binaries, not shells).

## Recovery — do not evade

- Do **not** retry scanners and do **not** route around the block with proxies/VPNs. Circumventing an
  access control that has already engaged is a materially different (worse) position than breaching a
  program rule.
- The accounts usually still exist; only the route is blocked. Say so explicitly — it stops the
  operator from thinking data was lost.
- Send one message on the vendor's disclosure channel covering both: (a) the block on this IP,
  (b) the written exception + IP allow-listing needed to resume. Those are the same conversation.

## Honest post-mortem line to leave in the engagement log

> Firing forward after a verbal-only exception: ~8 minutes of `nuclei`, one `waf-detect` info line,
> IP flagged, engagement access lost. Zero findings. The guarded build + local validation + block
> monitoring is what limited the damage to that.
