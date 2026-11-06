# The "failure that pretends to be a result" family — INDEX

This file is a **map, not a manual.** The specific failures below each have their own reference; this
one exists so a future session recognises them as **one family** and reaches for the right sibling.

Source: 2026-10-10, one long session on a single target that surfaced **eight** instances of a single
class:

> **nothing crashes. A number, a status, or a document looks produced, and it is wrong.**

These cost more than exceptions because they survive review, survive the gates, and reach the operator
as a confident false statement. Every hard failure in that session was this shape — there was no
outright crash to chase.

## Why they hide

| mechanism | why the pipeline cannot see it |
|---|---|
| broad `try/except Exception` | the defect becomes a *status field*, plausibly labelled `RAN_WITH_ERROR` — reads as *the tool* failed, not *my code* failed |
| `ast.parse` green | syntax ≠ importability ≠ callability (a `NameError` inside a method body waits for the call) |
| a gate counts executions | executions can all hit a **wall** (a redirector, a catch-all) and still count |
| a consumer reads the wrong field | the producer looks silent when it explained itself perfectly |
| a container shape is assumed | `len(dict)` counts keys, not rows — a number that is wrong but plausible |

## The family — go to the sibling

| the symptom you are looking at | sibling reference |
|---|---|
| a gate demands an artefact **nothing produces** — failing every run, and older runs predate the rule | `phantom-requirements.md` |
| a gate says evidence is missing / "filler" but the file clearly EXISTS (`ls` and `stat` agree) | `unreadable-evidence-and-av-quarantine.md` |
| candidate list is full of junk; an index file scored HIGH | `aggregator-ingest-scope-and-false-positives.md` |
| the negative report is honest but not sendable | `negative-report-substance.md` |
| gate blocks on a CORRECT outcome (0 findings is the right answer) | `terminal-state-and-phase-appropriate-gates.md` (RULE 41) |
| a gate scores its own echoed output | `mechanical-triage-gate-and-self-echo.md` |
| a patch "succeeded" and nothing changed (CRLF anchor, stale variable) | RULE 31 + RULE 31b in SKILL.md |
| **gates all green and the vectors reached nothing** | `bug-bounty-exhaustive-testing` → `references/cdn-redirector-signed-url-audit.md` (see §7 below) |
| every probe line is `ERR` with `URL can't contain control characters`, and `0 interesting` | §"Hollow coverage" below — the probe base kept the `[NNN]` live-probe marker |
| every probe line is `ERR` with `getaddrinfo failed`; hostname looks like `host.env` / `hostwp-config.php` | §"Hollow coverage #2" below — wordlist bare path joined without `/` |
| a payload/PoC step fired at a third-party host (google, zendesk, CDN) | §"Scope leak" below — crawled links are NOT scope |
| CHECK 12 / asset-coverage fails although the run itself is correct | §"Stale ledger" below — `--derive` ran before the manifest closure mutated `tools-usage.json` |
| run says `COMPLETE` + `33/33` but the report predates the evidence, and relaunching changes nothing | §"Green gates on a stale evidence cache" below — phase-complete state is a cache a producer fix does not invalidate; the final gate checks artefacts EXIST, not that they are fresh |

## The one-line discriminators

```bash
# "nothing writes this artefact" -> phantom requirement
grep -rn "<artefact-name>" <pipeline-scripts>/     # hits only in the gate == no producer

# "the file exists but the gate says it is missing" -> readability, not presence
python -c "print(open(r'<path>','rb').read(64))"   # OSError EINVAL == AV/quarantine lock

# "the report says no reason recorded" -> read the producer's real field names
python -c "import json;print(list(json.load(open('<gated.json>'))[0].keys()))"

# "0 findings" -> did the vectors reach a real surface?
#   probe /  /nonexistent-xyz  /robots.txt  -> identical status+size == a wall, not an app
```

## The guards that now catch this family before a run

Three static checks in `hermes-health-audit.py`, each earned the hard way — **all must read BERSIH**:

| guard | catches |
|---|---|
| `import_fail` | runtime `NameError` that `ast.parse` misses |
| `unbound_name_fail` | a name used but bound in no enclosing scope — **closure-aware**, or it false-positives on every nested function (the first version flagged 37) |
| `budget_arith_fail` | `… + budget` unguarded, and `budget or 0` — `0` is *valid-but-fatal*: `deadline = now`, everything skipped silently, clean exit code |

Plus `bundle-sync.py check\|sync\|verify` so a shipped copy cannot drift from the live toolkit.

**When you build a new check of this shape, validate it against a known-bad fixture FIRST.** The
unbound-name guard's first version produced 37 false positives; a noisy guard is worse than none
because it trains you to ignore the real one.

## Hollow coverage — the `[NNN]` live-probe marker (2026-10-10)

`live.txt` / `urls.txt` lines are written with a status suffix: `https://host/ [200]`.
A consumer that only does `l.split("?")[0].rstrip("/")` keeps the marker and builds
`https://host/ [200]/api/profile` → **every** probe dies with
`URL can't contain control characters`, `0 interesting`, and the vector file still records
`EXECUTED`. Measured: **56/56 probes errored** across all 15 business-logic vectors — C3 coverage was
100% hollow while the gate counted it as full.

Discriminators (1 command each):
```bash
grep -c 'ERR' <dir>/business-logic/*.txt     # == "# PROBES: N executed" for EVERY file
grep -n "Probes base" <run log>              # a base containing ' [200]' is the smoking gun
```
Fix (producer side): strip the marker before use —
`l = re.sub(r"\s*\[\d{2,3}\]\s*$", "", l).strip()`. `execute-variants.py` and
`execute-references.py` already split on the space; `execute-business-logic.py` did not.
Rule: **any consumer of `live.txt`/`urls.txt` must strip the trailing `[NNN]` marker**, and assert
the built URL has no whitespace (a truncated target-dir path that swallows a space is the same bug —
see `msys-path-and-tool-invocation-traps.md`).

## Hollow coverage #2 — the missing-slash URL join (2026-10-10, same day, different vector)

A **second** way the same family produces `ERR`-only evidence — same symptom (`0 interesting`,
coverage counted as full), different mechanism and different fix. Found on `plugins.jetbrains.com`
while C2 was running.

Mechanism: the payload **wordlists** carry bare paths, the builder concatenates without a separator.

```python
# execute-variants.py:292-300  (PATH_ENDPOINTS branch, i.e. the wordlist path)
url = f"https://{domain}{payload}"          # BUG
#  domain  = plugins.jetbrains.com
#  payload = .env   /  web.config  /  config.php   (wordlist lines have NO leading slash)
#  ->  https://plugins.jetbrains.com.env       <-- the PATH became part of the HOSTNAME
```

`exploit-cookbook/references/sensitive-files-wordlist.txt` lines are `.env`, `.env.local`,
`.git/config`, `wp-config.php` … — **no leading `/`** (confirm with `head -5 <wl> | cat -A` → `.env$`).
Note the sibling `PATH_ENDPOINTS` dict literals **do** carry the slash (`"/.git/config"`), so the two
branches disagree and only the wordlist one breaks.

Measured on one run dir: **46/100** info-disclosure probes `ERR … getaddrinfo failed`, **32/32**
SSRF probes `ERR`, while `status: EXECUTED` was still logged for the vector.

Discriminators (1 command each — the marker bug and this one look alike until you read the error):
```bash
grep -c '^\[ERR\]' <dir>/variants/*.txt              # ERR-count == probe count => hollow
grep -o 'plugins\.jetbrains\.com[^ /]\{0,12\}' <dir>/variants/info_disclosure.txt | sort -u | head
#   see `jetbrains.com.env` / `jetbrains.comwp-config.php`  ==> missing-slash join
head -5 <wordlist> | cat -A                          # bare `$`-terminated path == no leading slash
```
Error-text triage (the three shapes are NOT interchangeable):
| evidence error | mechanism | fix site |
|---|---|---|
| `URL can't contain control characters` | `[NNN]` marker left in the base | strip the marker |
| `getaddrinfo failed` | payload glued onto the hostname | join with `/` |
| `first path segment in URL cannot contain colon` | the whole URL got **quoted** before use | unquote |

Fix (producer side — normalise in ONE helper, never rely on wordlist formatting):
```python
def build_probe_url(domain, path):
    """Join host + path safely regardless of leading slash."""
    return f"https://{domain}/{path.lstrip('/')}"
```
Apply it to **both** branches (wordlist path *and* the `PATH_ENDPOINTS` dict) so a future wordlist
edit cannot resurrect the bug. Same class as the marker fix: a consumer must not trust the shape of
upstream text.

Sibling bug in the same run: `urls.txt` itself carried a malformed third-party URL
(`https://plugins.jetbrains.com///www.googletagmanager.com/ns.html?id=…`) which was then handed to
`nuclei` and `dalfox` — so the scanners spent minutes attacking a Google Tag Manager page. Gate the
tool hand-off on the same in-scope host check (see "Scope leak" below) **and** reject URLs whose path
begins with `//`.

**Operator's preferred remedy when hollow coverage is found mid-run: finish first, fix after.**
Asked to choose between (A) let it finish as-is, (B) abort + fix + re-run 0C, (C) finish → fix →
re-run 0C..0F, he picked **C**. Do not abort a running phase to patch a producer; the downstream
invalidation recipe is the one above ("Green gates on a stale evidence cache").

## Scope leak — crawled links are NOT scope (2026-10-10)

The poc-techniques step fired SAML/CVE payloads at URLs harvested from crawled pages:
`myaccount.google.com` and `sales.jetbrains.com` (Zendesk). Nothing was harmed, but that is a
**scope violation** (third-party hosts), not a scanning quirk.

Rule: **host-gate every fired payload** — only hostnames matching the declared scope may receive a
payload; skip and record the rest (`SKIP_OUT_OF_SCOPE_HOST`). Before reporting, grep the evidence
dumps for hostnames outside scope; "no impact" is not an excuse, the request should not have been
sent. Same discipline as RULE 30 / Rule 30b.

**Implemented 2026-10-10** in `execute-poc-techniques.py::discover_urls()` (module-level
`_OUT_OF_SCOPE_HOSTS`), because a rule nobody implements is just prose:

```python
_t = urlparse(target if target.startswith("http") else "https://" + target).netloc.lower().split(":")[0]
_base = ".".join(_t.split(".")[-2:]) if _t.count(".") >= 1 else _t
def _in_scope(u):
    h = urlparse(u).netloc.lower().split(":")[0]
    return h == _t or h.endswith("." + _base)
```

Dropped hosts are recorded, never silent: `entry["skipped_out_of_scope_hosts"]`, a
`# SKIP_OUT_OF_SCOPE_HOST: payloads NOT sent to ...` line at the top of the evidence file, and a
`SKIP_OUT_OF_SCOPE_HOST: dropped N URL(s) -> [...]` log line. Verified on a real run dir: **22
crawled URLs dropped** (`myaccount.google.com`, `policies.google.com`, `fontawesome.com`,
`privacyportal-de.onetrust.com`, `static.zdassets.com`, …).

Insert the gate **before** `with_params`/`no_params` are derived, and note the writer orders
`ev_lines.insert(0, …)` *before* `ev_file.write_text(...)` — inserting after the write records the
field but leaves the header out of the file.

**Known blind spot (unfixed):** the match is by NAME, so a host that merely *looks* in-scope passes —
`sales.jetbrains.com` is Zendesk-hosted yet matches `*.jetbrains.com`, so payloads still reach it.
Catching that needs a CNAME/registrable-domain check (resolve the host, skip when the CNAME target
leaves the target's domain) or a vendor-SaaS suffix list. Flag it to the operator rather than
claiming the scope gate is total.

## Stale ledger — `--derive` before the producer finished (2026-10-10)

`prepare_coverage_gate()` runs `asset-coverage --init/--derive` **once**, and the manifest closure
(`_account_mandated_tools()`) **appends to `tools-usage.json` afterwards**. The derived ledger still
says `no entry in tools-usage.json` for a tool that ran seconds later → CHECK 12 fails on a correct
run, and the generic REWORK branch (re-run force execution) cannot fix it.

Discriminator: compare the `asset-coverage.json` derive time against `tools-usage.json` mtime.
Fix: re-run `python asset-coverage.py <dir> --derive` **after** the closure, then resume — or move
derive after the closure. `0E`/`0E-REVIEW`/`0F` entries being `NOT_RUN` at 0D time is EXPECTED (they
are produced later); only `0C` entries matter for CHECK 12.

## Green gates on a stale evidence cache — COMPLETE + 33/33, and the report is still wrong (2026-10-10)

**The most expensive instance of the family: every gate is green and the document is out of date.**

Symptom sequence, measured end-to-end:

1. Pipeline reaches `🎯 AUDIT PIPELINE COMPLETE (PHASE 0A→0F)` + `audit-checkpoint: TOTAL: 33/33
   checks passed` — with the findings layer built from **hollow** C3 evidence (see "Hollow coverage").
2. You fix the producer, re-run C3 standalone → `BUSINESS-LOGIC SUMMARY: 15/15 vectors`, `err=0`.
3. You relaunch the orchestrator expecting the report to be rebuilt. It finishes in **~60 s**, prints
   `FINAL GATE PASSED` / `33/33` again, and `Validated: None`. **Nothing was recomputed.** The report
   keeps the OLD funnel (26 candidates) although the evidence now says 14.
4. Only after the phase set is invalidated does the report move (funnel 14 candidates / 2 survivors,
   new timestamp).

**Why relaunch is a no-op:** phase-complete state is a **cache keyed on phase NAMES**
(`trackers/audit-pipeline-<safe_target>.json` → `completed_phases`, `current: DONE`), and sub-step
skip is separately keyed on **marker-file existence** (`_done(fname) = exists and size>100`). Fixing a
producer invalidates **neither**. So resume says `RESUME MODE: already completed [0A..0F]` and jumps
to the final gate, which re-verifies that artefacts *exist* — not that they were built from current
evidence. Same shape as the stale ledger above, one layer up.

Discriminators:
```bash
# report older than the evidence it aggregates == stale report (do NOT re-verify, RE-RUN)
ls -la <dir>/AUDIT-REPORT.md <dir>/business-logic-usage.json <dir>/tool-evidence | head
# every phase pre-marked done == relaunch is a no-op
python -c "import json;print(json.load(open(r'<trackers>/audit-pipeline-<slug>.json'))['completed_phases'])"
```

Fix — invalidate the cache, do **not** delete it (operator rule: delete = `_QUARANTINE` + manifest):
```python
S = Path.home()/"AppData/Local/hermes/trackers"/"audit-pipeline-<slug>.json"
cur = json.loads(S.read_text(encoding="utf-8"))
shutil.copy2(S, Q/f"state.before_rerun_{ts}.json")            # backup first
cur["completed_phases"] = ["0A","0B","0C"]                     # keep only phases you TRUST
cur["current"] = "0D"                                          # earliest invalidated phase
cur["note"] = "forced re-run: 0E/0F were built from hollow C3 coverage; producer fixed"
S.write_text(json.dumps(cur, indent=2), encoding="utf-8")
```
Then relaunch: 0D re-derives the ledger, 0E rebuilds the findings layer from the corrected evidence,
0F regenerates the report. Record the reason in `_QUARANTINE/manifest.json` alongside the backup.

Rule: **a green final gate is a statement about artefact existence, not about evidence freshness.**
After fixing any producer, ask "which downstream phases consumed the wrong data?" and invalidate
exactly those — the report is an aggregation, so a stale input propagates to the operator-facing
document, which is where it does the damage.

## The meta-rule

**After patching pipeline code, pick the verification bar that matches what you changed.**

```
syntax  ->  import  ->  call  ->  effect
```
Each bar passed while the next failed in this session. `ast.parse` catches neither a runtime
`TypeError` nor a silent skip. Run the changed script **against a real target dir** and assert on the
artefact it should have produced — not on the fact that it imported.

**And never let a broad handler swallow a defect into a status field.** An internal coding error
became `"status": "RAN_WITH_ERROR"` on every asset in a batch, which reads downstream as *the tools
failed*. If a handler is broad it must still record **which** exception. `RAN_WITH_ERROR` on every
item in a batch is a smell — check the code path before believing the tools.

## The checklist

```
□ Gates passed, AND the vectors reached a real surface?
□ Every artefact a gate demands is produced by some code path?
□ Aggregator excludes its own artefacts, its own output, and file-path keyword hits?
□ Run the aggregator twice — identical count?
□ Report reads the producer's real field names and container shape?
□ Report carries per-candidate reasons + a coverage table?
□ Static guards clean (import / unbound-name / budget-arithmetic)?
□ Shipped bundle in step with the live toolkit?
□ After a patch: syntax -> import -> call -> effect, whichever bar matches the change?
```
