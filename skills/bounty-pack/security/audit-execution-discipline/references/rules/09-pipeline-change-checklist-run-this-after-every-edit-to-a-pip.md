## Pipeline change checklist — run this after EVERY edit to a pipeline script
Doing only step 1 and declaring victory is how a "fixed" pipeline stays broken for the next engagement.

1. `python -m py_compile <script>` — syntax only, proves nothing else.
2. Copy the edited file(s) into the shipped bundle: `bundle-src/audit-pipeline-bundle-v1/toolkit/scripts/`.
   **A script the executors load from their own directory MUST be in the bundle** (this is exactly how
   `tool_router.py` was missing while five executors imported it → silent HTTP fallback on any fresh machine).
3. Rebuild the zip (`D:/data hermes/audit-pipeline-bundle-v1.zip`) and **md5-compare the patched files
   live-vs-zip**. A zip built before the last edit silently ships the old code — this happened twice in
   one session.
4. End-to-end dry run against a throwaway local target (`python -m http.server <port>`), then read the
   produced `tool-evidence/*.txt` + `tools-usage.json` and confirm: every tool shows a real invocation,
   no `FAILED_USAGE`, parameterized URLs reached sqlmap/dalfox.
5. Run the gate over that workspace and confirm the verdict is *earned*: passes for the steps that ran
   (variants / PoC / business-logic / references / techniques) and failures only for genuinely pending
   or unaccounted steps. A gate that passes while a scanner never ran is worse than a failing gate.
6. Clean up: kill test servers, and check for leaked helper processes (`tasklist | grep -i interactsh`).

**End-to-end dry run (proof the pipeline is wired), local target `http://127.0.0.1:8096`:**
- C1: arjun, sqlmap, dalfox, kxss, ffuf, CORScanner, race-checker = EXECUTED with on-disk evidence; sqlmap automatically switched to the discovered parameter URL `/page?q=1`; gobuster NO_OUTPUT; graphqlmap RAN_WITH_ERROR; SSRFmap NEEDS_REQUEST_TEMPLATE; interactsh STARTED_NO_TOKEN.
- C2: 15/15 vectors routed to REAL tools (dalfox/nuclei/graphqlmap per class), 244 requests.
- PoC layer: 1 executed + 9 no-entry-point (logged); PoC variants 2/3 repos, 8 requests.
- Business-logic: 15/15 vectors, 56 probes, 22 interesting.
- References layer demonstrably fires real tools too (ref-35/36-arjun.txt) — note it can call the router **per clue**, so it runs under its own budget/`--tool-cap` (was an uncapped 600 s-per-arjun-call, which is why C6 aborted the orchestrator at 2400 s; see `references/pipeline-tool-timeout-budget.md`).

`tool_router.py` got the same treatment (sqlmap param guard, graphqlmap `.bat` invoked directly instead of through python.exe).

Smoke-verified 2026-09-29 against a throwaway `python -m http.server`: dalfox/gobuster/ffuf/nuclei/CORScanner/race-checker/sqlmap all ran real scans (nuclei even emitted `[tech-detect:python]`, ffuf wrote a real JSON of results); graphqlmap loaded and issued a real HTTP call. Re-run that smoke test after touching the table (expected positive banners per tool are in `references/tool-execution-verification.md`).

**Parameter/template targeting (2026-09-29):** sqlmap has no templates — it needs a URL with `?p=v` + the auth cookie; `_param_url()` auto-picks target → urls.txt → openapi.json (same-host), else deeper discovery (openapi → katana crawl → arjun). nuclei runs against the local mirror `D:\data hermes\nuclei-templates` via `-t "<mirror>/http" -tags ...` — **`-template-dir` is not a flag** (`-t` accepts template directories). For a target-specific surface, write a 1-off YAML from a captured request + cookie and run `-t my.yaml`. Full recipe: `references/tool-param-template-targeting.md`.

**⛔ Re-zip the handoff bundle after ANY pipeline patch** — the ZIP at `D:\data hermes\audit-pipeline-bundle-v1.zip` goes stale the moment a live script is patched; the user ships it to other agents. Flow (live patch → sync bundle-src → `_gen_index.py` → MANIFEST/LOAD → Python-zipfile rebuild → testzip + old/new diff): `references/audit-pipeline-bundle-rezip-2026-09-29.md`.

**⛔ RULE 2c: "status:EXECUTED" is a LIE — verify by reading the evidence BODY**

**User correction (quarterwise audit 2026-09-28): "Sdh all tools dpakai? Dan all varian attack?"** — asking the question exposed that `tools-usage.json` said `EXECUTED` for nine tools that had *scanned nothing*:

```
dalfox      → `unknown command "https://…"`   ← wrong CLI, exit 1, never scanned
CORScanner  → `unrecognized arguments: --headless` ← never scanned
SSRFmap     → `error: the following arguments are required: -r, -p` ← never scanned
sqlmap      → `no parameter(s) found for testing in the provided data` ← no param tested
nuclei(nosqli tag) → target was a *foreign* URL scraped from page content, not the target
race-checker→ ran against a static root page → 4/50 "success", meaningless
```

All of these had a non-empty `tool-evidence/*.txt` (>100B — the gate's threshold passed) because the file contains the **error banner**. A >100B evidence file proves a *process ran*, not that a *test happened*.

**MANDATORY — after any pipeline run, before claiming tool coverage:** read the evidence BODY of every file, don't trust the size or the `status`:

```bash
# the only trustworthy read: what did the tool actually say?
for f in <out>/tool-evidence/*.txt; do
  echo "=== $(basename $f)"; tail -c 400 "$f" | tr -d '\r'; echo
done
```

Treat as NOT-RUN (and re-fire with corrected CLI) if the body contains any of:
`unknown command`, `unrecognized arguments`, `required: -r`, `no parameter(s) found`,
`Usage:`, `error:`, `Could not find template`, a `Usage`/help banner, or a target URL
that is NOT the audit target.

**⛔ Sub-case: an ENVIRONMENT failure recorded as a NEGATIVE (atmail deep-dive 2026-09-30).**
A transient DNS outage on the workstation (~2 min) silently turned three steps into fake negatives
written straight into the report table:

```
kxss      → dial tcp: lookup api-gwy.pc4.atmailcloud.com: no such host   ← resolution failure
curl      → POST /auth -> 000                                            ← never left the box
sqlmap    → [CRITICAL] host 'api-gwy.pc4.atmailcloud.com' does not exist  ← aborted, scanned nothing
```

`sqlmap` had been *reported as "negative"* — it had not sent a single request. The tells, all
mechanical, are: **a CRITICAL/DNS line in the log, an exit that returns in ~0 s, a `000` HTTP code,
and a `curl` that also fails at the same moment.** Resolution failures are contagious across tools
in the same window, so **if one tool in a batch shows DNS/`000`, re-verify DNS and re-run the whole
batch — do not trust any negative from that window.**

**Sibling case — a tool that aborts on its own transport error (Superstate 2026-09-30).**
`arjun` stopped with `Encountered an error: api.superstate.com` / `Skipped https://... due to
errors`, and every injection payload returned a Cloudflare challenge page. That is a **BLOCKED**
result attributable to the edge WAF, not evidence the parameter is clean. Same for any scanner
that dies on a 403/challenge from Cloudflare/Akamai/DataDome: record it in the coverage ledger
as `BLOCKED (edge WAF)` and name the payloads never delivered — never as "tested, negative".
If the class genuinely matters, move to whatever gets through (`bot-protected-target-testing`)
or a documented-safe subset instead of reporting a clean negative you did not earn.

Cheap pre-flight before any tool that is supposed to produce a NEGATIVE:

```bash
python -c "import socket;print(socket.gethostbyname('<host>'))"   # must print an IP
curl -sk -m 10 -o /dev/null -w "%{http_code}\n" https://<host>/<target-path>   # must not be 000
```

And the honest outcome vocabulary for this case is **NO RESULT / re-run pending**, never
"negative" — a tool that could not resolve the host has told you nothing about the target.
After the re-run, quote the *tool's own* conclusion verbatim (e.g. sqlmap's
`POST parameter 'JSON username' does not seem to be injectable`) as the evidence.

**⛔ Sub-case: the ANONYMOUS-RPC false negative (Superstate 2026-09-30).** Same costume, third
disguise. `forge test` fork suites need an **archive** node. A non-archive public RPC does not
say "no archive" — it fails per-account and the failure lands in the pass/fail column looking
exactly like a target defect:

```
[FAIL: EVM error; database error: failed to get account for 0x5615dEB7…:
 HTTP error 403 … "Archive requests require a personal token"]
```

Tells: the error text is a **provider/JSON-RPC message**, the hex address is Foundry's own
deterministic deployer (not the target), and *every* forked suite fails identically while all
non-fork suites pass. `rpc.flashbots.net` says it plainly (`state at block #N is pruned`);
provider wording differs, the cause is identical. Supplying a working RPC turned the same
suite from "6 failed" into **231 passed / 0 failed**. Vocabulary for this case: **provider
capability gap / re-run pending**, never "failing tests" and never "negative".

**⛔ Sub-case: the EXIT CODE lies while the run succeeded (slither shim, 2026-09-30).** The
inverse of RULE 2c's usual shape — `slither . --foundry-ignore-compile > out 2>&1; echo $?`
returned **127** ("command not found") while `out` contained a complete, correct analysis
ending in slither's own summary line. Do not void a run on the exit code, and do not
"re-fix" a tool that already worked. The evidence body is the source of truth in **both**
directions: a non-empty file proves a process ran (not that a test happened), and a non-zero
exit does not prove it failed. Read the last lines of the artifact before either verdict.

**Also enforce:** the pipeline must never inherit a target from scraped page content.
A `gov.uk` URL appearing in page copy became a nuclei target this run — out of scope,
an unintended third-party scan. Sanitise recon URLs to the audit host's registrable
domain before any tool fires (see RULE 28 bullet on full-URL targets).

**Reporting shape:** when the user asks "all tools used / all variants tested", answer
with a per-tool table of **RAN / FAILED / NOT-INSTALLED / N-A**, where the verdict comes
from the evidence body — plus an explicit **gaps** list. Never answer "yes, all done"
off the usage JSON alone.

**Answer "did you use ALL tools / ALL variants?" mechanically, never from memory.** The user asks
this on most engagements and it is a trap for self-reporting. Two steps:

```
# 1. enumerate the tool universe and mark what is even present on this box
for t in subfinder httpx katana gau ffuf gobuster dirsearch nuclei dalfox sqlmap arjun kxss \
         interactsh-client CORScanner commix graphqlmap SSRFmap race-checker nmap whatweb \
         wpscan nikto testssl sslscan jwt_tool tplmap sstimap xsstrike wfuzz feroxbuster; do
  printf "%-18s " "$t"; command -v $t >/dev/null 2>&1 && echo INSTALLED || echo "not-installed"
done
python -c "import importlib
for m in ['graphqlmap','race_checker','playwright','websocket','jwt','wafw00f']:
    try: importlib.import_module(m); print(m,'INSTALLED')
    except Exception: print(m,'not-installed')"

# 2. diff INSTALLED against the tools that actually left evidence on disk
ls -la <out>/tool-evidence/ <out>/tools2/   # whatever this engagement wrote
```

That produces three honest classes, and only the middle one is embarrassing:

- **NOT-INSTALLED** -> honest N-A on this host. Name it as a coverage gap; do not install mid-audit
  unless the class needs it.
- **INSTALLED but never fired** -> the real gap. This session `commix` (command injection) and
  `wafw00f` (WAF fingerprint) were both present and never run — a reviewer asking "all tools?" would
  have caught it. Check these before answering.
- **RAN but evidenced only by an error banner** -> covered by the RULE 2c body-read above.

Then answer with the per-tool table + a short explicit **gaps** list, and say what you would need to
close each gap (an account, a request template, a param-bearing URL). "Yes, all done" is never the
answer; "here is the table, here are the three gaps and why" is.

> **Full failure-signature table + the one command that tells the truth + the
> recon-URL scope-leak guard:** `references/tool-execution-verification.md`

**⛔ RULE 2c-bis: 0-byte evidence ≠ negative · fuzzer falsification ≠ finding · bytecode findings need attribution**

Tiga pola triase yang lahir dari engagement Superstate (2026-10-01). Detail + perintah ada di
`references/evidence-and-scanner-triage.md`.

1. **File bukti 0 byte bukan negatif.** `nuclei -silent ... > out.txt` dengan nol temuan menulis file 0 B —
   tidak bisa dibedakan dari "scan tidak pernah jalan". Jangan pakai `-silent` untuk scanner yang diperkirakan
   kosong; bungkus dengan banner + `echo "=== exit=$? ==="` + marker selesai, lalu `grep` marker itu sebelum
   mengutip negatif. Untuk tool yang stdout-nya memang kosong saat bersih (trufflehog `--json`, subfinder/httpx),
   **stderr-nya yang jadi bukti run** — trufflehog menaruh `{"msg":"finished scanning","chunks":…,"verified_secrets":0}`.
   Sebelum bilang "semua tool selesai", jalanin sapuan 0-byte (cuplikan di reference) dan jelaskan tiap hit.
2. **Falsifikasi echidna/medusa = hipotesis, bukan temuan.** Pisahkan dengan eksperimen pembeda: salin harness,
   hapus SATU aksi tersangka, jalankan ulang. Properti yang berubah jadi `passing` penyebabnya aksi itu; yang
   tetap gagal berarti nyata ATAU invarian kita salah. **Curigai invarian sendiri lebih dulu** (kasus nyata:
   invarian saya tidak memodelkan gross-up fee, jadi FP). Saat menulis invarian atas aritmatika uang, tulis ulang
   semantik pembulatan/gross-up kontrak di dalam invariannya.
3. **Atribusikan temuan bytecode ke fungsinya sebelum menilai severity.** Mythril mode bytecode mencetak
   `Function name: constructor` untuk temuan apa pun dan hanya memberi blob `calldata:`. Ambil selector 4-byte-nya
   dan cocokkan dengan `cast sig "<signature>"`; satu temuan "High" di sini ternyata menunjuk `initialize(...)`,
   bukan aritmatika uang → rating turun jadi QA. Menilai dari label scanner = overclaim.

**⛔ RULE 2d: Aim the tool at the PARAMETERISED, AUTHENTICATED surface**

The natural follow-on failure from RULE 2c: even a correctly-installed tool tests **nothing**
when pointed at a root/static page. `sqlmap -u https://target/` → `no parameter(s) found`;
ffuf/dalfox/arjun on the marketing root → 0 signal. The real surface is
`/path?param=value` **plus** the session cookie.

- Re-run any tool that returned `not injectable` / `0 results` **once** against a real
  param URL with `--cookie`/`-H "Cookie: …"` before recording a NEGATIVE — otherwise you
  tested nothing. (This session's whole RE-RUN pass exists because the first pass aimed at roots.)
- A green verdict on a static page (e.g. race-checker "no race") is worse than an error — it
  impersonates coverage.
- Next.js / RSC / Server-Action targets: the action-replay recipe + the RSC-echo
  false-positive guard (query param echoed into flight payload ≠ LFI/SSTI/XSS) live in
  `references/server-action-replay.md`.

**⛔ RULE 2e: Payment / plan-entitlement testing has a hard fraud line**

When asked to "bypass Pro / fake the payment": test the **entitlement** class (is plan/price
client-trusted? do fabricated success-URLs flip the plan? is the webhook signature verified?),
and **refuse** the fraud class (completing a fake payment, forging a valid webhook to actually
grant entitlement). State the line once, then execute the allowed half. Recipe + safe test
matrix: `references/payment-entitlement-bypass.md`.

BUILD CHECK: `python tool_router.py` prints availability. Test routing WITHOUT running tools (inspect TOOL_PATHS + NUCLEI_TAG), because calling route_and_run actually launches sqlmap/nuclei (slow — will time out a quick test cell).

