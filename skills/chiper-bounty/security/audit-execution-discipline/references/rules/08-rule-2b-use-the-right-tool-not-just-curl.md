## ⛔ RULE 2b: Use the RIGHT tool — not just curl

> **The `execute_code` raw-HTTP disguise (operator caught twice, 2026-11-02).** Hand-rolling
> `http.client.HTTPSConnection` / `urllib.request` inside `execute_code` is **functionally
> identical to manual `curl`** — same one-request-at-a-time loop, same miss-everything-crawl coverage.
> The operator's standing rule is "curl = LAST RESORT" and it extends here: `execute_code` is for
> **triaging / decoding / diffing the tools' OUTPUT** (parse ffuf JSON, decode a MeesagePack LFI,
> MessagePack-unpack a ticket, compute a JWT claim) — **never for running the probes themselves.**
> When a target's policy says "automated tools prohibited", the correct move is still the real
> toolchain (`nuclei`/`ffuf`/`arjun`/`dalfox`/`ghauri`/`sqlmap`) with `-rl`/`--delay`/`-c 1..2` rate
> caps — NOT a hand-written `urllib` loop, which is the "balik cm curl aja" failure in a new costume.
> Symptom that gives it away: a long train of `call()` helpers + `http.client` + `ssl._create_unverified_context`
> that runs 30+ "probes" with no scanner artefact on disk. When you see yourself about to write that,
> stop and run the toolchain instead.

TOOL ROUTER (2026-09-26): `scripts/tool_router.py` centralizes class→tool routing. ALL payload/variant/technique executors (execute-variants, execute-references, execute-poc-techniques, execute-poc-variants, execute-business-logic) call `tool_router.route_and_run(class, target, out_dir, ...)` instead of raw urllib where a real tool exists. Verified disk mapping:

- sqli → sqlmap · xss → dalfox · cors → CORScanner · graphql → graphqlmap · race → race-checker.py
- cmdi/lfi/ssti/xxe/nosqli/open-redirect/auth-bypass/csrf/cache-poisoning/403-bypass/http-smuggling/file-upload/password-reset/idor → nuclei with per-class tag
- info-disclosure → gobuster dir · ssrf → interactsh OOB (needs request template; logged fuzz_only otherwise)
- Classes with NO CLI (ssrf/idor/waf-bypass/generic) → HTTP fallback, flagged `fuzz_only:true` in usage JSON — honest, not silent.

**Tool-list correction (older RULE 2b text was stale):** `dalfox <url>` is WRONG CLI (needs `dalfox url <url>`); CORScanner/ffuf reject `--headless`; SSRFmap needs `-r/-p`; graphqlmap needs `-u` + package on PYTHONPATH (py3.14 readline crash); justify, don't trust EXECUTED evidence alone.

**✅ FIXED 2026-09-29 in `scripts/force-full-execution.py` (live, synced to bundle-src).** Command construction is now tool-name driven with each CLI verified against its own `--help`, and statuses are honest:

| tool | correct invocation now emitted | notes |
|---|---|---|
| sqlmap | `-u "<param-url>" --batch --level=2 --risk=1 --threads=4 --timeout 15 --retries=1 --smart` | sqli class = `[arjun, sqlmap]` — arjun's param discovery runs FIRST; its evidence feeds `_param_url()` |
| arjun | `-u "<target>" -t 4 -d 1` | **pip tool, NOT `go install`** (`go install github.com/s0md3v/Arjun` fails: no Go package): `pip install arjun` → Scripts/arjun.exe v2.2.7. Hidden/backup param discovery; clean target → `No parameters were discovered.` |
| dalfox | `url "<target>" --skip-bav` | `url` subcommand REQUIRED |
| gobuster | `dir -u "<target>" -w <wordlist> --timeout 10s -t 5 -q` | `dir` subcommand REQUIRED |
| ffuf | `-u "<base>/FUZZ" -w <wordlist> -mc 200,204,301,302,307,401,403 -t 20 -s` | FUZZ keyword REQUIRED |
| nuclei | `-u "<target>" -silent -timeout 10 -t "<local>/http" -tags tech,exposure,misconfiguration` | local mirror pinned: `D:\data hermes\nuclei-templates` (13.7k yaml). **`-template-dir` is NOT a nuclei flag** (`flag provided but not defined`) — `-t` accepts template *directories* |
| CORScanner | `-u "<target>"` | no `--headless` |
| race-checker | `-u "<target>" --attempts 50` | |
| graphqlmap | `echo "dump_via_introspection" \| graphqlmap.bat -u "<target>"` | REPL → stdin; `.bat` fixed to cd + PYTHONPATH |
| kxss | `echo "<target>" \| kxss` | installed 2026-09-29: `go install github.com/Emoe/kxss@latest` → ~/go/bin/kxss.exe; reads URL from stdin |
| SSRFmap | skipped as `NEEDS_REQUEST_TEMPLATE` | needs `-r <reqfile> -p <param>`; interactsh OOB covers it |

Honest status vocabulary (a non-zero exit or a help/usage dump is NEVER "EXECUTED"):
`EXECUTED` · `RAN_WITH_ERROR` (tool really ran, then errored on the target — e.g. graphqlmap hitting a non-GraphQL endpoint) · `FAILED_USAGE` (usage/help text detected → never scanned, BLOCKS the gate) · `FAILED` · `NO_OUTPUT` (ran clean, 0 findings) · `FUZZ_ONLY` · `SKIP_NO_PARAM` · `NEEDS_REQUEST_TEMPLATE` · `STARTED_NO_TOKEN` · `SKIP_NO_URL_TARGET` · `SKIPPED_NO_SOLIDITY_TECH`.
`verify-tool-usage.py` CHECK 2b accepts this vocabulary: RAN statuses count as executed (evidence still required), FAILED_USAGE/FAILED block the report.

**Two more defects found during the 2026-09-29 end-to-end dry run:**
1. Tool discovery used `candidate.exists()` — on case-insensitive Windows `.../tools/graphqlmap` matched the DIRECTORY `GraphQLmap`, so exec got a directory. Fix: `exists() and is_file()`, plus the graphqlmap branch now falls back to `tools/graphqlmap.bat`.
2. The shipped zip did NOT contain `tool_router.py`, yet `execute-variants/-references/-poc-techniques/-poc-variants/-business-logic` all load `Path(__file__).parent/"tool_router.py"`. On a fresh machine every executor silently degraded to plain HTTP probes = the exact "curl only" symptom. `tool_router.py` is now bundled in `toolkit/scripts/`. Whenever you regenerate the zip, assert its presence.

3. **interactsh process leak.** The C1 interactsh block used `ip.terminate()`; six zombie `interactsh-client.exe` processes were found still LISTENING hours later on this Windows box. Fixed with a leak guard in `force-full-execution.py`: `taskkill /F /T /PID <pid>`, re-check `ip.poll()`, force tree-kill if still alive, and record `leak_guard` on the entry. Verified: 0 leftovers after the fix. After any audit, run `tasklist | grep -i interactsh` and clean up strays.
   **Positive control before you read any OOB negative.** Fire one request at the listener from your
   own box (`curl -s http://<payload-domain>/x`, or just resolve the hostname) and confirm the hit
   appears in the interactsh log *before* submitting the SSRF payload. Without that step, "no
   callback" cannot distinguish "the target never connected" from "my listener was never receiving" —
   and an SSRF negative is only evidence once the listener has demonstrably logged a hit. Same rule
   when the SSRF vector is a value you can only reach through a client-populated field: inject your
   own `<option>` into the live `<select>` via `evaluate`, select it, submit the app's real form, and
   require the OOB hit (2026-09 verified-negative: an MT4/MT5 "broker server" picker that resolves the
   submitted id through its own server table never emitted a DNS callback).

4. **Toolchain wiring for the C1 layer** (installed + wired 2026-09-29):
   - `arjun` is a **Python** CLI, not Go: `pip install arjun` → `Scripts/arjun.exe`.
     `go install github.com/s0md3v/Arjun@latest` FAILS ("does not contain package …Arjun") because the
     repo is a Python project with no go.mod — don't retry it.
   - `kxss` is Go: `go install github.com/Emoe/kxss@latest` → `~/go/bin/kxss.exe` (reads URLs on stdin).
   - `MANDATORY_TOOLS` is now `sqli: [arjun, sqlmap]` and `xss: [dalfox, kxss]`; arjun runs first so its
     evidence feeds `_param_url()` for the sqlmap step.
   - `_param_url()` picks the parameterized URL from, in order: the target itself, arjun's evidence file,
     `urls.txt`, `openapi.json` — same host only. No parameter anywhere ⇒ `SKIP_NO_PARAM` (honest),
     never a fabricated `?id=1`.
   - nuclei runs pinned to the local mirror: `-t "D:/data hermes/nuclei-templates/http" -tags
     tech,exposure,misconfiguration` (13,754 yaml, no remote cache needed). `-template-dir` does NOT
     exist as a nuclei flag — use `-t <dir>`.

