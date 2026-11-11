# Gate re-derive, tz frame, and the FUZZ_ONLY hole (measured 2026-10-12, spectrocoin.com + auth.spectrocoin.com)

Two full 0A→0F runs in one session. Both ended **NEGATIVE** (`passed-findings.json = []`), both
gates GREEN — but **twice the 0D gate reported the identical failure on attempt 1 and needed
the rework branch**, and **a GREEN gate did NOT mean every manifest tool had fired**. All three
findings below are measured, not theorised.

---

## 1. `verify_tool_usage` REWORK re-runs the tools but never re-derives the ledger → HARD BLOCK loop

**Symptom.** `❌ GATE FAILED (attempt 1) — asset-coverage FAIL for phase(s): ['0C']`, then
`🔁 REWORK (generic): re-running full force execution`. Attempt 2 prints the **byte-identical**
failure. Without intervention attempt 3 HARD-BLOCKs and **no 0E/0F artefact is ever produced**.

**Why.** The gate's CHECK 12 reads `asset-coverage.json`. The rework path calls
`run_step5_tools()` (re-runs `force-full-execution.py`, which rewrites `tools-usage.json`) and
then loops straight back to the gate check. **Nothing re-derives `asset-coverage.json` from the
rewritten `tools-usage.json`** — so the gate re-reads a ledger that predates the rework, forever.

**Proof it was staleness, not real missing coverage.**
```bash
cd <dir> && python <skill>/scripts/asset-coverage.py . --derive
python <skill>/scripts/asset-coverage.py . --phase 0C      # -> 49 ok / 0 fail
```
Same dir, same artefacts, one `--derive` → PASS. The rework had really run the tools.

**Fix applied (additive, in `audit-pipeline-orchestrator.py` → `run_step5_tools()`):** after a
successful re-run, re-derive before returning:
```python
cov = Path(r"~/.chiper/skills/security"
           r"\audit-execution-discipline\scripts\asset-coverage.py")
if cov.exists():
    _sp.run(["python", str(cov), str(self.output_dir), "--derive"], capture_output=True)
```
Backups kept beside the file: `audit-pipeline-orchestrator.py.bak_gate_rederive_<ts>`.

**CORRECTION — this patch was recorded as "Verified" and it was NOT.** Attribution error, caught
on the very next engagement: attempt 2 passed only because a background safety-net `--derive`
loop (started by hand as a stopgap) was refreshing the ledger every 4 s. The patch itself was a
**no-op**, and on engagement #3 the same two failures came back with **no patch log line at all**.
Read §1b before trusting any "the fix worked" claim, including one written in this file.

## 1b. A patch guarded by `if path.exists()` fails SILENTLY — verify the patch's OWN log line

**What happened.** The re-derive block was inserted as
```python
cov = Path(r"C:\…\hermes\skills"
           r"\audit-execution-discipline\scripts\asset-coverage.py")   # ← MISSING \security\
if cov.exists():
    … log("asset-coverage re-derived after rework (rc=…)")
```
The real location is `…\hermes\skills\**security**\audit-execution-discipline\scripts\asset-coverage.py`.
`cov.exists()` returned **False**, so the whole block was skipped: no re-derive, **and no error**.
`py_compile` passed. The rework ran, the gate re-read the stale ledger, attempt 2 failed with the
byte-identical message.

**The tell — use it every time.** A patch like this is only observable through its side effect.
Do not accept "the file compiles" or "the code is present" as verification:
1. **Grep for the patch's own log line in the next run's log.** Its absence is the failure signal.
   `grep -n "re-derived after rework" <dir>/orchestrator-run.log` → empty ⇒ the branch never ran.
2. **Read the path out of a neighbouring known-good block** in the same file
   (`final_coverage_gate()` already had the correct `skills\security\…` literal) instead of
   retyping it from memory. One `grep -n "asset-coverage.py" <script>` would have caught it.
3. **Assert the precondition once, up front**, before relying on the guard:
   `python -c "import pathlib;print(pathlib.Path(r'<path>').exists())"` → must be `True`.
4. **A safety net masks the patch.** If a background loop / watchdog is compensating for the bug,
   you cannot attribute a later success to the patch. Either stop the net for one attempt, or
   verify via (1). "It passed after I patched it" is not evidence when something else was also
   fixing it.

> Same family as RULE 31 (`references/rules/11-rule-31-patch-verify-loop-never-trust-a-patch-succeeded.md`)
> and `silent-failure-static-guards.md`: **run it on a real target-dir, and read the artefact the
> patch was supposed to change** — never `ast.parse`, never the absence of a traceback.

**Emergency unblock if you can't patch mid-run** (worked for run #1): loop a `--derive` every few
seconds in the background until the log shows `GATE PASSED` / `HARD BLOCK`, then kill it.

> Generalised rule: **any rework branch that regenerates an input must also regenerate the ledger
> derived from it.** Silent-drift class — see `whole-chain-contract-audit.md`.

---

## 2. `asset-coverage._ts()` compared UTC against a NAIVE-LOCAL run window → hand-written evidence rejected

**Symptom.** `cross-artefact: 0 target-mismatch, 9 stale-timestamp -> NOT_RUN` and
`timestamp '2026-10-12T02:49:51+07:00' predates the run (2026-10-11T23:41:19.72...)`.
The evidence was **later** than the run start, not earlier.

**Why.** `_ts()` did `v.astimezone(timezone.utc).replace(tzinfo=None)` for any tz-aware stamp,
but `run-meta.json → started_at` is written **naive local**. A `+07:00` stamp 02:49 local becomes
19:49 "UTC", which *is* < 23:41 local − 1h → every asset touched by a manual/gap run flipped
`USED → NOT_RUN`.

**Two fixes, both needed:**
1. Patch `asset-coverage.py::_ts()` → normalise to the **same frame as `started_at`**: naive local
   (`v.astimezone().replace(tzinfo=None)`; no-arg `astimezone()` = local). Backup:
   `asset-coverage.py.bak_ts_tz_<ts>`.
2. **When you write evidence by hand, emit a NAIVE stamp**: `# TS: 2026-10-12T05:30:00`
   — **no `+07:00`**. `date -Iseconds` is the trap (it appends the offset).

Sanity check that costs one line:
```python
dt.datetime(2026,10,12,2,49,51,tzinfo=dt.timezone(dt.timedelta(hours=7))).astimezone().replace(tzinfo=None)
# -> 2026-10-12 02:49:51  (must NOT be < run start - 1h)
```

---

## 3. THE FUZZ_ONLY HOLE: a GREEN 0D gate does not prove every manifest tool ran

Operator instruction that exposed it: *"pastikan semua tools dan skill dalam fasenya dipanggil,
jgn dilewati atau curl2 aja"*.

`force-full-execution.py` refuses to invent CLI flags. For any tool without a **verified
invocation** in its own registry it records:

| status | reason written by the producer |
|---|---|
| `FUZZ_ONLY` | `"<tool>: no verified CLI invocation for vuln_type=<v> — fallback HTTP probe only"` |
| `SKIP_WITH_REASON` | wordlist resolved to nothing (e.g. ffuf) |

`asset-coverage --derive` maps `FUZZ_ONLY` / `SKIP_WITH_REASON` → **N/A "documented skip"** →
CHECK 12 PASSES. So the gate can be fully green while ~11 manifest tools never executed.
**Measured on run #2:** `ssrfmap, graphqlmap, jwt_tool, sstimap, smuggler, sslscan, subjack,
linkfinder, secretfinder, cloud_enum, kube-hunter` = all `FUZZ_ONLY` under a passing gate.

### Closing the hole (this is the accepted procedure)

1. **Run each tool for real** against the in-scope target, gentle, one run per tool.
2. Write the output in the pipeline's own evidence format — the `# TOOL EVIDENCE:` marker is
   what the anti-fabrication check greps for:
   ```
   # TOOL EVIDENCE: <tool>
   # TARGET: <url>
   # CMD: <exact command>
   # EXIT: <rc>
   # TS: <naive local, NO offset>
   --- OUTPUT ---
   <raw output>
   ```
3. **Update the ledger row** (`tools-usage.json`) for that tool:
   `status` = `EXECUTED` (rc 0) / `RAN_WITH_ERROR` (ran, non-zero — both map to USED when the
   evidence marker is present) / `NOT_FOUND` only if the binary truly is absent;
   plus `evidence_file`, `command`, `timestamp` (naive).
4. `asset-coverage.py . --derive` → `verify-tool-usage.py .` → `deep-audit-mode.py guard .`
   Re-derive AFTER the ledger edit; the checks read the derived ledger, not the raw one.
5. Never mark `EXECUTED` without a real run — CHECK 12 re-validates file existence **and** the
   marker, so a hand-written claim with no output file fails anyway.

### Making a manifest tool actually resolvable (the FIX, not "the tool is broken")

`force-full-execution` + the orchestrator locate tools with `shutil.which`. On Windows:

* **`shutil.which` needs an extension.** A bare bash script named `linkfinder` may resolve from
  bash but not from Python. Create **both** wrappers in a PATH dir (`$HOME/go/bin`):
  a shebang script *and* a `<name>.cmd` that calls the real script
  (`@echo off` + `python "<repo>\linkfinder.py" %*`). Verify from **bash-launched** Python
  (same env the pipeline uses): `python -c "import shutil;print([t for t in TOOLS if not shutil.which(t)])"`.
* **`execute_code`'s Python has a different PATH** than the terminal's — a tool can look
  unresolvable there and be perfectly fine in the pipeline. Always do the final check from
  `terminal`.
* **ffuf's wordlist path is probed, not configured**: `D:/data hermes/wordlists/0C-api/api-endpoints.txt`,
  else `D:/data hermes/wordlists/0B-recon/common.txt`, else `<workdir>/words.txt`. If none exists →
  `SKIP_WITH_REASON`. Copy `0B-recon/directories/common.txt` to `0B-recon/common.txt` to arm it.
* **Go-source tools** (`byp4xx`): `go mod init <n> && go build -o <PATH>/byp4xx.exe .`.
* **Python-repo tools** without a PyPI package (linkfinder, secretfinder, cloud_enum, smuggler
  → clone; sstimap, ssrfmap, graphqlmap → clone): the `.cmd` wrapper is the whole integration.

### jwt_tool specifically

* It **crashed with `KeyError: 'argvals'`** because `~/.jwt_tool/jwtconf.ini` was an older schema,
  and `createConfig()` could not regenerate it on modern Python (`InvalidWriteError: ... contains
  delimiter :`). Fix = delete/rename the stale ini and **write a minimal one by hand** with
  `[crypto] [customising] [services] [input] [argvals]` (drop the comment-keys that contain `:`).
* Pass the token as the **positional STRING** — a file path yields an empty `Original JWT:`.
* To actually *send* a forged token you must give it a place to substitute:
  `-rh "Auth…: Bearer <tok>"` (built from fragments if the client redacts the header name).
  Without it: `[-] No substitution occurred`.
* Real result on a serious IdP: `alg:none` (4 casings) / null-signature / RSA key-confusion →
  **401 every time**. Record it as a genuine negative with the tool's own output.

### 3b. THE PRODUCER IS NOW FIXED — stop hand-closing the hole (patch applied 2026-10-12)

§3 above is the *manual* escape hatch. It is no longer the normal path: the root cause was a
registry gap in the producer, and the producer now carries verified invocations.

**Root cause of FUZZ_ONLY — two defects, both in `force-full-execution.py`:**

1. **`tname` did not strip `.cmd`.** The per-tool branch chain matches
   `tname = Path(tool_path).name.lower()` with `.exe/.bat/.py` removed. Tools that resolve through
   a `.cmd` wrapper (`linkfinder, secretfinder, cloud_enum, smuggler, jwt_tool, sstimap, byp4xx`)
   kept the literal `linkfinder.cmd` → **no branch ever matched** → fell to the final `else` →
   `FUZZ_ONLY`. A `.cmd`-wrapper tool was therefore *structurally incapable* of running, no matter
   what was installed.
2. **No branch existed** for `sslscan, subjack, linkfinder, secretfinder, cloud_enum, kube-hunter,
   smuggler, sstimap` even with a correct `tname`.

**Fix (additive, backups kept as `force-full-execution.py.bak_verified_cli_<ts>`):**
`tname` gains `.replace(".cmd","")`, a `ghost` host variable is derived once
(`self.target.replace("https://","").replace("http://","").split("/")[0]`), and each missing tool
gets a branch with its **verified** invocation:

| tool | invocation | note |
|---|---|---|
| `sslscan` | `sslscan <host>` | bare HOST — a scheme/path is a usage error |
| `subjack` | `subjack -d <host> -t 3` | |
| `linkfinder` / `secretfinder` | `<tool> -i "<url>" -o cli` | |
| `cloud_enum` | `cloud_enum -k <ORG> -t 20 --disable-azure -qs` | see below |
| `kube-hunter` | `kube-hunter --remote <host> --report plain` | |
| `smuggler` | `smuggler -u "<url>/" -m POST -t 20 -q` | |
| `sstimap` | `sstimap -u "<url>" --level 1` | |
| `jwt_tool` | *(no run)* → `SKIP_WITH_REASON` + reason | needs an issued JWT; documented skip, NOT a silent FUZZ_ONLY |

**cloud_enum has two traps:**
* **`--disable-azure` is mandatory on this host.** The Azure container brute-force
  (`-b fuzz.txt`, 1837 names) never terminates — it was killed every single run. AWS+GCP finish in
  **~6 s** with `--disable-azure -qs`. State Azure as a bounded-scope exclusion rather than letting
  the tool be killed and recorded `RAN_WITH_ERROR`/`TIMEOUT` (TIMEOUT can never pass CHECK 12).
* **keyword must be the ORG label, not the first label.** `ghost.split(".")[0]` gives `auth` for
  `auth.spectrocoin.com` — i.e. it probes `auth` buckets and misses the org entirely. Use
  `ghost.split(".")[-2] if ghost.count(".") >= 1 else ghost` → `spectrocoin`.

**Verification — run the producer once, do not trust `py_compile`.** A real
`force-full-execution.py <url> --tech … --output-dir <tmp>` run gave:
`sslscan/secretfinder/cloud_enum/kube-hunter/smuggler/sstimap = EXECUTED`, `subjack = NO_OUTPUT`,
`jwt_tool = SKIP_WITH_REASON` → **zero FUZZ_ONLY**. Read `tools-usage.json`, not the log.

> **Discriminator — `FAILED_USAGE` is not necessarily a broken invocation.** `linkfinder` reported
> `FAILED_USAGE` in that same run; the evidence file's own output said
> `Error: invalid input defined or SSL error: HTTP Error 429: Too Many Requests`. The invocation was
> correct, the **target** was throttling. Read the tool's raw output before \"fixing\" the command —
> otherwise you re-patch working code. (Same family as `claim-discipline-verify-before-assert.md`.)

**Consequence for future runs:** the FUZZ_ONLY hole only needs reopening if a *new* tool is added to
`MANDATORY_TOOLS` without a branch. Then add one verified invocation — do **not** go back to
hand-running tools + hand-editing the ledger.

---

## 4. Canonical dir vs engagement dir — a PARTIAL copy fails the guard

The orchestrator writes to `~/.chiper/skills/bounty-pack/poc-plans/orchestrator-<host>_<...>`; the gate
you call reads **whatever dir you pass**. Copying only `*.json` + `tool-evidence/` into the
engagement dir produces exactly three guard failures:

```
❌ PoC variant evidence missing: ['<repo>']          -> missing poc-variants/
❌ asset-coverage FAIL for phase(s): ['0C']          -> 0C:payload:poc-variants(C5) NOT_RUN
❌ skills claimed applied w/o evidence on disk: [...] -> missing skill-evidence/ + late-skills.txt
```
Fix = **full** copy of every entry (`for e in *; do cp -r "$e" "$B/"; done`, excluding the log),
then `--derive`, then re-run both checks. Cheapest correct option: just run the guard on the
orchestrator dir and treat that as canonical.

---

## 5. `[STALL-WARN]` is usually a false alarm — verify from artefacts, not the log

`[STALL-WARN] orchestrator: no step progress for NNNs (last phase 0A, pid=…)` is emitted by an
external monitor watching the **phase field**, which only advances at *step* boundaries — the
whole 0C tools/variants/DOM-XSS/impact sequence runs inside one phase. Add `| tee` block-buffering
the log, and a 15-minute "stall" can be a healthy run.

Truth check (in this order): **evidence-file mtimes** (`find <dir> -newermt '-8 minutes' -printf
'%TT %s %p\n'`), then the Windows process list. Do not judge from `tail`.

When a tool *is* genuinely wedged (a `nuclei` left over from a **previous** orchestrator run,
alive 40 min): `taskkill /F /T /PID <WINPID>`. **MSYS `ps` PID ≠ Windows PID** — read WINPID from
column 4 of `ps -W` (`…… <msyspid> <ppid> <pgid> <WINPID> ?`), or `taskkill` answers
`ERROR: The process "<msys-pid>" not found`. At loadavg ≈ 88 on 4 vCPU even `tasklist` hangs —
relieve the box first (see `unstick-frozen-pipeline-tool-loop.md`).

---

## 6. Reusable vector recipe: legacy SOAP / WSDL service on a modern estate

Found a live legacy SOAP OAuth2 service on the apex host (`…/api/oauth2?wsdl`).

* The first WSDL is only a shell → `wsdl:import location="…?wsdl=<name>.wsdl"`; **fetch that** for
  the real schema (`xs:element`/`xs:complexType` → parameter list, e.g. `client_id, client_secret,
  user_name, user_pass, version, scope…`). `soapAction=""`, style `document`, use `literal`.
* **Prove the endpoint works before testing it**: a plain, well-formed envelope returned
  `HTTP 500 <soap:Fault>` from the origin (the *origin's* fault, not the WAF's 403). That is the
  signal that payloads are actually reaching the parser.
* **Discriminator: WAF block vs origin parse.** DOCTYPE-bearing envelopes answered
  `403 <!DOCTYPE html> … Cloudflare "Attention Required!"`; the body *never* reached the origin.
  So `403` here is **not** "no vulnerability", it is "vector blocked at the edge".
* **XInclude is the DOCTYPE-free bypass to try first**: `<xi:include parse="text" href="…"/>` with
  no DTD passed the WAF (origin answered), but the origin did **not** resolve the entity —
  verdict was *not demonstrated*, with the residual gap stated honestly.
* Also try `data:` in place of `file://` (the `file://`/`/etc/passwd` shape is what the WAF greps).
* Non-destructive only: read-only GET/POST against the vendor's own documented endpoint; no
  entity-expansion/"billion laughs" payloads.

---

## 7. SPA / `static-site` role: enrich `urls.txt` from the bundle BEFORE 0C runs

**Measured on two products in one session.** `_deep_recon()` classifies the host and enumerates
endpoints, but on a client-rendered app it under-delivers:

| product | host role | endpoints deep-recon found | real API endpoints in the bundle |
|---|---|---|---|
| `auth.spectrocoin.com` | `redirector` | 6 | ~30 |
| `profile.spectrocoin.com` | `static-site` | 4 (`/`, `/favicon.ico`, `/robots.txt`, `main.<hash>.js`) | 36 |

A 4-URL `urls.txt` means 15 payload variants + 15 business-logic vectors + 52 references all fire
at the app shell — the classic *"hollow coverage from the files `urls.txt`/`live.txt`"* case in
`coverage-lies-and-report-quality.md`. The gate stays green (every vector "ran"), the finding count
is 0, and none of it measured the product.

**Which steps read what (measured by grepping the producers — keep this table when widening):**

| producer | reads |
|---|---|
| `force-full-execution.py` | `urls.txt` |
| `execute-variants.py` | `crawled.txt`, `live.txt`, `urls.txt` |
| `execute-business-logic.py` | `urls.txt` |
| `execute-references.py` | `urls.txt` |
| `execute-poc-variants.py` | `crawled.txt`, `live.txt`, `urls.txt` |

So **`urls.txt` is the single lever** — and the 0C sub-steps re-read it when *they* start, which
means appending after 0B and before/while `force-full-execution` is running still reaches C2/C3/C4/
C5/C6. No restart needed.

**Recipe (do it during 0B, as soon as `urls.txt` looks thin):**
```bash
P=https://<host>; UA="Mozilla/5.0 … Chrome/124.0"
curl -s -A "$UA" "$P/<main-bundle>.js" -o bundle.js          # path from urls-deep.txt / html-assets
grep -oE '"/api/[a-zA-Z0-9/_{}.-]+"' bundle.js | sort -u     # API paths
grep -oE '"/[a-zA-Z][a-zA-Z0-9/_.-]{2,60}"' bundle.js \
  | sort -u | grep -viE '\.(css|js|png|jpg|svg|woff|ttf|webp|gif|json|ico)$'   # routes + endpoints
```
Also read `gen-cfg.js` / `window.config` — it names the related services
(`AUTHORITY`, `TOKEN_ENDPOINT`, `CLIENT_LOGOUT_ENDPOINT`, `SIGNUP_URI`), which is how you learn the
estate is multi-product in the first place.

Then **append, de-dupe, and keep the original lines** (`dict.fromkeys(old + new)`), writing the
result back to the orchestrator's `urls.txt`. On `profile.spectrocoin.com`: 34 → 74 URLs, 36 real
endpoints (`/api/fe/profile/state`, `/debit-cards`, `/verifications/*`, `/user-contracts/sign`,
`/user/secrets`, `/uaa/api/2fa/*`, `/uaa/api/devices`). Verdict stayed 0 findings, but it was now
a 0 measured against the actual product surface.

> Boundary: this is *widening the input the pipeline already owns*, not hand-scanning. Use the
> bundle as the oracle (it is the app telling you its own API), never invent paths.

---

## Net verdicts (for calibration)

| engagement | candidates | cleared validation | reportable | gates |
|---|---|---|---|---|
| `spectrocoin.com` (web2 SPA) | 182 | 0 | **0** | 33/33 · 13/13 · GREEN |
| `auth.spectrocoin.com` (OIDC IdP) | 43 | 0 | **0** | 33/33 · 13/13 · GREEN |
| `profile.spectrocoin.com` (authed account app) | 51 | 0 | **0** | 33/33 · 13/13 · GREEN |

Third run needed the safety-net loop again (the §1b no-op), then **the corrected patch + this
reference's §1b check** — see §1b for how it was caught. `exchange.` and `pro.` are 302 → the apex
host, i.e. not separate products; check liveness before opening an engagement
(`curl -o /dev/null -w "%{http_code} -> %{redirect_url}"`), don't inherit a host list on faith.

Both runs' top "candidates" were **Cloudflare challenge pages** (`title: Just a moment...`) scoring
`impact_score=6` from the impact gate — the triage gate dropped all of them. A hardened target
producing an honest zero *with coverage attached* is the correct outcome, not a reason to
re-declare the pipeline broken.
