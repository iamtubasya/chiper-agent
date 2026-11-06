# nuclei: correct invocation, stall diagnosis, and request-budget arithmetic

Session-derived (Deutsche Telekom estate, 2026-10-29). Six consecutive failed launches, all
self-inflicted. The target was never the problem — the tool completed in **2 seconds** once the
arguments were right.

## 1. The arithmetic you must do BEFORE launching

`templates × hosts = requests`. At a given `-rl`, `requests ÷ rl = seconds`. Do this on paper first;
a plausible-looking flag set can queue many hours of traffic.

Measured template-directory sizes on a standard install (11,718 HTTP templates total):

| dir | templates |
|---|---|
| `http/exposures/configs/` | 219 |
| `http/exposures/tokens/` | 218 |
| `http/takeovers/` | 73 |
| `http/misconfiguration/` | 986 |
| `http/exposed-panels/` | 1,582 |

The trap, live: five dirs selected (`configs` + `tokens` + `takeovers` + `misconfiguration` +
`exposed-panels`) = **3,078 templates** × 600 URLs = **1.85M requests**. At `-rl 80` that is
**~8.5 hours**. It ran 45 s and had written 0 bytes — correctly, it was nowhere near done.

**Rule: if `requests ÷ rate > ~1 h`, you have chosen the wrong template set, not a slow scan.**
Cut to one or two dirs, or cut the host list.

Priority order that actually pays (highest signal per request):

```bash
# 1. takeovers — small (73), high-value, completes in seconds
nuclei -l urls.txt -nc -silent -jsonl -rl 50 -c 15 -timeout 8 -retries 1 \
       -t ~/nuclei-templates/http/takeovers/ -o tk.jsonl

# 2. tokens + configs (437) — secrets and stray config exposure
nuclei -l urls.txt -nc -silent -jsonl -rl 80 -c 25 -timeout 8 -retries 1 \
       -t ~/nuclei-templates/http/exposures/tokens/ \
       -t ~/nuclei-templates/http/exposures/configs/ -o tok.jsonl

# 3. everything else — only against a CURATED host list, never the full one
```

Skip `exposed-panels` and `misconfiguration` on a wide URL list entirely. They are 2,568 of the
3,078 templates and produce mostly SPA-catch-all noise on a modern estate.

## 2. Stall vs. slow vs. dead — how to tell them apart

| symptom | cause | action |
|---|---|---|
| `flag provided but not defined: X` + `EXIT=2`, no `-o` file | argv error | read the message; check the flag exists |
| no output, live PID, 0 bytes, >3 min, `-tags`/`-severity` in use | corpus-compile stall | kill; re-issue with explicit `-t <dir>` |
| no output, live PID, output file growing | slow but working | wait, or check `-stats` for `Requests: N/M` |
| output file 0 bytes, process gone, stderr empty | finished with 0 findings, OR argv error | re-run once with `-stats` to distinguish |
| `EXIT=124` | shell `timeout` killed it | partial coverage, not a negative |

## 3. Prove execution with `-stats` (the only honest negative)

```bash
nuclei -u https://host -t ~/nuclei-templates/http/takeovers/ -nc -stats -stats-interval 5
```

Expected healthy shape:

```
[INF] Templates loaded for current scan: 73
[INF] Templates clustered: 68 (Reduced 132 Requests)
[0:00:02] | Templates: 73 | Hosts: 2 | RPS: 9 | Matched: 0 | Errors: 0 | Requests: 20/20 (100%)
```

Read it as: 73 templates genuinely loaded, clustering applied, request budget fully consumed, zero
errors, zero matches. That is a **verified negative** — write it into the ledger with the command.
`Requests: 20/20 (100%)` is the line that separates "clean" from "never ran".

## 4. Flags that do not exist (and the tool they belong to)

| flag | belongs to | nuclei behaviour |
|---|---|---|
| `-maxtime` | **ffuf** | `flag provided but not defined`, EXIT=2, no output file |
| `-retry` | nothing | the nuclei flag is `-retries` (plural) |
| `-t <listfile>` | nothing | `-l` is targets, `-t` is templates; see the `-l`≠`-t` trap in SKILL.md |

Bound runtime portably with the shell instead of a tool flag:

```bash
timeout 1500 nuclei -l urls.txt -nc -silent -jsonl -rl 60 -c 20 \
        -timeout 8 -retries 1 -t <dir> -o out.jsonl
```

## 5. Operational notes

- **`-nc` is mandatory** when anything downstream parses the output. `dnsx -resp` has the same
  problem (ANSI codes around `[CNAME]` made a regex parse return 0 rows while `wc -l` said 730).
- **Process counting via `ps -ef | grep -c nuclei` overcounts.** Each launch spawns a wrapper; six
  attempts left `grep -c` reporting 5–13 for a single logical run. Kill by name and confirm the output
  file's mtime stops moving rather than trusting a process count.
- **`pkill` is not guaranteed present** in every MSYS shell — it returned `command not found` here.
  Fall back to `tasklist | grep nuclei` / `kill <pid>`.
- **Write to a fresh output filename per attempt.** A stale 0-byte file from attempt 1 is
  indistinguishable from a genuine empty result from attempt 6.
