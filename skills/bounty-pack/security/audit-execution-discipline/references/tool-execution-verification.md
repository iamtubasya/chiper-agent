# Tool-Execution Verification — "EXECUTED" is not "RAN"

Companion to **RULE 2c**. Source: quarterwise.co.uk audit, 2026-09-28, where the user
asked *"Sdh all tools dpakai? Dan all varian attack?"* and the honest answer turned out to
be **no** — nine tools carried `status: EXECUTED` in `tools-usage.json` while having
scanned nothing.

---

## 1. Why the gate passes liars

`verify-tool-usage.py` CHECK 2/3 only asserts an evidence file exists and is `≥100B`.
A tool that dies on argument parsing writes its **usage banner + error** to that file —
comfortably >100B — and the gate is satisfied. So:

```
>100B evidence file  ==  a process ran
>100B evidence file  !=  a test happened
```

The only trustworthy read is the **body**.

## 2. The one command that tells the truth

```bash
for f in <out-dir>/tool-evidence/*.txt; do
  echo "=== $(basename "$f")"
  tail -c 400 "$f" | tr -d '\r'
  echo
done
```

Also confirm the tool's own verdict line is present (e.g. sqlmap
`does not seem to be injectable`, nuclei `Scan completed in ... N matches found`,
dalfox `Found N testing point`).

## 3. Failure signatures observed (treat any of these as NOT-RUN)

| Body contains | Meaning | Correct invocation |
|---|---|---|
| `unknown command "https://…"` | wrong CLI verb (dalfox) | `dalfox url <url>` or `dalfox file list.txt` |
| `unrecognized arguments: --headless` | flag doesn't exist (CORScanner, ffuf) | drop the flag entirely |
| `the following arguments are required: -r, -p` | needs a raw request file + param | `SSRFmap -r req.txt -p <param>` |
| `no parameter(s) found for testing in the provided data` | sqlmap hit a param-less URL | supply `-u '<url>?p=v'` or `--crawl` |
| `Could not find template '…'` | template path wrong | `-t <dir>` (no trailing slash) or `-t cves/` |
| `Usage:` / bare help banner | argparse rejected everything | fix flags first |
| a hostname that is **not the audit target** | target was scraped from page content | sanitise URLs to the target's registrable domain |

**Extra failure mode — plausible-but-meaningless success:** `race-checker.py -u
https://target/` returned `Successful requests: 4/50 … no obvious race conditions` — against
a *static marketing root page* with no state to race. A green verdict on the wrong endpoint
is worse than an error, because it looks like coverage. Race tools need a **state-changing
endpoint** (POST that mutates a row), not a GET on a page.

## 4. Target-scope leak (must be policed)

The recon `urls.txt` for this audit picked up a `https://www.tax.service.gov.uk/...` link
from page copy. `force-full-execution.py` then fired per-class `nuclei` scans at it
(`auth-bypass`, `nosqli`, …). That is an unintended third-party scan.

**Rule:** before any tool fans out over recon URLs, filter to the audit target's
registrable domain. Add a guard in the recon→variants handoff:

```python
import tldextract, sys
base = tldextract.extract(TARGET).registered_domain          # e.g. "quarterwise.co.uk"
urls = [u for u in urls if tldextract.extract(u).registered_domain == base]
```

At minimum, grep `urls.txt` for foreign domains and report any that leaked.

## 5. Reporting shape the user expects

When asked "all tools used / all variants tested", answer with a table whose verdicts come
from the evidence **body**, never from `tools-usage.json`:

| Tool | Status | Evidence | Verdict |
|---|---|---|---|
| nuclei (all tmpl) | ✅ RAN | 7035 templates, 10921 req, 0 matches | clean |
| sqlmap | ✅ RAN | full technique set → `sourceType does not seem to be injectable` | clean |
| dalfox | ⚠️ re-fired | pipeline CLI was wrong; re-run via `dalfox file` | covered |
| commix | ❌ NOT-RUN | wrapper shim broken on this host | N/A |
| kxss / gif / … | ❌ NOT-INSTALLED | — | gap |

…followed by an explicit **gaps** section. Never “yes, all done” from the usage JSON alone.

## 6. Don't turn this into a permanent constraint

Missing binaries / broken wrappers are **environment state**, not durable rules. Record
them as a *gap in this run*, and if the user wants them, the fix is an install command —
never a skill line saying “tool X doesn't work”. The durable lesson is only:
**read the evidence body before claiming coverage.**
