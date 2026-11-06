---
name: codebase-bounty-review
author: RESEARCHER_NAME
description: "White-box bug-bounty review of a SOURCE-CODE target (GitHub repo / SDK / node / protocol codebase) where there is no live host to scan and the program forbids live testing. Use when the program's assets are repos (Immunefi Blockchain/DLT, OSS security programs) rather than websites/APIs. Adapts the 0A-0F phase model to the codebase track and integrates with bb-audit-launcher + audit-execution-discipline."
tags: [security, bug-bounty, audit, codebase, source-review, blockchain, immunefi]
metadata:
  hermes:
    version: 1.0.0
    tags: [security, bug-bounty, audit, codebase]
---

# Codebase Bounty Review (source-only track)

Companion to `bb-audit-launcher` (the 0A-0F orchestrator) for targets whose in-scope assets are
**source repositories**, not live hosts. Example trigger: "audit exploit <Immunefi program> whose
assets are GitHub repos". Load `bb-audit-launcher` **first** (rules + gate table), then this skill.

## PART 0 — Decide the track BEFORE any tool fires

Read the program text. Route:

| Program says | Track | 0C tool layer | 0D gate |
|---|---|---|---|
| assets = GitHub repos; "no testing on mainnet/testnet"; "local forks only" | **codebase (white-box)** | SAST + dependency scan + source review | **N/A** (no HTTP surface) |
| assets = live domains | web2 (normal launcher flow) | nuclei/ffuf/… | normal |
| assets = on-chain contracts | web3 (foundry/slither) | contract scanners | N/A / fork |
| **live hosts exist BUT `security.txt`/policy forbids automated scanning, AND the product source is public** (open-source SaaS with a hosted Cloud edition — carbon.ms 2026-10) | **hybrid: source track + passive-only recon** | **N/A** (quote the clause); CT / robots / llms / OpenAPI / `.well-known` only | `N/A (policy prohibits automated scanning — quoted)` |

**Third row, in detail:** the scanner layer is **N/A, never "passed"** — same HARD RULE as
row 1, with the *policy clause* as the reason instead of the absence of a host. Quote the
clause verbatim into the risk log once (see `recon-scope-triage` → "policy EXISTS but
PROHIBITS the method") and proceed on the source track without re-raising it each turn.
Passive enumeration (certspotter CT, `robots.txt`/`llms.txt`, `openapi.json`,
`.well-known/*`) is not automated scanning and stays in play — it is also how you find the
subdomain-per-vertical split that tells you where the tenant-isolation surfaces are.
Full recipe + the bug classes this track pays on:
`references/multi-tenant-cache-scope-review.md`.

**HARD RULE (same as the launcher's vendor rules):** if the program forbids live testing, the
scanner layer (nuclei/ffuf/gobuster/dalfox/sqlmap/subfinder/naabu/httpx/katana/gau/waybackurls/arjun/
trufflehog/subzy/…) is **N/A / NOT RUN** — never "passed". Say it in PHASE_LOG. Absence of a live
host is not a scanner result.

## PART 1 — Phase mapping (0A-0F, codebase track)

- **0A SCOPE** — parse the program page: assets (repo list), reward tiers, prohibited activities,
  impact definitions (these tell you WHICH bug classes pay). Write `SCOPE.md` + `PHASE_LOG.md`
  (`_progress`/target dir), phases 0A-0F. Note `engagement_type` = bug-bounty (impact-demonstrated).
- **0B RECON (code)** — clone every in-scope repo (`--depth 1`; big Java repos may fail Windows
  checkout → see pitfalls). Map modules (LOC, entry points, newest/most-security-relevant packages).
  Pull recent history (`git fetch --depth N`) — *newest commits = least-reviewed code*.
- **0C HUNT (white-box)** — see PART 2.
- **0D GATE** — **N/A** (mark `N/A-BLOCKED` / `N/A (codebase track)`; never "passed").
- **0E FINDINGS** — `findings.json` with `validated_findings[]` **and** `observations[]`, plus a
  **coverage ledger** of verified negatives. `PHASE_LOG.md` carries the ledger.
- **0F REPORT** — per-program format. Impact-first. PoC = code path + line refs (+ runtime PoC if
  feasible). One root cause = one report.

## PART 2 — The hunt: order of operations

1. **Automated layer (cheap, evidence-first)**
   - JS/TS: `npm audit --json` (needs package-lock). Note runtime vs dev deps.
   - Go: `govulncheck ./...` and `gosec -fmt=json -out=<WINPATH> ./...` (see pitfalls).
   - Java/Gradle: `./gradlew dependencies` / OWASP dependency-check if network allows.
   - Rust: `cargo audit`.
   - Secrets/dangerous-API sweep with **ripgrep** (not Python os.walk — too slow on big trees):
     `rg -n -i -e 'BEGIN [A-Z ]*PRIVATE KEY' -e '(private_?key|secret|api_?key|password)\s*[:=]\s*"[^"]{16,}"'`
     plus sinks: `exec(|child_process|eval(|innerHTML|unsafe {|Math.random|MD5|SHA1`.
2. **Triage the automated hits.** Most are noise (Go G115 integer conversions; test keys; TLS
   `InsecureSkipVerify` *followed by* a real `VerifyPeerCertificate`). Read the body before believing any
   finding.
3. **High-value manual review** — prioritise by the program's *paid impacts*, not by LOC:
   - verification / authz paths (signature checks, quorum, allowlists) → theft / "authorize without signer"
   - proof verification (SSZ / Merkle-Patricia / IAVL / RLP) → forgery
   - **newest features** (grep recent commits; `NEW == UNREVIEWED`)
   - **the target's own docs for self-declared open issues** — `ROADMAP.md`, `docs/bugs/`,
     `docs/superpowers/specs/`, and `TODO`/`FIXME`/`not supported yet` in security code. These name
     what the vendor itself considers unfinished, so a genuinely-still-open one is a high-quality
     lead *and* pre-empts "this is by design". **Verify the current status in code before you write
     it up** — such banners are often stale (observed 2026-10: "still open — active cfcheckpt
     rejection" was fully implemented by the target version, complete with task-numbered code and
     counters; the item was closed, not a finding). Language stubs with `TODO Phase N` for a whole
     feature set (e.g. a rules engine) are usually *guarded* elsewhere — find the guard (a
     fail-closed gate that only lets the safe case through) before treating the stub as the bug.
   - stubs in security code: `rg -i -e 'fake|stub|placeholder|temporary|accepts (every|any)|return true;|not implemented|TODO' <security dirs>`
   - money paths (fees, staking, bridge/messages, balances)
   - **Soroban/Stellar + generic Rust contracts** — the five defect classes that paid in practice
     (caller-supplied argument, no-op verification, missing `require_auth`/`assert_admin`,
     fail-open guards, client-controlled identity) and the `cargo test` + `vitest` runtime-PoC
     recipe live in `references/soroban-stellar-review.md`.
4. **Confirm the isolated-defect pattern.** A strong finding is often *one* code path that skips a
   control the rest of the codebase enforces. Prove the contrast (e.g. peer verifier X does real crypto,
   the audited one does not) — it pre-empts "this is by design".
4b. **A bounded traversal that ends SILENTLY is a fail-open control — and it pays.** Whenever a security
   decision is made by *walking* attacker-influenced structure (metadata, manifest, JSON-in-string,
   headers, ACL list), find the walk's budget and ask what happens when it is exhausted. The safe shape
   is a REFUSAL; the paying shape is `return` inside the walk with no signal to the caller. Then the
   attacker simply puts the payload past the bound.
   - Hunt the constants: `rg -n 'MAX_(NODES|DEPTH|ITEMS|ENTRIES|KEYS|SIZE)|maxDepth|maxNodes|slice\(0,|\.length > [0-9]{2,}' <security dirs>`
   - The tell is **an asymmetric guard**: a bounded *walk* feeding a *whole-document* decision. Depth
     alone is usually fine; a node/width cap on a document the attacker can pad is not.
   - Watch for the control that still passes and hides the bug: a flat-field scan (`Object.entries` at the
     top level) blocks the naive payload, so the first PoC you write "works" and the bound looks
     irrelevant. Park the payload **nested, past the cap** — that is the case the flat scan cannot see.
   - Worked case (bWallet 2026-10, validated): `src/mobile/market/safety.ts` walks inscription metadata to
     500 nodes then stops. Flat `nsfw:true` is caught by a separate top-level scan, so the bypass needs
     `{attributes:[{trait:v0}×400, {nsfw:true}]}` (801 nodes) → `check()` returns `blocked:false`.
     3/3 runs, with controls (flat flag, depth-3 flag, 20k JSON-string path) passing — the controls are
     what make the report credible.
   - Same shape elsewhere: `parseJsonish` length caps, "first N items" allowlists, pagination guards,
     `MAX_*` in a recursive `walk`, and any `catch {}` around a verification walk.
   - The evidence that lands: PoC importing the REAL module (`bun run poc.ts`), the observed
     blocked/expected table, AND the same assertions dropped into the repo's own test tree so the
     maintainer sees `1 pass / 2 fail` with their own runner. Then REMOVE your file from their tree and
     show `git status` clean.
   - Cite the sibling: if the file's own docstring records a previous fix of the same class ("nesting
     deeper than the old walk hid terms"), the width variant is the *same defect unfixed*, and quoting
     their sentence kills "by design" on arrival.
4c. **Check the guard is on the RIGHT SEAM — enumerate what the kill switch actually wraps.** A global
   safety control (spending pause, kill switch, rate cap, feature freeze) is usually implemented as a
   wrapper around one or two API methods. Every money/signing path that reaches the wallet by a *different*
   method silently escapes it. Measured 2026-10 (bWallet): `guardSpending()` wrapped exactly `createAction`
   and `signAction`, while ten money paths signed directly with `createSignature({hashToDirectlySign})` —
   Memepool sells, escrow, launchpad tokens, four partnership/placement paths, btrust, issuer keys. The
   project's own `docs/MONEY-GUARD.md` promised the switch pauses "one feature in every shipped copy".
   - Find the wrapper: `rg -n "for \(const method of \[|guard\w+\(|assertNotPaused|KILL_FEATURES"` then read
     which method names it loops over.
   - Then invert: `rg -n "hashToDirectlySign|createSignature\(|signTransaction|sendRaw"` and diff the two
     sets. Every signing call site NOT in the wrapped set is a candidate.
   - Report it as **one root cause** (guard on the wrong seam), not N findings — and if an earlier report
     already filed one instance, list the others as impact amplification rather than minting a duplicate.
5. **On multi-tenant / RLS-backed targets, sweep the tenant-boundary code FIRST** — auth,
   claims/permissions, session and their caches — before module logic. The paying shape there is
   a *cache or memo key missing a dimension its value depends on* (user-only key holding a
   company-scoped value), because a stale value crosses the tenant boundary. Checklist, related
   shapes and the candidate-vs-filing gate:
   `references/multi-tenant-cache-scope-review.md`.

## PART 2b — Mature / heavily-audited protocols: find the UNAUDITED surface first

If the target already carries a dozen+ audits and a long Known-Issues list (common for DeFi
lending / prime-broker / L1 protocols), do NOT read the code blind — run audit-coverage gap analysis
first, or you will burn the budget on already-covered ground and re-report known issues.

1. **`SECURITY.md` is the door** (a protocol site's `/security` page links to it; pull it raw from
   `raw.githubusercontent.com`). It holds scope, tiers, the **complete Known-Issues list** (= your
   dedup map), and the **Credits** section (= the bug classes they actually pay for).
2. **Map audit PDFs → modules** (`audits/*.pdf`, extract with `pypdf`, count module keywords). Zero
   hits = unaudited = highest value.
3. **NEW == UNREVIEWED.** `git fetch --unshallow` (depth-1 hides history), then
   `git diff --stat <last-audit-tag>..HEAD -- <src>` and `git log --oneline -60`. Rank modules by
   insertions since the last audit; the bullseye is *large insertion count AND no audit-keyword hit*.
   Read commit subjects for recently-*fixed* bug classes — hunt their siblings.
4. **Known-Issues list = auto-reject list.** Grep each candidate against it (and the audit text)
   before writing up. "Accepted approximation" / "by design" doc-comments are defences, not docs.
5. **On a RESUMED target, inventory the prior output first — LOCAL workspace AND the mail Drafts folder.**
   Local: `report/`, `drafts/`, `findings.json`, `STATUS.md`. Remote: list the drafts folder
   (`[Gmail]/Draf`) for the program's subject prefix. Both define your dedup map, and the mailbox version
   is the one that knows which findings were already *written up* but not yet sent.
   Observed 2026-10 (bWallet b-Aware): six prior drafts sat in the folder whose subjects named the lifted
   classes — pre-ticked "remember" storing a 90-day allowance, Memepool sells bypassing the spending kill
   switch, stranded buy funding, a self-attested proof-of-reserves gate, unverified paymail destination.
   Twenty minutes of reading those subjects redirected the hunt away from four already-filed bug classes and
   toward the untouched one. Two hard rules that came with it:
   - **Verify a prior finding against HEAD before calling it stale.** One of them looked old; checking the
     code showed it was still true (`guardSpending()` wraps only `createAction`/`signAction`, while the sell
     path signs via `createSignature`). Do not re-file it — cite it as amplification if the new evidence
     widens its reach.
   - **Never delete drafts by subject prefix.** The prefix is shared by every finding for that program;
     delete by the uid of your own copy (detail in `email-automation`). Observed 2026-10 (DigiByte wallet): the workspace held
   nine already-reported findings (`b_F1..b_F9` + staged drafts) from a prior session; reading their
   one-paragraph summaries first defined both the dedup map AND the bug classes already taken
   (all nine sat in the asset-metadata/credit-path space), which is what pointed the new hunt at
   the untouched classes (coin-selector/signing path, M3 parent-walk, seed handling). Ten minutes
   of `ls report/ && head` beats re-deriving a duplicate.
5. Confirm the **deployed** version before claiming on-chain impact — release/pre-release scope wording
   is in `SECURITY.md`.

Full recipe, commands and pitfalls: `references/audit-coverage-gap-analysis.md`.

## PART 2c — A control wrapped around NAMED METHODS is only as wide as that list

The fourth defect class that pays, alongside no-op verification, caller-supplied data, and fail-open
guards: **a guard installed by wrapping a method-name allowlist, while other paths reach the same
primitive directly.**

Worked case (bWallet 2026-10, already filed as L4-C1 — use as the template, do not re-report it):
the operator-facing "stop spending" kill switch is implemented as

```ts
for (const method of ['createAction', 'signAction'] as const) {
  w[method] = async (...a) => { await assertNotPaused('spending'); return original.apply(w, a); };
}
```

Anything that signs without those two methods never reaches the guard. Ten money paths in that tree
sign with `createSignature({ hashToDirectlySign })` directly — token escrow, launchpad tokens, four
partnership/multisig paths, btrust, chat issuer keys, the Memepool sell — so the switch covers
`createAction`-based sends only, while `docs/MONEY-GUARD.md` promises it pauses the feature "in every
shipped copy of the wallet".

### The hunt
1. Find the guard: `rg -n "\[\s*'[a-zA-Z]+'\s*,\s*'[a-zA-Z]+'\s*\]" src | grep -i "guard|wrap|pause"`,
   plus any `Object.assign(Object.create(wallet), { … })` / `guardSpending` / `guardAllowance` shape.
2. Read the wrapped method list, then enumerate the primitive it guards (`createAction`,
   `signAction`, `internalizeAction`, `broadcast`).
3. Grep for every other route to that primitive: `rg -n "createSignature|hashToDirectlySign|signActionBytes|Transaction.fromBinary" src`
   and list each file.
4. For each hit ask: **does this path reach the guarded method, or does it stop one layer below?**
   A path that builds the tx locally and signs a digest never touches `createAction`.

### Severity and filing discipline
- The bypass is real but usually needs the specific feature (here: a token sell), so map it to the
  program's own impact wording — bWallet calls it "bypass an approval or permission" / funds at risk.
- **One root cause, one report.** All ten paths share "guard placed on the wrong seam". File the
  strongest one and add the rest as an impact-amplification section or a note to the operator — do not
  mint nine duplicates. Say explicitly in the report that the list is exhaustive, because a triager
  reading one path will otherwise assume it is a single-endpoint oversight.
- Fix framing: move the check below the seam (into the signing primitive or the wallet's key-use
  layer), not into each caller. A caller-side check leaves the next caller to reintroduce the hole.

## PART 2d — Live-blocked → source-review pivot (GitHub org recon)

When a live web engagement hits an authentication wall (Turnstile/reCAPTCHA on every signup
channel, no registration endpoint, all interesting endpoints behind ROLE_USER), do NOT stop at
"needs auth, can't test". Pivot to **source review via the target's public GitHub org** — this
is a hybrid of the codebase track and the live track, and it finds real bugs.

### The pivot workflow

1. **Find the org.** The target's schema.org / JSON-LD, footer, or `sameAs` links often name the
   GitHub org (`https://github.com/<org>`). Enumerate repos:
   `curl -s "https://api.github.com/users/<org>/repos?per_page=100"`.
2. **Match the deployed version.** Compare live build asset hashes against repo files:
   - Live: `curl -s https://<host>/login | grep -oP 'href="/build/[^"]*"'`
   - Repo: `public/build/<same-hash>.css` in the tree API
   - **Identical hashes = the deployed PHP/app code matches the repo.** This is what makes a
     source-only finding load-bearing for a live host.
3. **Read the security-critical files first** (in order):
   - `config/packages/security.yaml` — firewalls, access_control, PUBLIC_ACCESS routes
   - `src/Controller/WebHookController.php` (or equivalent) — webhook/SSRF handlers
   - `src/Security/` — authenticators, token generators
   - `src/Controller/*Controller.php` — look for missing ownership checks (`// TODO Permissions`)
   - `.env`, `docker-compose.yml`, `src/DataFixtures/` — default creds, test tokens
4. **Confirm the route exists live** even without a valid token/account:
   - `GET /webhook/test` → **405** proves the route matched and is public (router rejects method
     BEFORE auth). A 302-to-login would mean auth is required.
   - `POST /webhook/invalid` → **404** proves the ParamConverter ran and failed (entity lookup).
   - `GET /project/1/edit` → **302 to /login** proves the route exists but requires auth.
5. **Report with three-layer evidence:** source code + live endpoint behavior + version match.
   Provide a ready-to-run PoC script the vendor can execute with their own token/account.

### Framework patterns that block live PoC (document, don't fake)

- **Symfony ParamConverter**: `public function index(Project $project, ...)` with
  `@Route("/webhook/{token}")` resolves the entity BEFORE the method body. Invalid token → 404
  → the SSRF/vuln code never executes. You cannot bypass this without a valid entity.
- **Token entropy**: `base64_encode(random_bytes(64))` = 86 chars, CSPRNG, not brute-forceable.
  Say this explicitly in the report so the triager knows you assessed it.
- **nginx path normalization**: `/js/../project/1/edit` is normalized to `/project/1/edit`
  BEFORE the firewall check, so dev-firewall bypass (`security: false` for `/js/`, `/css/`)
  does not work. `/index.php/<route>` DOES match routes but does not bypass auth or the
  ParamConverter.

### Scope re-validation BEFORE staging (user directive, 2026-10-26)

The user rejected TWO findings as OOS in one session:
1. Username enumeration on an unauthenticated form — the bounty explicitly excludes
   "username enumeration on public sign-up or password-reset flows".
2. Type juggling → 500 error — not in the "what we pay for" list, arguably "denial of service".

**Rule: re-read the bounty's "What we do NOT pay for" list clause-by-clause before staging
any draft.** Map each finding against every exclusion. If a finding is borderline, say so to
the user BEFORE staging — do not let them discover it after the vendor rejects it. A rejected
OOS report damages reputation and risks a program ban.

**User challenge pattern:** when the user asks "km yakin ini gk oos? tp inscope?" — they are
telling you the finding is weak. Re-read the scope, be honest about the gap, and either find a
stronger angle or say plainly it won't qualify.

## PART 2e — Web2 auth-server / account-lifecycle review (FastAPI, Django, Express, Rails…)

When the in-scope repo is a **server application with an account system** (not a contract, not a
native client), the paying bug classes live in the account lifecycle, not in the crypto. Map the
lifecycle first — register → verify → login → 2FA → password-reset → device/session management —
then read each transition for the state the previous step left behind.

**⚠️ Account pre-hijacking is NOT a standalone finding — gate it before filing.** The primitive
(register the victim's email first so YOUR password persists; the victim's own re-registration only
resends the code, keeping your password) only pays when the victim **cannot escape**. In DedSec CCTV
1.0.3 the sign-up code screen carries a "change email" option, so the victim just switches address and
your pre-registered account never becomes theirs — the operator explicitly rejected this exact
"validated 3/3 High" report (2026-11): *"victimnya bisa ganti email saat daftar, jangan sebut ini lagi"*.
Gate: can the victim change/abandon the address (change-email path, recovery, or simply not finishing
sign-up) without loss? If yes → drop it; it fails the "why doesn't the victim take the easy way out"
test. It only wins when email is a hard, unchangeable identity with no change path and no recovery.
(Reference for the underlying mechanics only, NOT as a paid case:
`references/auth-server-account-lifecycle-review.md`.)

Checklist for every registration/verification pair:
- Does re-registration of an unverified account **update the password**, or silently keep the first
  caller's? The code comment often confesses it ("resend; password is NOT changed") — quote it.
- Is there any state that the victim's own normal action activates on the attacker's behalf?
- Does the takeover survive a password reset? (Check whether reset clears 2FA / device binding — if
  not, the victim cannot self-recover and severity rises.)
- Is there a **disable path for every enable path**? A 2FA method with no disable endpoint turns any
  account-takeover primitive into a permanent lockout — say so in the impact.

**Validate against a self-hosted copy, never the official API.** A program whose SECURITY.md says
"test only against your own account or a self-hosted copy" means the PoC harness runs locally. For a
Python/FastAPI target the harness is cheap — recipe (env-before-import, TestClient, memory email
backend, isolated SQLite per run, limiter reset, isolating the logic bug from the device lock) is in
the same reference file.

**Read the shipped reverse-proxy config before claiming a rate-limit / XFF bypass.** Self-hostable
projects usually ship a `deploy/Caddyfile.example` / nginx conf. DedSec CCTV's Caddyfile does
`header_up X-Forwarded-For {client_ip}` — it OVERWRITES rather than appends, so a client-supplied
XFF cannot spoof the per-IP limit and the "bypass" lead is dead on arrival. One `cat` saves a
rejected report.

## PART 3 — Finding quality bar (what makes it pay)

- **Impact-first**, mapped to a named in-scope impact tier.
- **Reachability**: gated behind a feature flag / privileged account? Say so and pre-empt the program's
  own downgrade clauses ("Functionality Not Active in Production", "privileged account"). Downgrade
  yourself honestly rather than overclaim; the program text says non-active bugs are still encouraged.
- **Code = proof** for "verification is a no-op" bugs: cite the exact `return true;` line and every
  call site. A runtime PoC is often cheap even in a 300 MB repo — don't assume you must build the whole
  project: **isolated-compile** the *verbatim* production class(es) with `javac` and a shim for any
  missing annotation, then drive them from a tiny `Main`. Recipe + worked case:
  `references/isolated-compile-poc.md`; skeleton: `templates/IsolatedPocMain.java`.
- **Ship two PoC forms:** the isolated harness for YOUR evidence (`evidence/<name>-run.txt`), and a
  JUnit test dropped into the repo's own test tree for the MAINTAINER to run with their build.
- **Verified negatives are deliverables** — list them; "not tested" ≠ "clean".
  ⛔ **User directive (2026-10-17, DigiByte wallet review): "tidak ada namanya clean code clean
  project, pasti ada celah" + "kerjakan perlahan2, pakai semua tools secara maksimal, jgn terburu2
  mengambil keputusan".** Never present a reviewed module as a conclusion — the honest shape is
  "module X reviewed & verified sound THIS round; remaining queue: Y, Z". A hardened codebase
  (reference-cited comments, KAT parity tests, documented fix waves) means the gap is in the
  layers where tests are thinner or logic spans components — say that, and keep the queue visible.
  During multi-turn reviews, report progress after each chunk ("jgn diam aja"): what was read,
  what was verified, what is queued. Rushing to "sound/clean" on a bounty target is the one
  framing the user has explicitly banned.

## PART 4 — Pitfalls (learned)

- **Running a target repo's own pytest on this host can die in plugin autoload** — an installed
  plugin's entry point imports a missing dependency (observed: `anchorpy` → `ModuleNotFoundError:
  No module named 'pytest_xprocess'`), and the whole run aborts before collecting a single test.
  Fix: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest … -p no:cacheprovider`. The suite then
  runs normally — use it as the baseline proving the target behaves as the code reads before you
  claim a PoC exploits a gap the tests do not cover.
- **Write a repo PoC as a pytest test in the repo's own `tests/` tree, NOT a standalone script.**
  A standalone `python harness.py` doing `from app.main import app` dies with
  `ModuleNotFoundError: No module named 'app'` (sys.path[0] = the *script's* dir, not the repo), and
  on this host a stray `argparse` 1.4.x in `Python314/Lib/site-packages/argparse.py` shadows stdlib
  argparse, breaking pytest (`allow_abbrev`) and pydantic_settings (`BooleanOptionalAction`) for a
  `subprocess.run` spawned from `execute_code`. Fix: drop the harness into `tests/test_poc_<name>.py`,
  reuse the repo's OWN `client` + email-`outbox` fixtures (its conftest already sets
  ENVIRONMENT/DATABASE_URL/EMAIL_BACKEND and calls `limiter.reset()`), and run it through the
  **terminal** tool with the exact invocation the repo suite already passes:
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/test_poc_<name>.py -q -s -p no:cacheprovider`.
  Green on a fresh target is your baseline; the `-s` shows the `print(...)` evidence lines (e.g. the
  attacker-login token) so the transcript is the proof, not just the assertion.
- **`execute_code` and the terminal have DIFFERENT working directories.** A file written by
  `execute_code` with a relative path lands relative to ITS cwd, not the git-bash cwd the terminal
  `cd`'d into — and git-bash `/tmp` is `%TEMP%`, which native Windows Python may resolve elsewhere.
  Symptom: `python: can't open file '…/poc.py'` for a file you just "wrote". Fix: write every PoC /
  report script to an ABSOLUTE Windows path (`C:/Users/.../<target>/poc.py`) and run it from there.
- **Verify a surface EXISTS before calling it "remaining" — and before calling it untestable.**
  Two self-inflicted errors in one engagement (2026-10, nym-vpn-client), both erring in the
  direction of *understating* coverage:
  - The agent listed a crate called `nym-exports` as "still unexamined". **No such crate existed** —
    the name was generated from memory. Enumerate what is really there (`ls -d */` at the cargo
    workspace root, `find <dir> -name '*.rs'`) before writing any remaining/untested list.
  - The agent reported the Windows firewall as an "opaque native lib, not verifiable from source".
    The C++ source was **in the repo** at a sibling path (`nym-vpn-windows/winfw/`), so the "honest
    gap" was testable — and closed as a PASS in one pass once found.
  Rules: (1) never name a surface from memory — list the real paths first; (2) before declaring
  FFI/native code unreviewable, hunt its source: sibling top-level dirs, `.cpp`/`.h`/`.vcxproj`/
  `CMakeLists.txt`, and `build.rs` link lines (`println!("cargo:rustc-link-lib=…")` names the lib and
  usually points at its source dir); (3) if the native component is third-party-derived, say so and
  name the upstream — `winfw` is a **Mullvad** WFP fork (`mullvadguids.cpp`, `mullvadobjects.cpp`),
  which changes the prior from "unaudited" to "a widely-deployed kill switch with its own audit
  history"; (4) **when you discover a mislabel, retract it explicitly** in the deliverable and the
  PHASE_LOG — a false "untested" line is a false negative the next session inherits (and a false
  "tested" line is worse).

- **MSYS path trap (Windows):** with `MSYS_NO_PATHCONV=1`, native tools (rg/gosec/go) receive `/d/...`
  unmodified and fail ("cannot find path"). Pass **Windows** paths (`D:/data/...`) to native tools;
  pure/bash-builtins accept `/d/...`. `gosec -out=/d/...` silently fails to save → use `-out=D:/...`.
- **Huge Java repo checkout fails on Windows** (long paths): `git config core.longpaths true` then
  `git restore --source=HEAD :/`. rc=128 with "Clone succeeded, but checkout failed" is recoverable.
- **`delegate_task` for source review is unreliable here** — 600 s timeout, work discarded. Do the
  review directly.
- **Python os.walk sweeps on 300 MB repos time out** under Defender — use ripgrep, or run in background.
- **gosec on a whole Go repo compiles every `examples/` package → very slow.** Scope it:
  `gosec … ./sdk/...` with `-exclude-dir=examples,tck`.
- **Don't report dependency CVEs as findings** without a reachable impact on the in-scope asset.
- **A single very long heredoc/command gets truncated by the command channel.** Writing a long
  report or PoC file as one `cat > f <<'EOF' … EOF` fails with a bare shell parse error
  (`unexpected EOF while looking for matching \`''\`) and **nothing executes** — not even an
  earlier `mkdir` in the same `&&` chain, because the parse fails before the first command runs.
  Chunk it: several `cat > f <<'EOF'` / `cat >> f <<'EOF'` appends, or write the body as separate
  per-file pieces and let a small script assemble them. Keep each chunk to a few KB. A bare parse
  error (not a tool error) on a long write is this, every time.
- **The same size limit bites every WRITE path, not just the heredoc.** A tool call whose *arguments*
  are very large — a single `write_file`/`patch` carrying a whole multi-KB document, or a big
  `file_content` blob — can stall the request stream so the call never lands at all (observed
  2026-10: one oversized write "timed out before it could be delivered"; nothing changed on disk).
  Split the work: create the file small, then append in several `patch`/`write_file` calls, each
  comfortably under ~8K tokens of arguments. A stalled/undelivered call is silent — verify the file
  exists and grew afterward rather than assuming the write happened.
- **A value that reads back as `***` was redacted by the output layer, not corrupted in the file.**
  When a source constant or env-shaped value in tool output shows `***`, do not conclude the source
  is malformed or "empty" — it is the harness redacting it. Read around it (surrounding lines,
  call-site usage) and reason from that; only treat it as a real value if the behaviour contradicts
  it.
- **Java/Gradle: use the repo's exact JDK.** Read `gradle/toolchain-versions.properties` (e.g.
  `jdk=25.0.2`). A wrong JDK fails the buildSrc/convention plugin (JDK 21 rejects the unnamed-variable
  `_`, a JDK 22+ feature). Install that JDK and pass `-Dorg.gradle.java.home=<jdk-dir>`.
- **Gradle user home must share a drive with the project (Windows).** A split-drive checkout
  (project on `D:`, `~/.gradle` on `C:`) dies in the PBJ compiler with
  `IllegalArgumentException: 'other' has different root` (`Path.relativize` across roots, because the
  plugin adds classpath jars to the source-root set). Fix: put `GRADLE_USER_HOME` on the same drive as
  the repo (copy the cache there). Directory junctions/symlinks do NOT help — Gradle canonicalises the
  project path back to its real drive.
- **Get the real Gradle project path from `./gradlew projects`.** hiero names projects by artifact
  (`:app-service-clpr-impl`), not by directory (`:hedera-node:hedera-clpr-service-impl`).
- **Runtime > static when the finding is "X returns true".** Write a JUnit test that drives the REAL
  production path end-to-end (here `verifyBundle(...)` → `VerifiedBundle`) and run it with the node's
  own test task; cite the JUnit XML (`tests=N failures=0`) as evidence. Standalone harnesses over
  copies of production classes are a weaker, secondary proof.
- **Rust/Soroban PoC: crate dir != package name for `-p`.** Directories are snake_case
  (`zk_credit_verifier`), packages hyphenated (`zk-credit-verifier`). `cargo test -p zk_credit_verifier`
  dies with `package ID specification ... did not match any packages; help: a package with a similar
  name exists: zk-credit-verifier`. Read `[package] name` from the crate's `Cargo.toml`.
- **First Rust test build of a fresh workspace is slow (~2–8 min).** Run it with
  `background=true, notify_on_complete=true`; later `cargo test -p <crate>` runs reuse the cache in seconds.
- **Next.js/TS PoC: assert by KEY PRESENCE, not `JSON.stringify`.** `JSON.stringify(call.args)` on a
  Drizzle `set({...})` throws `TypeError: Converting circular structure to JSON` (PgTable/PgUUID close a
  cycle). Use `"totalLiquidity" in c.args[0]`.
- **The target's OWN tests are corroboration gold.** Repo tests frequently encode the insecure behaviour
  (`__tests__/api/cron/liquidation.test.ts:88` "runs without auth when CRON_SECRET is unset";
  `__tests__/api/kyc/webhook.test.ts:196` "accepts ... when no webhook secret is configured"). Cite the
  line numbers — it pre-empts "this is by design". Full recipes: `references/source-only-poc-harness.md`.

## PART 4b — Multi-language stacks: Rust/Soroban + Next.js APIs

DeFi repos often ship a `contracts/*` Soroban workspace **plus** a Next.js `app/api/*` surface.
Two extra layers pay off; full recipe + worked example in
`references/rust-soroban-and-nextjs-codebase-review.md`.

**Runtime PoC for Rust/Soroban (real evidence, cheap):** drop a `#[test]` into the crate's own
`src/test.rs` (already declared `mod test;`) and run it with the project's toolchain.
- **`-p` takes the Cargo PACKAGE name — NEVER guess it from the directory or from a rule of thumb.**
  Hyphenation is per-crate and inconsistent inside one workspace: `contracts/zk_credit_verifier` is
  package `zk-credit-verifier`, but `contracts/usdc_lending_pool` is package `usdc_lending_pool`
  (underscore!). Both mistakes look identical: `package ID specification … did not match any packages`.
  Read `name =` from that crate's `Cargo.toml` (or take the cargo error's own suggestion) before running.
- The first `soroban-sdk` build compiles ~200 crates ≈ 4 min → run in **background with notify**;
  a 600 s foreground call times out mid-compile.
- `env.mock_all_auths()` in the harness mocks `require_auth`, so a passing PoC proves the *logic*
  (a fabricated argument is accepted), not the auth layer — say so honestly.
- The repo's OWN test suite is evidence: a test that asserts the insecure behaviour (e.g. an arbitrary
  caller receiving a payout) is a ready-made finding — cite it beside your PoC.

**Soroban contract bug-class checklist (order of value):**
1. `caller.require_auth()` present but `assert_admin`/`assert_multisig_admin` **absent** on money fns.
2. Invariants evaluated over **caller-supplied arguments** instead of stored state (collateral entries,
   `yield_amount`, `bid_amount`, score/tier).
3. **"Verification is a no-op"**: a comment claims crypto (proof/signature) validation, the body only
   checks length / non-zero bytes, and the fetched provider key is unused (`_pubkey_hash`).
4. Cross-contract reward/payout fns must pin the caller to the expected contract
   (`if caller != lending { return 0 }`) — flag the ones that don't transfer from the contract balance.
5. `if (secret) { check }` guards that **fail open** when the env var is unset.

**Next.js API white-box checklist:**
- Per-route auth-guard matrix: grep each `app/api/**/route.ts` for
  `requireApiAdmin|requireApiUser|requireTradeVaultAdmin|...` and hunt the odd route out
  (e.g. a `requireAuthenticatedUser` where siblings use `requireApiAdmin`).
- Webhook signature verification wrapped as `if (header) {...} else if (!isTestnet) reject` ⇒ logic is
  effectively closed when the deployment's passphrase includes "Test" → attackers just omit the header.
- HMAC verifiers that `return true` when the secret env var is missing.
- Unauthenticated POST routes whose handler builds+signs a transaction with a server key
  (`Keypair.fromSecret(ADMIN_SECRET_KEY)`) — check whether that key is ALSO the on-chain contract admin.
- Rate limiters that trust `x-forwarded-for` / `x-real-ip` and fail open when the shared store is down.

- **Cargo package names are hyphenated, not the directory name.** `contracts/zk_credit_verifier` is
  package `zk-credit-verifier`; `cargo test -p zk_credit_verifier` fails with "did not match any
  packages". Use the hyphenated name (or read the crate's `Cargo.toml` `name`).
- **First Soroban build is slow (~4–8 min compiling `soroban-env-host`).** A foreground `cargo test`
  trips the 600 s tool timeout mid-build. Launch `background=true, notify_on_complete=true`, then
  `process(action=wait)`; subsequent runs are seconds.
- **`npm ci` on a large Next.js repo can take ~8 min.** Background it. Targets usually ship a
  `__tests__/helpers/fake-db.ts` chainable DB stub + `vitest.config.ts` — reuse them for API PoCs
  rather than hand-rolling mocks. Mock any module that imports `"use client"` browser-only code
  (e.g. a Stellar wallet kit) so the route imports cleanly under the node vitest env.

## PART 4b — Validation & delivery order (user-mandated)

On a source-only review the user requires this order — do not jump straight to a report:

1. **Validate first.** Re-read every finding from disk (never from memory) and re-run its PoC
   (`cargo test` / `npx vitest`) before claiming anything. Re-run the crate's FULL suite to prove the
   added PoC breaks nothing (e.g. `cargo test -p lending` → 108/108 + proptest).
2. **Then draft + complete PoC.** Produce the disclosure draft (external artifact: **English, with a
   short introduction** — name/context/channel) and a *runnable* PoC per finding, dropped into the
   repo's own test tree (Rust `src/test.rs`, JS `__tests__/`) **plus** a copy under `_audit/pocs/`.
3. **Hand over for MANUAL user check** before any submission. Do NOT send or place in Gmail Drafts
   until the user says GO.
4. **Only then continue hunting** other surfaces.

Honesty bar: label runtime-validated findings `validated-runtime`, code-only ones `code-verified`;
where the target's own tests *intend* a fail-open as "dev mode", say so and still report it (note the
missing `NODE_ENV` guard) — don't inflate, don't drop.

## PART 5 — Integration

- Start with `bb-audit-launcher` (rules, stop-rules, coverage-claim gate); this skill supplies the
  codebase-track adaptation only.
- Execution rules: `audit-execution-discipline` (verify from disk, not from memory).
- Reporting: `bug-report-delivery` / `report-writing`; for Immunefi use the program's impact table.
- Delivery to email draft (if asked): see the operator's `~/check_basabasi_email.py` for IMAP creds;
  APPEND to `[Gmail]/Draf` (draft folder), never send. The full draft workflow (locale folder, X-Unsent,
  verify-by-refetch, load-secret-at-runtime) is in the `email-automation` skill — load it instead of
  re-deriving it.

## PART 6 — Report hygiene & claim discipline (user-mandated)

Direct user corrections from a real engagement — a report that violates these loses credibility with the
triager, regardless of how good the finding is.

- **Never claim a result you did not execute.** If you added a test/script but did not run it, say exactly
  that and label the outcome *expected*, not *observed*. "Test PASSES on current source" while the build was
  never run is a self-contradiction — and it directly contradicts the coverage section that says "no build
  was run". The triager checks this.
- **Keep the whole document internally consistent.** Finding text, PoC section and coverage/residual-gaps
  section are read together. Re-read the full report for contradictions before saving/sending.
- **The PoC must drive the REAL production entry point end-to-end** — not a helper class or the stand-in's
  own unit test. A test on the fake proves nothing about the shipped path. Wire the real path, show it
  accepts the forged input, and ship two forms: the executed test in the repo's own tree (cite the JUnit
  XML: `tests=N failures=0 errors=0`) plus the isolated harness. (Cross-ref: PART 3, PART 4.)
- **No personal identity in the report header.** Bug-bounty platforms already bind the report to the
  submitter's account; name/alias/email in the document is unwanted disclosure and pure noise. Header =
  program / asset / date / revision only.
- **Do not pad with low-value observations.** Dependency-advisory dumps, well-known public test keys,
  and informational nits lower credibility and invite "N/A". Either drop them or compress to ONE line
  under a clearly-labelled "Notes (informational, not part of the finding)" header.
- **Follow the impact chain, but file it under the ORIGINAL root cause.** A no-op verification can be
  reachable *only* through downstream code, which makes it look like a second finding. Example:
  `zk_credit_verifier` accepts a 1-byte "proof" (the root cause), and separately
  `borrower_reputation::apply_zk_tier_upgrade` raises `reputation_score` to ≥1000 while
  `governance` uses that score directly as voting power — so the same defect escalates to governance
  capture. That is **impact amplification for TL-03**, not a new report: one root cause = one reward.
  Write the chain into the affected impact/severity section instead of minting a duplicate.
- **When a candidate finding is disproved, say so and keep the artefact.** A code shape that matches a
  known bug class can be dead on the target's runtime (see the Soroban re-entry guard). Convert the PoC
  into a `#[should_panic]` regression test and log it under VERIFIED NEGATIVES in the PHASE_LOG —
  that prevents the next session (and the next reviewer) from re-deriving and re-reporting it.
- **A self-contained PDF must EMBED its PoC — never cite an "attached PoC" file you did not attach.**
  Observed 2026-10: three per-finding PDFs referred to "the attached PoC `X.py`" while only the PDF was
  ever attached, so the deliverable contradicted itself. Fix: inline the PoC source into the PDF as an
  appendix, and have the delivery check assert a marker string from the PoC survives into the rendered PDF.
- **Verify delivery by re-reading it.** After writing the report to its channel (file, email draft, PDF),
  re-fetch and confirm the content actually landed (e.g. re-open the saved Gmail draft and assert key
  strings are present) instead of trusting the write call.
- **ONE finding = one report = one draft/email = one PoC.** Never bundle N findings into a single
  disclosure document. Observed correction (2026-10, TrustLend): the agent wrote ONE email draft holding
  all 12 findings; the user rejected it — *"perbaiki draftnya dulu, kan sy udh blg 1 draft 1 email 1 poc"* —
  and the redo was: delete the combined draft, emit one draft per finding, each with its own PoC command.
  Bundling is allowed ONLY for a genuine chain attack (A enables B). The delivery mechanics (per-finding
  draft loop, delete-then-append, Gmail subject-fold verification pitfall) live in the `email-automation`
  skill — load it for the send/draft step.
- **Every finding carries its own runnable PoC.** If a finding only has a "code path" description, add the
  missing runtime test before writing the report (see `references/source-only-poc-harness.md`). In the
  TrustLend pass five findings were still code-path only; adding 5 PoCs (2 Rust + 3 vitest) took the set to
  12/12 runtime-validated, which is what makes the report land.
- **Before claiming a follow-on / escalation impact, read the port's WRITE-path preflight — and if it
  blocks the chain, correct any earlier report you already wrote.** A read-path divergence ("the wallet
  credits units the chain does not") looks like it escalates to fund loss via "the user then spends the
  phantom" — so check the send/act path before writing that sentence. (Observed 2026-10: the same wallet
  refuses to build a send unless EVERY asset input is confirmed by an indexer to hold exactly the recorded
  quantity and asset id — `AssetInputCheck` → `VERIFIED`, else `MISMATCH` ⇒ set aside, `UNAVAILABLE` ⇒
  refuse — so the phantom cannot be spent and the burn chain never materialises. The claim had already gone
  out in an earlier report; the honest move was to **surface the overstatement unprompted and offer an
  erratum**, not to wait to be asked.) A fail-closed gate on the write path **caps severity but does not
  close the divergence** — report the divergence, state the gate, and stop short of the escalation.

## PART 7 — Source-only PoC recipes (any stack) + multi-finding delivery discipline

### Runtime PoCs beat code-path claims — build one PER finding
Each finding ships its OWN runnable PoC, dropped into the repo's existing test tree so the maintainer
runs it with the project's own build. Worked examples (actual code + commands + evidence):
`references/source-only-poc-recipes.md`.

**Rust / Soroban contracts (`cargo test`)**
- Drop `#[test] fn poc_<finding>()` into `contracts/<crate>/src/test.rs` (the crate already ends with
  `#[cfg(test)] mod test;`). Reuse the crate's own `setup()` helper — it calls `env.mock_all_auths()`.
- Run from `contracts/`: `cargo test -p <crate> <poc_name>`.
- ⛔ **`-p` takes the Cargo PACKAGE name — read `Cargo.toml`'s `name =`, never infer it.**
  Inconsistency is real: `zk_credit_verifier/` → `-p zk-credit-verifier` (hyphen) but
  `usdc_lending_pool/` → `-p usdc_lending_pool` (underscore). Wrong guess ⇒
  *"package ID specification … did not match any packages"*.
- First build compiles soroban-env-host (~3-6 min cold) — run it in the background, not foreground.
- **Make the PoC PRINT the exploit values, not just assert.** A bare `... ok` is weak evidence and the
  user will reject it (*"kurang lengkap … jgn hanya keterangan singkat"*). Print principal/balance
  before→after, tier granted, amounts, and a final `RESULT: <bool>`. Recipe: a `#![no_std]` crate has no
  `println!` in scope — add `extern crate std;` immediately after `#![cfg(test)]` in the crate's
  `src/test.rs`, then call `std::println!`, and run the single test with `-- --nocapture`.
- ⛔ **`soroban_sdk::Address` does not implement `Display`.** `{}` with an Address argument fails to
  compile (`error[E0277]`). Use `{:?}`. This bites on any "print the attacker address" line.
- **Capture transcripts per finding, not one merged log:** redirect each run to `evidence/raw/<ID>.txt`
  (`cargo test -p <pkg> <poc> -- --nocapture > …/TL-XX.txt 2>&1`) so each finding owns its evidence.
  Vitest `console.log` output carries ANSI escapes — strip `\x1b\[[0-9;]*[A-Za-z]` before parsing or
  your line filters silently match nothing.

**Next.js / TypeScript (`vitest`)**
- Drop PoCs in `__tests__/poc/*.test.ts`; run `npx vitest run __tests__/poc`. The repo's
  `vitest.config.ts` already aliases `@` → root and excludes `e2e/**` + `contracts/**`.
- Reuse the repo's `__tests__/helpers/fake-db.ts` (a thenable query-builder stub) for any Drizzle
  route: `vi.mock("@/lib/db/client", () => ({ getDb: () => db }))`, then `db.queue(result)` in the
  exact order the route awaits. Mock adjacent heavy modules (`@/lib/stellar/*`, `@/lib/contracts/*`,
  `@/lib/monitoring/*`) so the test isolates the auth/authz branch, not the network.
- ⛔ **Never `JSON.stringify` a Drizzle builder's `args`** — table/column objects are circular →
  *"Converting circular structure to JSON"*. Assert the shape instead:
  `c.method === "set" && "totalLiquidity" in (c.args[0] as object)`.
- ⛔ **`npm ci` first** — a fresh clone has no `node_modules` (~8 min); the vitest run needs it.

### Multi-finding delivery: 1 finding = 1 PDF = 1 draft = 1 email = 1 PoC
The user's HARD rule (canonical detail lives in the `email-automation` skill). When an engagement
yields N findings: **N drafts, N PDFs, N PoCs, N emails — never one combined draft holding all of
them.** This session built a single draft containing all 12 findings and the user rejected it
(*"kan sy udh blg 1 draft 1 email 1 poc"*). Only a genuine CHAIN attack may be bundled.
- **Sequence the user expects:** validate the findings → THEN produce the per-finding draft + complete
  PoC → user reviews manually → only then continue hunting. ("Validasi dulu, baru draft + PoC.")
- **"Pastikan divalidasi ulang" = re-run every PoC fresh** (cargo + vitest) and capture transcripts.
  Never assert a result from memory.
- **Regenerate the whole draft SET idempotently:** delete every prior draft matching the subject
  prefix, then append all N (folder / `X-Unsent` / attachment mechanics → `email-automation` and
  `reportlab-security-pdf`).

### Contract + API hunt patterns that paid here
- **A security decision that reads a CALLER-SUPPLIED value** — collateral, yield, price, count. The
  bug is trusting the argument instead of the stored/measured value (Soroban `create_loan_request`
  checked `request.collateral_entries`, not the borrower's stored entries).
- **"Verify" functions that only check a shape** — non-empty bytes, non-null, non-zero. A step labelled
  *cryptographic proof validation* that only scans for one non-zero byte is a no-op (`zk_credit_verifier`).
- **A money function that calls `require_auth()` but NOT `assert_admin`** while the rest of the contract
  gates admin actions — the odd-one-out contrast IS the proof (`collect_fees`, `treasury::distribute`).
- ~~State written AFTER an external call, no reentrancy guard~~ **NOT exploitable on Soroban —
  do not report it.** Soroban's host enforces a *contract-level* re-entry guard: re-entering a contract
  mid-execution aborts the whole call with `Contract re-entry is not allowed`
  (`Error(Context, InvalidAction)`). `multisig_admin::execute`, `governance::execute` and
  `usdc_lending_pool::withdraw` all do dispatch/transfer BEFORE writing their state — the shape is a
  smell, but a hostile target/token that calls back is rejected by the host. **Verified 2026-10:** a
  purpose-built re-entrant mock (`contracts/multisig_admin/src/test.rs::poc_execute_reentrancy_action_runs_twice`)
  aborted with exactly that error. Before flagging any state-ordering bug, ask "can the callee call
  back?" — on Soroban the runtime answers *no*. (On EVM this same shape IS a real bug; don't import
  that reflex into a Soroban review.) Keep the PoC as a `#[should_panic]` regression marker instead of
  deleting it — it documents the negative and keeps the repo suite green.
- **Fail-open auth guards** — `const secret = env.X; if (secret) { check }` skips the check entirely when
  the env var is absent (no `NODE_ENV` guard), and `if (!secret) return true` verifiers. Grep EVERY
  cron/webhook route for this shape and enumerate the whole set.
- **Conditional signature verification** — `if (sig) {...} else if (!isTestnet) reject` makes a
  testnet/default deployment accept unsigned events that credit state (`webhooks/sep31`).
- **Rate-limit key from a client-controllable header** — `x-real-ip` / `x-forwarded-for`. Prove the
  bypass A/B: same IP → 429 after the window; rotating the header → never limited.

### Endpoint-client / privileged-daemon review (native app, NOT a web API)

When the in-scope repo is a **client + privileged daemon** (VPN client, sync agent, updater,
security tool), the auth surface is the **local IPC channel**, not HTTP. This is a different
checklist from the web/contract patterns above, and it is easy to skip past while focused on the
client's networking code.

- **Fail-open client verification (the one that pays).** The daemon authenticates connecting
  clients by verifying the *client process is vendor-signed* — but a helper like
  `skip_authentication_checks()` returns **true** when the *daemon's own* signature cannot be
  verified, and the caller then sets the auth material to `None`, dropping client verification
  entirely. Grep `skip_auth|skip_authentication|self_is_signed|verify_certificate_signature` and
  READ THE FAIL-OPEN BRANCH — the happy path looks fine. Correct design is fail-*closed*.
  (Observed: `nym-ipc/src/authentication/{windows,macos}.rs` — identical shape on both platforms.)
- **Over-permissive IPC ACL/DACL.** The named pipe / socket grants READ+WRITE to
  `WellKnownSid::World` = **Everyone (S-1-1-0)**, so the fail-open branch above is reachable by ANY
  local user and the ACL provides no second line of defence. Grep
  `WellKnownSid|SecurityDescriptor|AbsoluteSecurityDescriptor|Trustee|ExplicitAccess|0o[0-7]{3}`.
- **Cite the platform contrast** — it pre-empts "this is by design". Linux (`SO_PEERCRED` → uid +
  vendor group membership, else a polkit prompt) is fail-*closed*; the inconsistency between
  platforms IS the argument.
- **Check the store layer too** (cheap, often clean): on-disk secret file modes (`0600`), parent dir
  (`0700`), keyring vs plaintext. Note it as a verified negative when it holds.
- **Severity discipline:** this is conditional on an unsigned / mis-signed daemon, and shipped builds
  are signed ⇒ LOW/MEDIUM. State the precondition and the affected population; do not inflate it to
  a Critical "any local user owns the VPN".

### Privacy / VPN client — leak-surface + swallowed-error review

Same native-client track, different payload: for a VPN/privacy client the paying impact is a
**traffic or DNS leak**, so review the *protections*, not just the auth.

- **Enumerate every swallowed-error site, then check each for a missing `return`.** Highest-yield
  grep on this codebase class:
  `rg -n "if let Err\(|inspect_err|trace_err_chain|\.ok\(\)|unwrap_or\(Ok\(\(\)\)\)" <state-machine dir>`
  For each hit ask: does the branch `return` / transition state, or does it only log? A log-only
  branch sitting among siblings that DO return is itself the defect — **the sibling set is your proof
  it is a bug, not a style choice.** (Observed 2026-10: `connected_state.rs` logs
  `"failed to enable dns forwarding"` with no return, while `connecting_state.rs` `return`s
  `ErrorState` and `error_state.rs` uses `.inspect_err(..).map_err(?)`.)
- **Check the CALLEE too — double fail-open is common.** A helper declaring `Result` may be
  *incapable* of returning `Err`:
  `if tx.send(..).is_ok() { rx.await.ok().unwrap_or(Ok(())) } else { Ok(()) }`
  discards the inner error AND treats a dead worker as success. When the callee always returns `Ok`,
  the caller's `if let Err` guard is **dead code** — say that explicitly; it is the finding.
- **Look for the "resource is live but unconfigured" shape.** If the socket/handle is bound at
  `spawn()` and its address is published *independently* of the config step, a failed config leaves
  the system pointed at a live-but-misconfigured endpoint → outage, or fallback outside the tunnel.
- **Check the apply/set SIGNATURE, not just the call site.** A helper declared `fn … -> ()` on a
  security-critical config path **cannot express failure** — every per-item error is log-only, so the
  caller's guarantee is empty. Read the *other branches* of the same caller: an intra-function
  asymmetry (`save(..)?` on the re-apply branch vs log-and-continue on the first-set branch) is the
  fix-it argument, and if the sibling `reset()` accumulates a `first_error`, the codebase demonstrably
  knows the pattern. (Observed: `nym-dns/src/macos.rs` — `apply_desired_state` returns `()`;
  `apply_new_config`'s `None` branch returns `Ok(())` unconditionally.)
- **Classify swallowed calls by security ROLE, not by count.** If the calls that *prevent* the leak
  are the swallowed ones while a benign one propagates, **the diff is simultaneously the proof and the
  impact analysis** — you don't argue severity separately. Learn each platform call's semantics before
  writing the impact paragraph (systemd-resolved `SetDomains(link, &[(".", true)])` = route *every*
  domain to this link + default-route flag; `disable_dot`; macOS `DnsSettings::save`). Enumerate
  **every** backend — Linux ships both `systemd-resolved` and `resolvconf`, each a separate candidate
  with its own semantics; do not stop at the first backend you read.
- **Kill switch must fail CLOSED.** Confirm the error path lands in a *blocked* state, not a bypass:
  check the policy enum (`Connecting|Connected|Blocked`) and that the error state itself applies
  `Blocked`. A firewall-apply failure that continues to connect is Critical-class.
- **Dual-stack default-deny.** An IPv4-only block-all on a dual-stack host is an IPv6 leak. All
  three platforms have now been verified — use these as the checklist:
  - **Linux:** nftables table family must be `inet` (covers v4+v6) with `Policy::Drop` on
    in/out/forward.
  - **macOS:** a pf `block drop all` with no family qualifier (matches inet+inet6).
  - **Windows:** WFP filters on **all four** ALE layers — `FWPM_LAYER_ALE_AUTH_CONNECT_V4`,
    `ALE_AUTH_RECV_ACCEPT_V4`, `ALE_AUTH_CONNECT_V6`, `ALE_AUTH_RECV_ACCEPT_V6` — added as
    match-all (`libwfp NullConditionBuilder`) at `wfp::FilterBuilder::WeightClass::Max`, in BOTH
    the session and the persistent variant. Only v4+v6 connect+accept at Max weight is a pass.
  `enable_ipv6=false` should *remove IPv6 from the allow-lists*, not just flip a separate switch.
- **The vendor's own leak comments are a map.** In-code notes like `"Hyper-V/WSL may leak in blocked
  states"` or an Apple-services PF-bypass workaround point at the areas worth probing — and at
  runtime toggles that weaken the control (e.g. an env var that disables the block rule: same shape
  as the fail-open auth above). Worked casebook of these shapes:
  `references/native-client-fail-open-casebook.md`.

## PART 8 — Reference-implementation differential review (ports, forks, reimplementations)

When the target is a **port / fork / re-implementation** of a known upstream (a wallet, a protocol
client, a consensus/asset library, a mobile app wrapping a C core), the highest-yield move is not
reading the port in isolation — it is **cloning the upstream the port cites and diffing behaviour
function-by-function**. Every divergence from the reference is a candidate finding, and the port's
own comments hand you the map. This is the technique that produced **both** new findings in a
heavily pre-audited Android wallet (2026-10): a fail-closed LOW from the reference's *success* path
(F4) and a HIGH false-positive-receive from its *error* path (F5) — same function, and the error
path was the exploitable one.

1. **Find the reference.** Grep the target for citations: `Ported from`, `confirmed vs`,
   `matches <X>`, `see <file>.cpp:NNN`, `Ported from RenzoDD/… BitIO.cpp`. The cited repo is your
   reference. Clone it `--depth 1`.
2. **Map function↔function.** For each ported unit, locate its counterpart in the reference.
3. **Compare the semantics that can differ:** bit/field widths, condition **scoping** (does the
   check carry the operation / type / version guard?), loop bounds and stop conditions, defaults,
   and overflow behaviour.
4. **Strongest signal = the port ALSO contradicts itself.** If module A scopes a rule to an
   operation and module B (fed by A's output) does not, you have an internal inconsistency *plus* an
   external divergence — that pairing pre-empts "this is by design". Cite both sides.
   (Observed: `DigiAssetDecoder.kt:241` sets `isBurn` for a transfer instruction to output 31 with
   no operation guard, while `AssetTxQuantity.kt:139` correctly scopes the same marker to BURN.)
5. **Check test coverage of the divergent branch.** Grep the test tree for the exact construct
   (the flag name, `outputIndex = 31`). If the tests only ever build it with the flag hardcoded —
   exercising one branch and never the divergent one — the divergence is uncovered. That is part of
   the finding.
6. **PoC = two-sided line citations + a deterministic simulation.** Exact `file:line` on the
   reference side and the target side, plus a small arithmetic/behaviour simulation that
   re-implements both branches and prints the divergent totals. Recipe + worked case:
   `references/reference-differential-review.md`.
7. **Diff the reference's ERROR / ABORT paths, not just its success semantics** — this is the
   highest-yield extension of the technique, and it found the bigger bug of the pair. A port that
   mirrors only the happy path will credit state the reference *discards*. Read every `throw` /
   `catch` / early `return` / `break` in the reference function and ask **what the reference's state
   is after it fires**. (Observed 2026-10, same function as F4: the reference's
   `decodeAssetTransfer` throws `exceptionInvalidTransfer` on any instruction naming a non-existent
   output, and its `catch` **clears every output's assets**, restores the inputs, and lets the
   trailing loop credit the whole input amount to the **last** output. The port has no
   whole-transfer validity step — it credits each in-range instruction independently — so it shows a
   recipient units the chain places at the sender's change output: a **false-positive receive**, the
   class the program names as HIGH, versus the fail-closed LOW of the success-path divergence.
   Same reference function, same technique; the *error* path was the exploitable one.)
   **Make it a checklist, not one look.** F5 was the *first* abort trigger; a later pass on the same
   function found a second (F6). Enumerate EVERY abort path in the reference function and check the
   port models each:
   - *argument / instruction invalid* (index out of range, bad count) → reference aborts, clears
     every output, and drops the remaining input units on the **last** output (F5).
   - *rule / permission failure* → the reference's `checkRulesPass()` throws `exceptionRuleFailed`
     and the handler clears every output; the port gated that rule on the **SEND** path only and
     never evaluated it on the **credit** path (F6). A rule-bound asset's transfer therefore
     credits units the chain wiped.
   - *pre-classification precedence* → the reference runs `decodeKYC` / `decodeExchangeRate`
     **before** the asset path and `return`s early, so a tx it classifies as another kind is never
     credited as an asset. A port with no such pre-classification diverges. **Unproven here**
     (the exchange-rate matcher needs output[1] to be a watch/exchange address) — record it as an
     unproven candidate, never as a finding.
   **Generalises to:** *a control the port enforces on the WRITE/send path but not on the
   READ/credit path is a bug class by itself.* Grep every gate the port applies before *acting*, then
   ask whether the same condition also governs *accepting* state. (Such a gate only caps severity —
   it does not close the divergence.)
8. **Align the two index spaces before comparing anything index-based.** Establish whether the
   port's output/input list is the **raw** list or a filtered one by reading the bridge/serializer
   that builds it — do not infer it from a comment. (Here `jni_asset.c`
   `getTransactionOutputsForHash` emits **all** outputs with their raw indices, so
   `outputCount == _outputs.size()`. Without that check, "the port uses a shifted index space" is
   untestable — and a comment elsewhere in the port claimed the opposite.)
9. **Also diff the port against its OWN pinned spec — the repo's `docs/…` canonical-rule document,
   not only an external reference.** A reimplementation of a consensus/wire format usually ships a
   document the code cites by name ("see docs/superpowers/specs/…", "spec §3.2"). Where that
   document declares a rule **CANONICAL (consensus) — PINNED** and the code implements something
   *stricter or looser*, that mismatch is a finding **before** you even have the upstream in hand —
   and the inline comment is usually the confession. (Observed 2026-10, DigiDollar: spec §3.2 says a
   DD output is "exactly 34 bytes beginning with `OP_1(0x51)`", while `BRDigiDollar.c:219` *also*
   requires `script[1] == 0x20`, and the comment right above admits "Requiring the second byte too
   keeps a 34-byte OP_1 script that is not that exact form from binding to an amount slot."). Grep
   the doc for the rules the code implements — counters/ordinals, ordering, widths, skip conditions
   — and compare operator-for-operator; a **counter that advances on a different set of items** is
   the highest-yield shape, because everything after the divergence is mis-bound. (Cents here bind by
   *output ordinal*, so a stricter test shifts `k` and every later output reads the wrong amount
   slot → false-positive balance.) Frame the fix as **"make spec, comment and code agree"** — you do
   not have to decide which side is right, and either way it is a real inconsistency.
   - **Gate the severity on how the divergent INPUT can reach the chain.** The F7 trap is a
     non-standard output (34-byte script, first byte `OP_1`, second byte not `0x20`), which default
     relay policy drops, so it only lands in a block if a miner includes it ⇒ **MEDIUM**, and say that
     gate out loud instead of claiming HIGH. (Same discipline as PART 3 reachability.)
10. **Check the port's TRUST SOURCES for the same datum — and whether it treats them alike.**
   A port usually carries one *authenticated* view of a datum (derived from the chain/protocol) and
   one *claimed* view (from a document or a service). The paying shape is **asymmetric trust of the
   same field**: the port correctly refuses the untrusted source, then accepts the same
   unverifiable string from a *different* third party.
   - Observed 2026-10 (Android wallet, F8): `AssetMetadataService` states in a comment that an
     asset's `issuer` must never be read from the metadata document — "the easiest thing in the
     file to forge" — and `provenIssuerOnly(proven, claimed)` ignores `claimed` entirely (so a
     missing proven value renders no row: *absent beats wrong*). Yet on the **provider** path the
     provider's own `issuer` string is passed into the **`proven`** slot
     (`AssetMetadataService.kt:180,195` → `:317 issuerAddress = provenIssuerOnly(proven =
     provenIssuer, claimed = null)`), and `updateIpfsFacts` writes `issuerAddress` unconditionally
     (`AssetMetadataDao.kt:35-48`). A provider that lies forges the attributed issuer ⇒ MEDIUM.
   - **For every datum the UI presents as authoritative, ask: where does it come from, and can the
     client re-derive it independently?** Grep the native/bridge surface for the matching
     `derive*` (here: `deriveIssuanceAssetId` existed, but **no** issuer derivation — so the
     wallet could not check the string at all). If no independent derivation exists, the only
     honest options are to omit it or label it third-party-claimed; rendering it inside the
     authoritative field is the bug. **The port's own distrust comment is the argument** — quote it
     beside the provider line, so the finding reads as "you already applied this rule to the other
     source".
   - **The cleanest reachable case usually needs no adversary trickery.** Pass-1 (authenticated
     source) failing for an ordinary reason — a gateway down — drops the client into Pass-2, where
     the *authenticated* payload (CID/name/image all verified) still carries a *claimed* issuer.
     Authenticated content + forged attribution in one row is the strongest framing.
   - **Put the trust boundary in the severity line**: *who must misbehave* decides the tier. A
     cert-pinned first-party provider must itself lie ⇒ MEDIUM; an unauthenticated network peer
     that can inject the response ⇒ HIGH. **Verify the pinning before claiming a MITM path**
     (`DigiScopePins.kt` / `DigistampPins.kt` here — all provider hosts pinned, so no MITM).

11. **Check whether a SIBLING path in the same codebase already verifies the same datum — and whether
    the path you are reading skips it.** The strongest form of "the port misses a control" is not "the
    reference does X and the port does not"; it is **"the port does X on one path and not on the sibling
    path handling the same datum"** — the contrast is internal, so "by design" is dead on arrival.
    Enumerate every consumer of a datum before judging any one of them.
    - Observed 2026-10 (Android wallet, F9): `ChainReconciliationService.fetchTransactionBytes` documents
      and enforces *"every transaction is accepted only when its bytes hash to the id asked for"*
      (`NativeBridge.rawTransactionId(bytes) == txid`), and `MultiEndpointAssetClient.getRawTransaction`
      enforces the same. The history-recovery import in the SAME file
      (`importPlannedHistory` → `register(bytes, raw.blockHeight, raw.blockTime)`) never compares the bytes
      to the planned txid, and the native `registerRawTransaction` **takes no expected-txid parameter** —
      so it stamps `tx->blockHeight` from the caller and registers whatever arrived. A signed,
      wallet-associated transaction the chain does not have enters the ledger at a caller-claimed height
      ⇒ **false balance, HIGH** — reached through the *repair* path, not the asset path.
    - **A missing parameter is structural, not a call-site oversight.** When the leaf function has no
      argument for the expected identity, verification is *impossible* at that layer — say in the fix that
      the parameter must be added, not that a caller should compare. A caller-side check leaves the next
      caller to reintroduce the hole.
    - **Where to look first: reconcile / recovery / re-import / repair flows.** They are written as
      best-effort bulk re-ingestion, which is exactly where a verification norm established on the primary
      path gets dropped. Grep `register*` / `import*` / `reconcile*` / `fetch*` functions that take a
      claimed height, index, or position alongside the payload (`rg -n "fun (register|import|reconcile)"`).
    - **The gate is "who must misbehave"** — state it: here an answer whose bytes differ from the requested
      txid is enough, which a merely buggy or desynced node produces as readily as a hostile one, so the
      severity does not rest on an adversary. (Contrast item 10, where the datum came from a cert-pinned
      first party ⇒ MEDIUM.)

⛔ **A quirk that MATCHES the reference is NOT a finding.** Before claiming a silent integer
overflow (e.g. `mantissa * pow10(exponent)`), an odd default, or a lenient parser, read the
reference's equivalent line. Ports deliberately mirror upstream bugs; only a port that *disagrees*
with its reference (or with its own documented rule) is a finding. Say "matches the reference, not
a finding" out loud and move on.

⛔ **A cited convention can kill a candidate — check before writing it up.** "The walk follows
`input[0]`, so it could name the wrong asset" dies the moment you find that `input[0]` *is* the
protocol convention (here `AssetDuplicateDetector` states ids derive from `input[0]` of the
issuance). Record it as a VERIFIED NEGATIVE, don't report it.

- **A port with a KAT / "UNFIXED"-flag harness has already audited those classes.** Compile-time
  flags that switch a function back to pre-fix behaviour for a known-answer test
  (`#ifndef WIRE_COUNT_BOUNDS_UNFIXED`) plus `invariant:` comments bounding every wire count mean
  the memory-safety surface is done. Do not burn the budget re-deriving it — move to **logic**
  (attribution, scoping, ordering, which-entity), which those flags do not cover. That is where
  F4-class bugs survive.
- **Verify the SHIPPED build actually sets the strict level of any compile-time security flag.**
  A check gated behind `#if SEC_CHECK >= 2` (hard-reject) vs `>= 1` (compute-and-log) has its
  effective level decided by the *build*, not by the header default (`#ifndef … #define … 0`).
  Before calling such a gate weak, grep the build config for the `-D` override —
  `native/build.gradle.kts` `cFlags(...)`, `CMakeLists.txt`, `app/build.gradle.kts` — and confirm
  which buildType it applies to. (Observed: a `DGB_HEADER_POW_CHECK`/`DGB_HEADER_DIFF_CHECK`
  "level-1 weakens rejection" candidate died because `defaultConfig` sets both to `2` for every
  build type. Candidate closed, not filed.)
- **When surface-by-surface is exhausted, sweep by bug CLASS instead of by file.** One grep over
  the whole tree for a narrowing/arithmetic shape finds every instance of a recurring defect class
  at once — then check each hit against its guard before believing it. Shapes worth a sweep:
  `.toInt()/.toShort()/.toByte()` on a parsed `Long`, `copyOfRange`/`substring`/`sliceArray` with a
  computed index, and array indexing after a varint/length read. (Observed 2026-10 in an Android
  wallet: a decimal formatter whose cut index derives from issuer-controlled `divisibility` was
  safe **only** because the digits were `padStart(decimals + 1)`; a varint reader was safe **only**
  because every multi-byte branch checks `offset + N <= data.size` first. Both hits, both already
  guarded — the guards are the thing to look for.)

## PART 9 — On-chain ACL + service monorepo (Solidity diamond, Rust API, JS runtime)

A very common program shape (observed 2026-10, LIT-Protocol/chipotle): one repo holding a
**Solidity diamond (EIP-2535)** that IS the authorization database, plus Rust services that relay
writes into it, plus a JS sandbox runtime. The licence-to-scan surface is zero — the whole hunt is
source + local test evidence. Full recipe, commands and the worked case:
`references/solidity-diamond-authz-review.md`. Starter harness: `templates/DifferentialAuthz.t.sol`.

**Order of operations that works**

1. **Policy first, then `git log`.** Parse the program page for the *paid* impacts ("extract keys,
   forge attestation, bypass the permission model, escape the sandbox" tells you the four hunt
   lanes). Then `git log --oneline -60` and read the security-ticket archaeology — vendor commits
   name their own fixed bug classes (`CPL-285/295/379`, `#62/#97/#116/#575`). **Those are your
   dedup map**: hunt *siblings* of fixed bugs, never the fixed bug. Comments in-tree describing an
   already-closed hole ("this closes the gap at the request boundary as defense in depth") are
   proof the class was reviewed — skip it, and record it as a verified negative.
2. **Map the ACL, not the features.** For a diamond: `AppStorage.sol` (the namespaced struct = the
   whole data model), `SecurityLib.sol` (every guard), `WritesFacet.sol` (every mutation + its guard),
   `ViewsFacet.sol` (every authorization *predicate*). Read the guards before the handlers — the
   finding is almost always a mutation that calls a weaker guard than its siblings.
   Enumerate: **who may write** (owner / api_payer / configOperator / admin wallet / usage key),
   **what namespace is shared** (e.g. one `allApiKeyHashesToMaster` map holding masters, usage keys
   AND admin-wallet aliases — namespace-confusion bugs live exactly there), and **which predicate the
   service actually calls**.
3. **Check the relay layer for identity laundering.** The service hashes the caller's credential and
   passes a `*_hash` into the contract. Verify **every management write derives that hash from the
   credential header**, never from a request body field, and that reads hash unconditionally with no
   "already a hash" passthrough. A `usage_api_key_to_hash()` that passes through 0x+64hex *plus* an
   endpoint that accepts it as a body param = cross-account write primitive. (Lit had the passthrough,
   but the guard rejected hash-shaped header input and reads still hashed unconditionally → closed.
   That asymmetry is worth re-checking on every target of this shape.)
4. **Prove the ACL with a differential test, not with prose.** Write a fuzz test that enumerates the
   predicate cross-product and asserts all authorization entry points agree. Four views answering the
   same question (`canExecuteAction`, `...Fast`, `canUseWalletInAction`, `...AndUseWallet`) WILL drift;
   the invariant `canUseWallet ⇒ canExecute` is a one-line assertion that catches real drift. Then add
   cross-tenant tests (stranger write, wallet/path hijack, namespace squat, master-key-has-no-power).
   `templates/DifferentialAuthz.t.sol` is the working shape — 256 fuzz runs, 5 tests, all green.
5. **Sandbox runtime: verify the egress filter against the PINNED upstream crate, not the comment.**
   A deny-list of internal CIDRs on a `fetch` path is bypassable via hostname/DNS-rebinding unless the
   runtime also does a **post-resolution** check. Download the pinned crate sources
   (`static.crates.io/crates/deno_net/deno_net-<v>.crate` → `tar xzf`) and confirm each op
   (`connect`/`connectTls`/`listen`/`listenDatagram`) calls `check_resolved_ip_deny`. If it does, that
   whole class is a **verified negative** — say so and stop spending budget on it.
   Same discipline for module loaders: check the specifier allowlist normalises `..` *before*
   validating (a raw prefix check on `cdn.jsdelivr.net/npm/` is escaped by `npm/x/../../gh/...`).
   ⛔ **An egress model built on "is this IP internal" has a STRUCTURAL blind spot: transports with no
   IP at all.** Enumerate those FIRST — you cannot fix with a CIDR list what has no address:
   - **Unix sockets**: pinnned `deno_net`'s `op_net_connect_unix` gates only on
     `check_open(.., OpenAccessKind::ReadWriteNoFollow, ..)` — a *filesystem* permission. `check_net`
     and `check_resolved_ip_deny` are never called, so `deny_net` is not consulted at all. If the
     runtime happens to grant read/write that path opens co-located daemons (IPFS API, the runtime's
     own gRPC socket, agent sockets) with zero egress-layer defence. `allow_read/write` being unset is
     the *only* guard, so this is the highest-value thing to prove at runtime.
   - **vsock / tunnel / QUIC**: check each `op_*` individually — `op_quic_endpoint_create` does
     `resolve_addr_sync` + `check_net` but **no** post-resolution check and **no** `check_unstable`,
     while `op_quic_endpoint_connect` does have both. A per-op guard audit is the only way to see this;
     the module-level comment will claim uniform coverage.
   Method: `curl -sSL -o x.crate https://static.crates.io/crates/deno_net/deno_net-<ver>.crate &&
   tar xzf x.crate`, then `grep -n 'pub async fn op_\|pub fn op_\|check_net\|check_net_resolved\|check_open\|check_unstable'`.
   Rank each op: `check_net` only = hostname/DNS-bindable; `+check_net_resolved` = sound;
   `check_open` only = **not a network control at all**.
5b. **Probe the live surface as ONE action returning a JSON blob, then assert separately.** The
   upstream suite tests what the vendor already fixed; write your own sweep that returns
   `{name: "OK:<value>" | "<Err>: <msg>"}` for every primitive and read the whole map from a single
   execution. Cheap assertions that paid here and are missing from a typical upstream suite: raw
   `process.binding("fs")` / `process.binding("os")` key lists, `Deno.open()` (vs the tested
   `node:fs` path), the **high-level** `node:dgram` send and `node:net` connect (vs only the raw
   `udp_wrap`/`tcp_wrap` bind ops), non-literal `import()` of `data:` / CDN / `ext:` specifiers (the
   bundler only rewrites *literals*), `child_process.execSync`, `Deno.env`, `process.abort`, and the
   full `Reflect.ownKeys(Deno)` + `Reflect.ownKeys(Lit.Actions)` lists. Keep the assertion test
   separate from the informational one so a single unexpected `OK:` names itself.
   Also verify **isolate reuse by reading the pool code path, not the comment**: a pool that is
   genuinely one-shot shows the handle consumed, the runtime shut down and the worker dropped after one
   request; a comment saying "one-shot" is not evidence.
   Building this runtime on Windows needs the rootless WSL chain in `security-tooling-setup` →
   `references/rootless-rust-build-wsl.md` (protoc/libclang/libLLVM/OpenSSL + the
   `CARGO_PROFILE_DEV_DEBUG=0` linker fix).
6. **Kill leads explicitly and keep the artefacts.** End the round with a `COVERAGE.md` split into
   *verified-with-tool-evidence / reviewed-negative-with-reason / NOT-tested*. Naming the three leads
   you disproved (and why) is worth more to the next session than another page of prose.
7. **Attribute the live deployment to the audited commit — diamond-aware, and match the PIPELINE's
   compiler.** Programs of this shape usually say it outright ("before reporting an issue that depends
   on what code is running, verify the live state yourself"), so this is in-scope work, not an extra.
   It is also the sentence that makes the whole audit load-bearing: "deployed runtime == HEAD, every
   executable byte identical" is worth more than another page of findings.
   - **Enumerate facets over RPC, never from the repo**: `facets()`, `facetAddresses()`,
     `facetFunctionSelectors(address)`, then `eth_getCode` each facet. Diff the live selector SET
     against `forge inspect <Facet> methodIdentifiers` for every facet — **both directions are
     evidence** (live-not-in-repo = a function no source can show you; repo-not-live = a stale deploy
     that predates a fix).
   - **Then byte-diff using the compiler the DEPLOYMENT uses — read the `Makefile`/CI, not
     `foundry.toml`.** On Lit the repo shipped both, and the pipeline's `compile:` target runs
     `npx hardhat compile` (default `evmVersion` **paris**), while `forge build` defaults to
     **cancun**/PUSH0 and came out 2-3% *smaller* on every facet — a delta that reads exactly like
     "the deployment is not the source". With the Hardhat profile every length matched and the only
     remaining diff was the 32-byte trailing CBOR metadata hash.
   Full recipe + the attestation lane:
   `references/tee-attestation-and-live-deployment-verification.md`.
8. **When the program pays for "forge attestation", attack the VERIFIER by re-implementing it.**
   Do not read the vendor's ~1300-line attestation module and call it reviewed — write an independent
   verifier from the spec, in a different language/stack, and run it against the live endpoint. Two
   independent implementations agreeing IS the evidence; a disagreement in either is the finding.
   Re-runnable script: `scripts/verify_tdx_attestation_v2.py` (TDX quote PCK chain + event-log replay
   + measured identity + KMS key-release chain + fresh-nonce statement).

**Pitfalls (paid for this session)**

- **`forge inspect <Contract> methodIdentifiers --json` — bare contract name.** The
  `path/to/F.sol:Contract` form fails with *"Could not find source file for contract … at …"* even
  though the file exists. Pipe to `tr -d '\r'` (CRLF on Windows corrupts the JSON) and stash per-facet
  files, then diff selectors in Python for diamond collisions (8 facets / 76 selectors → 0).
- ⛔ **`vm.expectRevert()` before a VIEW fails the test.** Views in this pattern return a **sentinel**
  (`0`, or the unregistered-value default) instead of reverting. Assert
  `assertEq(views_.getX(otherAccount, id), 0)` — an `expectRevert` here produces
  *"next call did not revert as expected"* and looks like a finding when it is a test bug.
- **Do not nest `vm.prank` inside `vm.startPrank`.** *"cannot override an ongoing prank with a single
  vm.prank"*. Either drop the inner prank (already impersonating) or close the block first.
- **`via_ir = true` makes `forge build`/`forge test` minutes long** and a foreground call dies at the
  tool timeout mid-compile. First build ≈ 4–7 min: `background=true, notify_on_complete=true`, then
  `process(action=poll)`. Incremental runs are seconds.
- **Write outputs where the *Windows* interpreter can read them.** `curl -o /tmp/x.html` then
  `python -c "open('/tmp/x.html')"` fails (*FileNotFoundError*) — MSYS `/tmp` is not what native Python
  sees. Keep all artefacts inside a real workspace dir (`~/<target>-audit/`) and pass native
  `C:\Users\...` / `D:/...` paths when a native tool reads them.
- **`web_extract` on a docs site can be backend-blocked** ("ddgs is search-only"). Fall back to
  `curl` + a 6-line strip-tags Python pass; keep the stripped text on disk as the policy artefact so
  later claims can be re-checked against it verbatim.
- **A per-replica replay cache is documented, not absent.** Read the comment before writing up "replay
  possible": the code may say *"this is per-replica; a shared store would be required for cross-replica
  dedup"*. That is a known, accepted limitation — reporting it as a finding is a self-inflicted N/A.
- **Static host scanners are useless here** and it is not a gap — on a repo-only program the scanner
  layer is `N/A (codebase track)`, same rule as PART 0. Do not claim coverage from absence of a host.
- ⛔ **A `0x`-prefix mismatch fabricates 100% of a selector diff.** `facetFunctionSelectors` returns
  `0x`-prefixed 4-byte hex; `forge inspect methodIdentifiers` values are bare hex. Comparing the raw
  sets on Lit reported **76 "hidden" and 76 "missing"** selectors on a diamond whose source matched
  exactly. Normalise both sides (`s[2:] if s.startswith("0x") else s`) before any set arithmetic, and
  treat an all-hidden-AND-all-missing result as a normalisation bug, never as a finding.
- **Wrong build profile ⇒ false divergence.** Foundry's default `evmVersion` is cancun (PUSH0),
  Hardhat's is paris. A repo that ships `foundry.toml` *and* `hardhat.config.ts` may build with only
  one. `forge build` gave APIConfig 1961 vs live 2037B, Billing 1302 vs 1339B, Views 8957 vs 9217B,
  Writes 14604 vs 14916B — all "divergences" that vanished under `npx hardhat compile`. Read the
  `Makefile`/CI `compile:` target first.
- **Facets under `libraries/` get no Hardhat artifact** (outside `sources`), so the EIP-2535 reference
  facets (DiamondCut/Loupe/Ownership) have no compiled counterpart to diff. Verify them by selector
  match plus stock-implementation reasoning, and say which ones you could not byte-verify.
- **A `forge inspect` on a ~15k-line project needs the bare contract name**, and `forge test` on a
  `via_ir` project takes minutes — launch `background=true, notify_on_complete=true` and read the tail
  after the fact instead of a foreground call.

## Support files

- `references/bounded-traversal-fail-open.md` — PART 2 item 4b: a security decision computed by a
  **bounded walk** that stops silently (node/depth/length caps) is fail-open; the attacker pads the
  document and parks the payload past the bound. Includes the flat-field-control trap that wastes a
  round, the controls you must ship, the repo's-own-test-tree handover (`1 pass / 2 fail`), and the
  "their own comment about a previous fix of the same class" argument — worked bWallet safety-filter
  case (Medium, validated).

- `references/solidity-diamond-authz-review.md` — PART 9: EIP-2535 diamond ACL review (which four
  files ARE the model), the relay-layer identity-laundering check, the differential-predicate harness,
  verifying a sandbox egress filter against the pinned upstream crate sources, and the worked
  LIT-Protocol/chipotle case (4 lanes, 6 verified negatives, 3 disproved leads, what was left untested).
- `templates/DifferentialAuthz.t.sol` — copy-and-modify Foundry harness: fuzz the predicate
  cross-product (slow/fast/combined + `canUseWallet ⇒ canExecute`), cross-account write denial,
  wallet/derivation-path hijack denial, namespace squat, master-key-has-no-authority.
- `references/tee-attestation-and-live-deployment-verification.md` — PART 9 steps 7-8 in full:
  diamond facet/selector enumeration over RPC + the `0x`-normalisation trap, matching the
  DEPLOYMENT's build profile (Foundry cancun vs Hardhat paris) to kill false divergences, and
  re-implementing a vendor's TDX/SGX attestation verifier independently — with the crypto
  mismatches that cost real time (DER vs raw r||s, PCK-chain verify direction, keccak
  `digest_bits`, recoverable-signature candidate selection) and the "quote carries no nonce,
  freshness lives in the statement signature" modelling rule.
- `scripts/verify_tdx_attestation_v2.py` — runnable independent verifier for a
  `GET /attestation/v2`-shaped endpoint: quote PCK chain to a pinned Intel root, QE binding,
  event-log → RTMR replay, measured identity + compose hash, digest-pinned images, KMS
  key-release chain, fresh-nonce statement. Edit the `APP_ID`/`PINNED_KMS`/policy constants
  at the top and run `python verify_tdx_attestation_v2.py [origin]`.
- `references/multi-tenant-cache-scope-review.md` — **multi-tenant SaaS with an RLS
  boundary (open-source code + hosted Cloud, scanner-forbidden policy)**: the third PART 0
  routing row, the passive surface map to build before reading code (`security.txt` →
  `llms.txt` → `openapi.json` → OAuth/MCP `.well-known` → certspotter CT), and the
  highest-value bug class on this shape — **a cache key that omits a dimension its cached
  value depends on** (`permissions:${userId}` holding a company-scoped `role`, where that
  `role` gates `bypassRls` → service-role client) — with the four-step verification
  checklist that decides candidate-vs-filing, plus the sibling sweeps (`SECURITY DEFINER`
  RPCs under service-role, company-scoping proxies that wrap only `update`/`delete`,
  open-by-design DCR, auth-path parity).

- `references/audit-coverage-gap-analysis.md` — PART 2b: mature / heavily-audited protocols. The
  `/security` → `SECURITY.md` door, the Known-Issues list as the dedup map, mapping `audits/*.pdf` →
  modules with `pypdf` (no hits = unaudited), and `git diff --stat <last-audit-tag>..HEAD` to rank the
  post-audit surface; includes the `git fetch --unshallow` trap and the deployed-version check.
- `references/cross-path-verification-consistency.md` — PART 8 item 11: the *a sibling path already
  verifies this* shape (F9 — the history-recovery import registers provider-supplied bytes without the
  txid check its sibling enforces), the "missing parameter makes verification structurally impossible"
  rule, the repair/reconcile-flow heuristic, and the who-must-misbehave severity framing.
- `references/trust-boundary-source-asymmetry.md` — PART 8 item 10: the *same datum from two sources,
  opposite trust* shape (the port refuses the metadata document's `issuer` but writes the provider's
  into the authoritative column, F8), the source→sink sweep, "migrations are a confession", and the
  who-must-misbehave severity rule.
- `references/spec-vs-code-divergence.md` — diffing the code against the repo's OWN pinned spec
  (`docs/…` sectioned "CANONICAL (consensus) — PINNED"): the *stricter predicate shifts the ordinal*
  shape (F7, DigiDollar cent binding), severity gating when the divergent input is a non-standard script
  that needs a miner, reusable DigiDollar wire-format notes, and the write-path-preflight discipline for
  retracting an overclaimed escalation.
- `references/reference-differential-review.md` — clone-the-upstream differential recipe + three worked
  DigiByte-wallet cases on the SAME reference function (success-path LOW / out-of-range-error-path HIGH /
  rule-failure-error-path MEDIUM), the multi-trigger invalidation checklist (argument-invalid,
  rule-failure, pre-classification-precedence), and the write-path-vs-credit-path asymmetry. the *success*-path divergence (DigiAsset
  output-index-31 burn marker scoped to the BURN op in the reference, unscoped in the port → units
  dropped from crediting, LOW) and the *error*-path divergence (an out-of-range instruction makes the
  reference discard the whole transfer and move all input units to the last output, while the port
  keeps the in-range credits → false-positive receive, HIGH); plus the recipe extension for error
  paths and index-space alignment, and the candidates disproven by convention/reference check.
- `references/evidence-screenshots-and-pdf.md` — the "make it triager-grade" pass: make the PoC print
  real exploit values, capture one transcript per finding, render a terminal-style evidence PNG with
  Pillow (exact sizes/colours + the ANSI-strip trap), teach `md_to_report_pdf.py` to embed `![cap](path)`,
  QA the PDF (layout + whitespace-normalised text checks + embedded-image assertion), rebuild drafts.
- `references/github-pvr-submission.md` — GitHub Private Vulnerability Reporting: vetting an advertised
  security address, the PVR report endpoint vs. the advisory endpoint, fine-grained vs. classic token
  permissions (`repository_advisories=write` / `public_repo`), the content-creation secondary limit on
  young accounts, and how to hand a token to a script without the secret-scrubber eating it.
- `references/source-only-poc-recipes.md` — copy-paste recipes for runtime PoCs in source-only
  engagements: Soroban `cargo test` harness, Next.js/vitest route PoCs with the repo's fake-db,
  plus a worked finding→PoC map.
- `references/isolated-compile-poc.md` — compile a verbatim production class standalone (javac + annotation
  (`app/api/*`) white-box playbook: `cargo test` runtime-PoC recipe, Soroban contract bug-class
  checklist (missing admin guard, caller-supplied invariant data, no-op verification, cross-contract
  caller pinning), the fail-open/conditional-auth API checklist, and a worked example.
- `references/isolated-compile-poc.md` — compile a verbatim production class standalone (javac + annotation
  shim) to get a real runtime PoC without building the project; worked CLPR/FakeBls case.
- `references/immunefi-dlt-program-mechanics.md` — how to read an Immunefi Blockchain/DLT program page
  (rewards, prohibited activities, impact tiers, the downgrade clauses to pre-empt).
- `templates/IsolatedPocMain.java` — driver skeleton for that harness.
- `references/source-only-poc-harness.md` — drop-a-test PoC recipes for the two most common source-only
  stacks: Rust/Soroban contracts (`cargo test -p <hyphenated-name>`, `env.mock_all_auths()`, slow first
  build) and Next.js/TS API routes (`npm ci` + `vitest run __tests__/poc`, reuse the repo's `fake-db`,
  Drizzle circular-JSON assertion pitfall, corroboration-by-existing-tests).
- `references/soroban-stellar-review.md` — Soroban/Stellar + generic Rust contract review: the five
  defect classes that pay, recon/grep commands, the `cargo test` + `vitest` runtime-PoC recipe, the
  "target's own tests encode the bug" corroboration trick, and the validate→draft→manual-check order.
- `references/native-client-fail-open-casebook.md` — client+privileged-daemon reviews: the five
  fail-open shapes that pay — A: fail-open IPC client auth + Everyone DACL; B: double fail-open on a
  privacy-critical config where the callee can't return `Err` and the caller only logs; C: runtime
  toggles that disable a control; D: **failure unrepresentable in the signature** (unit-returning
  apply helper + an unconditional `Ok(())` caller, vs its own `?`-using sibling branch); E:
  **swallowed-call asymmetry by security role** (the anti-leak calls swallowed while a benign one
  propagates — the diff is the impact analysis) — with the exact code shapes, the swallowed-error
  enumeration grep, the sibling-contrast argument, per-platform call semantics
  (`SetDomains((".", true))`, `disable_dot`, `DnsSettings::save`), severity discipline, and the
  labelled-untested rule for FFI/native-only platform code.
- `references/auth-server-account-lifecycle-review.md` — PART 2e: reviewing a **web2 auth-server
  codebase** (FastAPI/Django/Express). The account pre-hijacking class (first caller's password
  persists through the victim's own sign-up + verification), the registration/verification checklist,
  the "no disable path for an enable path" severity amplifier, the local FastAPI PoC harness recipe
  (env-before-import `lru_cache` trap, `TestClient`, memory email backend, isolated SQLite per run,
  `limiter.reset()`, `DEVICE_LOCK_REQUIRE_HWID=false` to isolate logic from the device lock, the
  password-policy-rejects-email-local-part gotcha), the read-the-Caddyfile-before-claiming-XFF
  discipline, and the reportlab-PDF + multi-account Gmail-draft delivery path — with the full worked
  DedSec CCTV case (High, 3/3 validated).
