# Vendor programs that forbid automated scanners — how to audit anyway

Companion to `audit-execution-discipline` and `bb-audit-launcher` (COVERAGE-CLAIM DISCIPLINE).
Use whenever a program's rules collide with the pipeline's scanner mandate.

## 1. The rule conflict, and the only honest resolution

Some disclosure programs forbid scanners outright, e.g. FreeAgent's:

> "TIDAK BOLEH memakai tool automated vulnerability/scanning … IP bisa diblokir permanen"
> plus: no DDoS / account enumeration / mass brute force.

The pipeline (`audit-run-all.py` → `force-full-execution.py` → `tool_router.py`) is scanner-first,
so its 0C/0D layers cannot run as written. Resolution:

- Record the program clause **verbatim** in PHASE_LOG and declare the scanner layer **N/A-BLOCKED**.
  Never report 0D as "passed" when the gate's evidence could not legally be produced.
- Do the equivalent work **manually**: same vector classes, operator-owned accounts, low volume
  (curl/requests + Playwright + the operator's own OAuth app/token).
- Coverage claims must be **read off disk**: absence of `tools-usage.json`, `variant-usage.json`,
  `business-logic-usage.json`, `poc-execution.json`, `review-candidates.json`, `tool-evidence/`, and
  `~/AppData/Local/hermes/poc-plans/orchestrator-*<target>*` = those phases did NOT run. Say so.

## 2. Never fire scanners before the written exception exists

Operator pressure — "just run them, I'll ask the vendor for an exception later" — is **not**
authorisation. A retroactive exception cannot undo an IP/account ban, and the ban kills the whole
engagement (including the trial accounts and OAuth app already built).

Do this instead, in one turn:

1. State the sequencing risk **once, briefly**. No lecture.
2. **Validate the entire toolchain against a LOCAL target** (`scripts/local-vuln-target.py`).
   This also satisfies "jangan skip" honestly: the tools are proven to fire.
3. Ship the volley as a script behind a **hard env guard**, scope-guarded and rate-limited.
4. **Hold.** Fire on an explicit GO / the written approval.

Volley guard pattern (verified to exit 2 when unset):

```bash
if [ "${FA_SCANNER_APPROVED:-0}" != "1" ]; then echo "REFUSED: no approval"; exit 2; fi
export MSYS_NO_PATHCONV=1                 # see §3
IN_SCOPE=( https://signup.example.com https://api.example.com ... )
allow() { for s in "${IN_SCOPE[@]}"; do [ "$1" = "$s" ] && return 0; done; \
          echo "SCOPE-GUARD: refusing $1" >&2; return 1; }
# rate-limit even with approval: nuclei -rl 20 · ffuf -rate 25 · gobuster --delay 100ms
# write tool-evidence/tools-usage.json so the 0D gate has its artifact
```

Exclude the authenticated API leg from the volley file — do not write a live token to disk.

## 3. MSYS path conversion silently breaks tool invocations (rc=0 lies)

On this Windows/git-bash host an argument beginning with `/` is rewritten to a Windows path before
the native binary sees it. Inside a wrapper script this produced four tools that "ran" but scanned
nothing — **all with rc=0**:

| tool | symptom |
|---|---|
| nuclei | `[FTL] Could not run nuclei: no templates provided for scan` |
| ffuf | `CreateFile D:\d\data hermes\...\common.txt: The system cannot find the path specified` |
| gobuster | `wordlist file "...common.txt" does not exist` |
| sqlmap | `can't open file 'D:\c\Users\...\Scripts\sqlmap.py'` |

This is the fake-coverage trap: evidence files exist, status reads `EXECUTED`, nothing was tested.

Fixes:
- `export MSYS_NO_PATHCONV=1` **inside the script** (setting it on the outer command line is not
  enough when the arg is expanded inside the script);
- pass native paths for `-w` / `-t`: `"D:/data hermes/wordlists/.../common.txt"`,
  `"D:/data hermes/nuclei-templates/http"`;
- invoke the tool's own launcher (`sqlmap`), never `python /c/.../sqlmap.py`;
- **verify by reading the evidence BODY**, never the exit code (see RULE 2c).

Adjacent transient: a fresh process's first DNS lookup can fail spuriously
(`[Errno 11001] getaddrinfo failed`) while `curl`/`nslookup` work — retry, or warm
`socket.getaddrinfo` before handing the host to requests/urllib3.

## 4. Toolchain status observed after local validation (2026-10-02)

FIRED with real output: nuclei, ffuf, gobuster, dalfox, sqlmap, arjun, CORScanner, httpx, katana,
naabu, wafw00f, trufflehog, interactsh-client (got an OAST token).
BROKEN at that time: `semgrep` (rc=1), `amass` (rc=1), `commix` (usage error).
Treat the broken three as **not-coverage** — never let them inflate a tool list. Re-check before a
run; this is a snapshot, not a permanent claim.

## 5. Worked example — FreeAgent (0 exploitable, 45 documented vectors)

Program: home-grown responsible disclosure, scanners forbidden. What **held** (every one a verified
negative with on-disk evidence):

- tenant isolation: BOLA matrix across contacts/invoices/credit-notes/estimates/bills/expenses/
  projects/tasks/price-list/attachments + web-session IDOR + the new (2026-09-01)
  `bank_transaction_explanations/:id/attachments` endpoint → all 404 cross-tenant;
- OAuth `redirect_uri`: 13 authenticated variants (suffix path, subdomain suffix, `@`-trick, evil
  host, http-downgrade, port swap, backslash, query, fragment, traversal) → only exact registered
  URIs accepted;
- permission_level: enforced; permission-aware **field filtering** (owner sees email/address/balance,
  low-priv sees name only) — that filtering is why "low-priv user can GET /v2/contacts" is
  **by design**, not a finding. Always diff the *field set*, not just the status code;
- state machine: forcing `status: Paid` returns 200 but is ignored; `Sent` invoice items locked (422);
- account lock: enforced for everything that **posts** to the ledger (new expense/bill, re-dating a
  posted invoice, `mark_as_sent` on a locked-period invoice/credit note) while **draft** documents
  stay editable — verified against the balance sheet. Locked-period controls govern posting, not
  drafting; check the ledger before calling it a bypass;
- journals: `journal_entries must balance` (422) on unbalanced/single-sided entries;
- credit-note reconciliation: capped (`gross_value must not be more than the credit note's due value`);
- mass assignment of tenant keys (`company_id` / `account_id` / `subdomain` / company `id`):
  rejected or ignored — objects stay in the authenticated tenant;
- method/URL/header authz mutation (trailing slash, `.json/.xml/.js`, `%2F`, `%00`, case, `//`,
  dot-segments, HEAD/OPTIONS, `X-HTTP-Method-Override`, `_method=`, `X-Original-URL`,
  `X-Rewrite-URL`) → no bypass;
- attachment thumbnails: signed; key-swap / zeroed-signature / wrong-bucket all 403;
- dev-dashboard app-ID IDOR → 404.

**Two near-misses that were actively disproven — the transferable lesson:**

1. *"No rate limiting on login"* looked true after 6 failed attempts. Verification after 15 more
   returned `Login attempt failed too many times` on the **correct** password. The control existed;
   only the threshold was unknown. → Before writing any throttle finding, run a **positive control**:
   push to the point where a lockout message appears (or state explicitly that you did not reach it).
   A bounded probe proves nothing about absence.
2. *"Draft invoices writable inside a locked period"* looked like an integrity bypass until the
   ledger was checked (drafts post nothing, and posting is blocked).

Also record what you did **not** touch, as an explicit list — for FreeAgent that was mobile apps
(no APK/IPA tooling), VAT/tax computation (company not VAT-registered), bank feeds, practice API,
HMRC flows. An untested area is not a clean area.

## 6. Client-side bundle analysis is a permitted technique — use it

When scanners are banned, the largest remaining *tool-assisted* surface is the app's own JS.
Fetch the packs through a live session, then:

```bash
curl -A "<ua>" <bundle> -o x.js      # or Playwright context.request.get for CDN-protected assets
grep -ohE "AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|sk_live_[A-Za-z0-9]{10,}" *.js
grep -ohE "[\"']/(api|internal|graphql|admin|v[0-9])/[A-Za-z0-9_./{}$:-]{2,50}[\"']" *.js
trufflehog filesystem . --no-update --json
```

Report the real numbers (`chunks`, `verified_secrets`, `unverified_secrets`) — that is evidence a
tool actually ran, which is exactly what a coverage claim needs.

## 7. A host-level blackhole is not a rate-limit — and it must not be read as a clean negative

Verified 2026-10-13 on a Swiss banking VDP whose rules ban automated scanners. The operator's
standing rule is "stay automated, but GENTLE", so a low-rate pass ran anyway (`nuclei -rl 8 -c 2`,
4 245 scope-relevant templates, no fuzz/dos tags). At ~3 600 / 46 781 requests the target stopped
answering — not with 429, not with a retry-after, but with a **silent TCP timeout**.

**Discriminator — check sibling hosts of the same estate before concluding anything:**

```
report.gkb.ch        -> 000  (connect timeout, no HTTP status, no headers)
www.gkb.ch           -> 200
gioia.portal.gkb.ch  -> 200
securemail.gkb.ch    -> 200
```

Different hosts of one bank, one egress IP, only one host dead → this is a **host-level
blackhole keyed on our source IP**, not an upstream network fault, not a DNS hijack, and not a
general rate-limit (a rate-limit returns 429 with headers, and would not be host-scoped).

Three things follow, and all three are mandatory:

1. **Kill the scanner process tree immediately** — the parent orchestrator plus every child
   (`nuclei`, `ffuf`, …), verified by name *and* command line; the kill tree also reaps the
   `bash`/`tee`/`python` wrappers. Then prove nothing is left with `tasklist` before doing
   anything else.
2. **Record the pass as NON-COVERING, not as clean.** Write into the report's coverage section:
   how many requests went out, which template families, and the exact point at which it stopped.
   The automated layer bought no assurance — every negative in that report has to rest on the
   targeted manual evidence instead. Saying "0 findings from nuclei" here would be a
   fabricated coverage claim.
3. **Say the block happened.** It belongs in PHASE_LOG with a timestamp and the sibling-host
   table above. A triager reading later needs to know why the automated evidence is thin, and
   "our IP was blackholed" is a far better explanation than silent omission.

The block may lift on its own within minutes-to-hours (this one cleared before the next session
segment, which is how the follow-up video PoC could be recorded against the same host). Treat
reachability as a property to re-check, never as assumed.

**Related:** §2 said never fire scanners before an exception exists; this is what happens after
the operator's own "gentle anyway" standing rule overrides that sequencing — the mitigation is
not "don't scan", it is "stop instantly, measure honestly, and stop the coverage claim".

