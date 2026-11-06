# The anti-fraud redirect block — and how to run a gated scanner volley

Two linked lessons from a 2026-10 engagement where the operator overrode a vendor's "no automated
scanning tools" rule. Keep them together: the first is a block shape this skill's tables did not
cover, the second is the discipline that decides whether firing at all is worth it.

---

## 1. The block shape: 302 to a help-centre article, on the whole app estate

Not every block is 403/429/TLS-alert. On this target the signature was a **302 redirect to the
vendor's own anti-fraud help article** — the same URL their bot protection serves to suspicious
traffic:

```
HTTP/1.1 302 Found
Server: nginx
location: https://support.<target>/hc/en-gb/articles/360002125180-Preventing-fraud
```

It arrived at the **edge for every application host at once** while the marketing apex stayed
healthy — which is the diagnostic that matters:

| Host | Before | During | After |
|---|---|---|---|
| `signup.<target>` | 200 | 302 -> Preventing-fraud | 200 |
| `login.<target>` | 200 | 302 -> Preventing-fraud | 200 |
| `<tenant-a>.<target>` (own trial) | 200 | 302 -> Preventing-fraud | 200 |
| `<tenant-b>.<target>` (own trial) | 200 | 302 -> Preventing-fraud | 200 |
| `api.<target>/v2/company` | 400 (normal unauth) | 302 -> Preventing-fraud | 400 |
| `api.sandbox.<target>` | 200/400 | 302 -> Preventing-fraud | 200 |
| `dev.<target>` | 200 | 302 -> Preventing-fraud | 200 |
| `www.<target>` (marketing) | 200 | **200** | 200 |

Read the blast radius before concluding "only the scanned host is affected" — the whole application
estate went dark, including hosts you were still using for manual work:

```bash
for u in https://signup.<t>/signup https://login.<t>/login https://<tenant>.<t>/login \
         https://api.<t>/v2/company https://dev.<t>/ https://www.<t>/ ; do
  printf "%-52s " "$u"
  curl -s -o /dev/null -m 20 -w "%{http_code} -> %{redirect_url}\n" "$u"
done
# and prove the ACCOUNT is untouched (only egress is blocked) — authenticated call with your token:
python - <<'PY'
import json,pathlib,sys; sys.path.insert(0,'.')
import fa_api                      # the engagement's own client
print(fa_api.call("GET","/v2/company")[0])   # 200 => account fine, IP blocked
PY
```

**Onset and recovery, measured:** a single host swept by `nuclei -rl 20` tripped it after **~8
minutes**; the flag **self-cleared in ~15 minutes**; tokens and accounts were unaffected — only
access from that egress. So: a temporary anti-abuse trip, not the permanent IP ban the policy
warned about. Do not promise the operator either outcome in advance; measure and report.

**After the block: do not evade it.** Rotating egress / stacking proxies to get back into a host
that has deliberately redirected you is a different act from testing under authorisation. Wait it
out or ask the vendor, and say which you are doing.

---

## 2. Before firing: validate the toolchain on a LOCAL target

This is the step that separates a real volley from a fake one, and it caught four broken tools in
one pass. Against a throwaway `python -m http.server`-style target on `127.0.0.1`:

```
nuclei   -> [FTL] Could not run nuclei: no templates provided for scan
ffuf     -> CreateFile D:\d\data hermes\wordlists\...\common.txt: The system cannot find the path
gobuster -> wordlist file "/d/data hermes/..." does not exist
sqlmap   -> can't open file 'D:\c\Users\...\Scripts\sqlmap.py': [No such file or directory]
```

**All four returned exit code 0.** Fired unchanged at the real target they would have produced five
empty- or usage-dump evidence files that a report would happily read as "all tools executed" — the
exact fabricated-coverage failure this skill warns about elsewhere. The cause is MSYS path rewriting
of the wordlist/template/launcher arguments; the fix is native paths plus the guard inside the script:

```bash
export MSYS_NO_PATHCONV=1                      # inside the script, not just the calling shell
WL_DIR="D:/data hermes/wordlists/0B-recon"     # native, not /d/data/...
NUCLEI_TPL="D:/data hermes/nuclei-templates"
sqlmap -u "$T/?id=1" ...                       # invoke the launcher, not python + an MSYS path
```

Then re-run and prove each tool **left real output** (a template match, a found path, a parameter
list, a verdict line) before it is counted as coverage. Three tools stayed broken/unvalidated on
that host and were recorded as `BROKEN`, never as coverage: `semgrep` (Python traceback),
`commix` (cannot print even `--help`), `amass` (rejects `-d localhost`; needs a real FQDN).

---

## 3. The gated-volley pattern

When the operator instructs you to run scanners anyway, ship them as one script with hard rails
rather than a sequence of ad-hoc commands:

```bash
#!/usr/bin/env bash
set -u
export MSYS_NO_PATHCONV=1
if [ "${SCANNER_APPROVED:-0}" != "1" ]; then
  echo "REFUSED: SCANNER_APPROVED is not set to 1."; exit 2      # env-var gate, verified to exit 2
fi
IN_SCOPE=( "https://signup.<t>" "https://<tenant>.<t>" "https://dev.<t>" "https://api.<t>" )
allow() { for s in "${IN_SCOPE[@]}"; do [ "$1" = "$s" ] && return 0; done
          echo "SCOPE-GUARD: refusing out-of-scope host: $1" >&2; return 1; }
run() { local n="$1"; shift; timeout 600 "$@" >"$EV/$n.txt" 2>&1; local rc=$?
        grep -qiE "unknown command|unrecognized arguments|Usage:|flag provided but not defined" "$EV/$n.txt" \
          && st=FAILED_USAGE || st=EXECUTED
        printf '{"tool":"%s","status":"%s","rc":%s}\n' "$n" "$st" "$rc" >> "$EV/_usage.jsonl"; }
```

Rules that earned their place:

1. **Write the constraint and the operator's assertion into the engagement log** — who approved
   what, when, and that no written exception was attached. A permission that arrives after an IP
   ban cannot undo it; saying so once, up front, is the whole contribution.
2. **Env-var gate + scope guard + low rate** (`nuclei -rl 20`, `ffuf -rate 25`, `gobuster --delay
   100ms`) — so the script cannot fire by accident and cannot wander off the in-scope list.
3. **Leave a machine-readable artifact** (`tools-usage.json`) so the phase gate has something to read
   afterwards instead of self-reported claims.
4. **Supervise the WHOLE process tree.** Killing the Hermes background job terminated the wrapper,
   but an orphaned `bash fire_scanners.sh` survived and **moved on to the next host on its own** —
   the block was detected while the loop was still scanning. Find and kill the wrapper by PID
   (`Get-CimInstance Win32_Process | Where CommandLine -match 'fire_scanners'`), then confirm zero
   `nuclei`/`qemu`/scanner processes remain, repeatedly — child processes respawn.
5. **Watch for the block signature from minute one** and make the kill decision yourself. Here the
   detection loop (302 -> anti-fraud article on any host) is what stopped it at ~8 minutes instead of
   letting it run to completion.

**Outcome to record honestly:** that volley produced **zero findings** (one `waf-detect:nginxgeneric`
info line across 5 empty evidence files) and earned a temporary estate-wide IP flag. Cost exceeded
benefit; the recommendation written into the log was: do not repeat without a written exception
*plus* a vendor-side allow-list, because the toolchain being "ready" is not the same as the run being
worth anything.
