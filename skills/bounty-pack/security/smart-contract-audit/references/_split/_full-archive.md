---
name: smart-contract-audit
description: "Use when auditing Solidity/EVM smart contracts."
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    budget_kb: 20
    tags: [security, smart-contract, solidity, foundry, slither, defi, bug-bounty, audit]
    related_skills: [bug-bounty, exploit-cookbook, onchain-finding-verification]
---

## ⛔ KONTRAK INTEGRASI (WAJIB DIBACA SEBELUM PAKAI SKILL INI)

Isi skill ini **dipecah**: core ada di file ini (auto-load), sisanya di `references/_split/`.
File di `references/` **TIDAK ikut ter-load otomatis** — hanya ter-LIST saat skill dibuka.
**Karena itu: buka file di tabel bawah ini lewat `skill_view(name=..., file_path=...)`
sebelum mengerjakan bagian yang relevan. Jangan menebak dari judulnya.**

Aturan pakai:
- Bagian CORE di bawah = aturan wajib, selalu berlaku, jangan dilewati.
- Bagian yang dipisah = kedalaman per-topik. **Panggil saat pemicunya muncul, jangan dibiarkan tak terpakai.**
- Kalau ragu bagian mana yang relevan, baca `references/_split/_INDEX.md` dulu (satu file, murah).

### Tabel pemicu → file (WAJIB dipanggil saat kondisi terpenuhi)

| kapan dipanggil | file |
|---|---|
| saat mengerjakan: **Workflow — 6-Phase Smart Contract Audit** | `references/_split/01-workflow-6-phase-smart-contract-audit.md` |
| saat mengerjakan: **Critical Pitfalls** | `references/_split/02-critical-pitfalls.md` |
| saat mengerjakan: **References** | `references/_split/03-references.md` |
| saat mengerjakan: **Appendix A: Solana Program Analysis (RPC-based, no source needed** | `references/_split/04-appendix-a-solana-program-analysis-rpc-based-no-source-nee.md` |
| saat mengerjakan: **Deployed-vs-source selector diff (do this EARLY on any deployed ** | `references/_split/05-deployed-vs-source-selector-diff-do-this-early-on-any-depl.md` |
| saat mengerjakan: **Companion Skills** | `references/_split/06-companion-skills.md` |
| butuh daftar lengkap split / arsip | `references/_split/_INDEX.md`, `references/_split/_full-archive.md` |


# Smart Contract Audit — Solidity/EVM DeFi



## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

**Complete workflow for auditing Solidity smart contracts on Ethereum/EVM chains.**
Covers: source acquisition, Foundry setup, static analysis, PoC development, finding verification.



## ⛔ VERIFICATION
Before claiming audit complete, run:
```bash
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-checkpoint.py <target_dir> --phase 0C
```
Checkpoint reads actual tool output files from disk (slither, aderyn, mythril reports).



## ⛔ TOOL ENFORCEMENT (MANDATORY)
Setiap tool di playbook ini WAJIB dijalankan. Bukan "sudah install" = selesai.
Baca reference files → ikuti panduan tool → eksekusi → buktikan dengan terminal output asli.

Bukan hanya sebut nama tool. JALANKAN:
- slither . → wajib, baca output findings-nya
- aderyn . → wajib, baca report-nya
- mythril → via WSL (wsl -d Ubuntu -- myth analyze)
- echidna → dengan config yang benar, jalankan fuzzing
- medusa → jalankan dengan test mode
- halmos → jalankan symbolic execution
- manticore → jalankan symbolic analysis
- z3 → jalankan formal verification
- crytic-compile → kompilasi dulu kalau ada error

Kalau ada tool yang error → FIX dulu, jangan skip.
Slither/Aderyn output KOSONG? = Tidak jalan = JANGAN claim complete.
Baca reference file tool-nya → ikuti langkah yang ada → JALANKAN.

⛔ **Slither/Aderyn/echidna/medusa mati di forge ≥1.7?** `--build-info`-nya tidak lagi hardhat-shaped →
`KeyError: 'output'`. Fix (sintesis build-info), shortcut echidna `--compile-force-framework solc`,
perangkap prefix property echidna vs medusa, thrash halmos, DAN cara benar membandingkan bytecode
deployed vs source (**bandingkan code section, bukan panjang** — metadata menyimpan path source):
`references/forge-buildinfo-and-deployed-source-verification.md`.



## ⛔ TOOL-COVERAGE LEDGER (MANDATORY before saying "done"/"deepdive")

User demands this EVERY engagement, repeatedly: *"sudah deepdive lagi? pakai all tools
dan varian attack yg blm dicoba"*. Answer with a **table of tool → result**, never narrative.

Required shape — one row per tool, and it MUST include:

| column | rule |
|--------|------|
| tool | every tool in the playbook above, plus any variant you added |
| result | `clean (N)` / `N findings, all FP after review` / `BLOCKED: <reason>` / `NOT RUN` |
| evidence | the artifact path on disk (`scanners/...`), so the row is checkable |

Non-negotiable sub-rules:
1. **Negatives are deliverables.** "0 callback", "0 ffuf hits", "no desync", "6 High → all FP"
   get written down with a one-line reason. Silently omitting a tool you did not run =
   overclaiming.
2. **List NOT-RUN items explicitly as gaps.** A ledger with no gaps is implausible on a
   real target; say which tool was skipped and why.
3. **Distinguish "tool found nothing" from "coverage won".** Shallow tools are weak
   evidence: mythril reported `No issues were detected` on 12 contracts yet missed the
   actual finding (F-1) that manual review + a fork PoC caught. Write that caveat down.
4. **Never quote a tool's self-label as a finding.** `[critical] config-json-exposure` may
   be a public site key / feature flag; open the body and judge it, then write
   "FP, verified" so it cannot be double-counted.
5. **A tool's failed run is not a result.** If a tool errored before the fix (e.g. mythril
   `ParserError` before the remapping patch), label that artifact as tooling failure in
   the directory README — never let a stale failure log be read as an analysis outcome.
6. **Severity counts come from the machine-readable artifact, never from the console.** `slither`'s
   console output carries **no `Impact:` field**, so counting `High`/`Medium` by grepping it yields a
   *formatting artefact* that is indistinguishable from a measurement — mid-session I nearly published
   "0 High / 0 Medium" from zero matches before checking the format. Parse `--json`
   (`results.detectors[].impact`) and quote the counts from there. General rule: **if the number you are
   about to publish came from grepping rendered tool output, it is not evidence yet.**
7. **Same tool run twice on one target → keep the failure and the success in DIFFERENT filenames.**
   When a tool needs a flag fix (mythril's `--solc-json` viaIR), the pre-fix attempt and the fixed run must
   not collide: `X.txt` = the `Stack too deep` failure, `X.viair.txt` = the clean run. Same concern as
   rule 5, but it bites exactly when a plain `>` redirect would overwrite, or a reader grabs the wrong log
   and reports a tooling failure as a clean sweep.
8. **Fuzzers announce degraded mode in prose, mid-log — grep every log for it.** `echidna` emits
   `Running slither failed. Echidna will continue, however fuzzing will likely be less effective.`
   A green property table does **not** mean the campaign ran normally, and its slither-guided fuzzing is
   what makes the coverage meaningful. Scope the caveat precisely instead of hiding it or over-applying
   it: *"15 of 16 runs slither-guided; 1 degraded (name it)"*. That is the difference between
   "no counterexample" and "the invariant is safe" — and it is also the honest framing when a re-run
   reproduces the degraded state deterministically (then it is a property of that harness, not of your
   machine).



## When to Use

- Targeting a Solidity/EVM DeFi protocol for bug bounties
- Analyzing smart contracts for vulnerabilities
- Writing PoC exploit tests for on-chain findings
- User says "audit this contract" or "analyze smart contract"



## Inputs

- **target** — contract address(es) or source code path
- **bounty_url** — Immunefi/code4rena/Sherlock bounty link (optional)
> **Immunefi severity = VSS v2.3, not CVSS.** Impact must come from the program's official impact list and the asset from its official asset list; elevated privilege / uncommon interaction downgrades or rejects. Tables + out-of-scope: `skills/security/bug-bounty/references/immunefi-vss-v2.3.md`

> **⛔ Do NOT reach for a browser to read an Immunefi program's scope.** `immunefi.com` renders the
> program data client-side, but the whole payload is also present in the server HTML as escaped JSON.
> A plain `curl` recovers the exact name↔address table, the impact list with severities, the reward
> tiers and the out-of-scope rules in one shot — no JS rendering, no Camofox/CDP:
> ```bash
> curl -s -A "Mozilla/5.0" "https://immunefi.com/bug-bounty/<slug>/information/" -o p.html
> curl -s -A "Mozilla/5.0" "https://immunefi.com/bug-bounty/<slug>/scope/"       -o s.html
> # unescape (\u00xx / \" ) then regex for:  \"assets\":[{...}]  \"impacts\":[{...}]  \"rewards\"
> ```
> Each asset entry is `{"url":"https://bscscan.com/address/0x…","type":"smart_contract",
> "description":"<ContractName>", "isPrimacyOfImpact":…}` — note the chain is whatever the explorer
> URL says, which is **not necessarily Ethereum** (DeXe's 10 in-scope assets are all BSC). There is
> also a `\"vault\"` block with the payout address. Set `web.extract_backend` aside: it is search-only
> (`ddgs`) and will answer `cannot extract URL content`.

> **Immunefi intake: the scope table is inside the page HTML, and the CHAIN is not a given.**
> `/information/` and `/scope/` render client-side, but the server HTML already carries an escaped
> JSON blob with the whole asset list — `curl` + regex beats a headless browser (and works when
> the browser backend is down):
> ```bash
> curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0" \
>   "https://immunefi.com/bug-bounty/<program>/scope/" -o scope.html
> python - <<'PY'
> import re
> t = open('scope.html', encoding='utf-8', errors='ignore').read()
> i = t.find('\\"assets\\"')
> print(t[i-200:i+9000].encode().decode('unicode_escape'))
> PY
> ```
> Gives `{id, url, type, description, isPrimacyOfImpact}` per asset plus the full `impacts[]`
> list with severities. `description` is the **contract name** (`PoolRegistry`, `SphereXEngine`,
> …) — that is the key you map onto the repo's file list.
> **Read the explorer host inside each asset `url` before assuming a chain.** A program can list
> every in-scope deployment on BSC (`bscscan.com/address/0x…`) while its repo, audit PDFs and
> docs are all Ethereum-shaped; the live chain is what the bounty is about. Also note the
> *stated* "last updated" date can lag the repo `HEAD` — verify identity rather than trusting it.
- **chain** — ethereum, base, polygon, etc.



## Impact Analysis
As an attacker, I could:
- [Specific action 1 with concrete consequences]
- [Specific action 2 with concrete consequences]
- [Specific action 3 with concrete consequences]

Business Impact: [What the protocol/users lose]
```
This format forces honest assessment: if you can't write concrete attacker actions,
the finding is probably informational, not exploitable.

### Phase 4b: Deep Dive Systematic Testing (30-120 min)

**After initial PoC, run a SYSTEMATIC 17-vector deep dive on the finding.**
Every vulnerability has multiple attack surfaces — test ALL of them.

**The 17-Vector Framework (for allocator/distributor/role-based contracts):**

| # | Vector | What to test |
|---|--------|-------------|
| V1 | Basic drain to zero | Can attacker set allocation to 0, withdraw all? |
| V2 | Multi-user atomic drain | Can attacker batch-drain N users in one tx? |
| V3 | Stealth partial drain | Can attacker reduce to 1 wei (appear benign)? |
| V4 | Below-claimed revert | Does contract prevent reducing below claimed amount? |
| V5 | Partial claim then drain | Can attacker claim some, drain the rest? |
| V6 | Cross-allocator drain | Can allocator A drain allocator B's deposits? |
| V7 | Front-run claim | Can attacker front-run pending claim tx? |
| V8 | Self-allocate + claim | Can allocator deposit to self and immediately claim? |
| V9 | Admin emergency drain | Can admin bypass allocations entirely? |
| V10 | Pause inconsistency | Does pause protect ALL state-changing functions equally? |
| V11 | Reduce to claimed boundary | What happens at exactly the claimed amount? |
| V12 | Reduce events | Are events emitted correctly for monitoring? |
| V13 | Instant drain (no timelock) | Is there any reaction window? |
| V14 | Gas limit / bounded loop | Can batch drain fit in one tx? How many users? |
| V15 | Reduce then reallocate | Can attacker redirect drained tokens to new address? |
| V16 | Selective token drain | Can attacker drain one token, leave others? |
| V17 | Emergency + reduce combo | Does emergency withdraw leave phantom allocations? |

**Run this AFTER initial PoC passes. The goal: find vectors the initial analysis missed.**

**Foundry test structure for deep dive:**
```solidity
contract DeepDive is Test {
    RD rd; MockReward tok; address allocator = makeAddr("alloc");
    address user1 = makeAddr("user1");

    function setUp() public {
        // Deploy with IDENTICAL configuration as production
        // Set roles exactly as they are on-chain
    }

    function _fundAndAlloc(uint256 amount) internal {
        // Helper: fund allocator + call addAllocations
        // Must match the exact on-chain flow
    }

    function _a1(address u, uint256 amt) internal pure returns (RD.Allocation[] memory) {
        // Helper: single allocation array
    }

    function _a2(address u1, uint256 a1, address u2, uint256 a2) internal pure returns (RD.Allocation[] memory) {
        // Helper: dual allocation array for batch tests
    }

    function test_V1_basicDrain() public { /* ... */ }
    function test_V2_multiUserDrain() public { /* ... */ }
    // ... all 17 vectors
}
```

**Key test patterns:**
- Use `vm.prank(allocator)` for allocator calls (NOT `vm.startPrank`)
- `vm.startPrank` + `new Constructor()` fails — one-shot `vm.prank` before `new`
- OZ v5 `_transfer` NOT virtual — test tokens must use manual IERC20, not inherit OZ ERC20
- Struct names from external contracts must be qualified: `Contract.StructName` (not bare `Name`)
- Batch writes >8K tokens to files — split into multiple writes



## Deployed-vs-source verification (do this BEFORE trusting the repo)

For a live proxy / upgradeable / dispatcher-with-delegated-modules target, the repo is a **claim**, not
evidence. Measure it. Full recipe: `references/deployed-vs-source-module-architecture.md`.

1. Recover the **live** source per address from Blockscout `/api/v2/smart-contracts/{addr}` (the
   Verifier-Alliance / eth-bytecode-db record) and read its `compiler_settings`: `viaIR`,
   `optimizer.runs`, `evmVersion` and the **remappings** — the remappings pin the npm dep versions and
   the source-path prefix the deploy build used (`project/contracts/...`).
2. Compare `forge inspect <C> deployedBytecode` against `cast code <addr>`.
   ⛔ **Never judge equality or difference by LENGTH.** The metadata appended to the bytecode embeds the
   *source paths* of the contract's closure, so a `project/contracts/...` build is tens-to-hundreds of
   bytes longer than a `contracts/...` build with byte-identical code (this produced a bogus
   "unpublished code" alarm on an SSV module that was in fact byte-identical). Compare the **code
   section**; a diff confined to the last ~51 bytes plus a 32-byte blob is metadata/IPFS noise.
3. Immutable differences are expected: forge zeroes them, the chain holds the constructor value. OZ 4.9
   `UUPSUpgradeable` has `address private immutable __self = address(this)`, so the implementation
   legitimately carries its own address — not a misconfiguration.
4. If the code really differs, look for the **deployment branch** before assuming the source is
   unpublished: `git ls-remote --heads origin`, then grep each candidate (`deploy/hotfix`, `deploy/*`,
   `fix/<finding-id>`) for the distinguishing lines, then
   `git diff --stat <default>..<branch> -- contracts/`.
5. Prove the module/impl swap on chain via the `ModuleUpgraded(uint8,address)` logs — the block numbers
   give you the patch timeline.
6. **Read the default branch AND the deploy branch.** An audit's stated "final commit for launch" can be
   tens of lines behind the live build; that gap changes which bugs are live *and* whether an
   "already known / already fixed" defence even applies. On SSV the live modules were `deploy/hotfix`
   = default branch + 10 lines, and that source is absent from the audited commit.

### ⛔ A `view` interface function is a STATICCALL — no reentrancy through it
Before writing "malicious X re-enters Y", check the callee's declared mutability. If the interface
declares the hook `view` (e.g. `ISSVWhitelistingContract.isWhitelisted`, `ICSSVToken.balanceOf`),
solidity compiles that call to STATICCALL and **any** state change inside the callee reverts, so the
hypothesis is impossible — one read of the interface file kills it. A function that merely lacks
`nonReentrant` is not vulnerable when every external call it makes is a staticcall or a transfer of a
fixed, trusted ERC-20.

- **Never pass `--solc 0.8.28`** to slither — it treats the value as an executable path and
  dies with `FileNotFoundError: [WinError 2]` / `InvalidCompilation`. Let forge select solc.
- `forge test` additionally needs the NESTED submodule `lib/forge-std/lib/ds-test`.
- `vm.envString: environment variable "RPC_URL" not found` on fork tests is an ENVIRONMENT
  result, not a code failure — exclude those from PASS/FAIL when reporting suite health.
- **⛔ Fork suites need an ARCHIVE node, and a non-archive RPC fails in a way that looks like a
  target bug.** Supplying a live-read RPC is not enough: `ethereum-rpc.publicnode.com` answers
  `-32602 Archive requests require a personal token` and flashbots answers `state at block #N
  is pruned`, which surfaces per-account as
  `[FAIL: EVM error; database error: failed to get account for 0x5615dEB7…]` — Foundry's own
  deployer, not the target. `https://eth.drpc.org` serves the historical state; the same
  redemptions suite went from "6 failed" to **231 passed / 0 failed** once it was used. Report
  the first outcome as *provider capability gap / re-run pending*, never as failing tests.
- **⛔ `slither` can exit 127 while the analysis fully succeeded.** Verify by the artifact's
  final summary line (`analyzed (N contracts …), M result(s) found`), not by `$?`.
- **⛔ slither 0.11.6 `AssertionError` at `slither/slithir/operations/member.py:33`** — a bare
  `AssertionError` with no message and no source line, raised by `Member(expr, …)` when the
  member-access receiver is not an rvalue. In practice it is a **member access on an array
  literal**, nearly always `[a, b].asDynamic()` (the `@solarity/solidity-lib` idiom that
  DeXe-style code uses for fixed-length view args) or a `.call{value: …}` chain. It kills the
  whole run for that file, so you get no detectors at all — **record it as NOT RUN, never as
  "clean"**. Two workarounds were tried and **both fail** (do not re-burn time on them):
  (a) skipping the `Member` node in `expression_to_slithir._post_member_access` makes the call
  target a `ReferenceVariable` and `convert.extract_tmp_call` then dies with
  `SlithIRError: Not extracted <class '…reference.ReferenceVariable'> TMPCALL0 REF_…`;
  (b) relaxing the assert inside `Member.__init__` reaches the identical `SlithIRError`.
  What works, cheapest first: (1) scan a throwaway copy with the array literals hoisted into
  named locals — those expressions rarely carry the finding anyway; (2) upgrade/pin a slither
  that handles tuples; (3) manual-review that file and list it explicitly as a coverage gap.
  Prove the patch is reverted afterwards, or a later engagement inherits a silently-wrong tool.
- If the repo's own tests import a SIBLING repo's submodule through a literal relative path
  (e.g. `../../lib/ustb/lib/onchain-redemptions/src/interfaces/IRedemptionIdle.sol`), that
  nested dir is empty on a shallow clone but resolves against the project root, so a remapping
  cannot fix it — copy the source in: `cp -r src lib/<sibling>/lib/<repo>/`. Also pin
  `remappings.txt` with `<lib>/=lib/<lib>/` (no `/src`) for that sibling, or `ustb/src/x.sol`
  becomes `ustb/src/src/x.sol`. Symptom to expect: the two sibling test files import the same
  file via *different* paths — that inconsistency is a copy-paste artefact in the vendor repo,
  not a missing contract.
- 600–750 slither results is normal; ~95% is `unused-state`/`constable-states`. Triage by
  detector name and filter to `src/` to drop `lib/forge-std/**` and `script/**` noise.

### ⛔ Testing an upgradeable implementation DIRECTLY does not work

Implementations call `_disableInitializers()` in the constructor, so `new Impl()` +
`impl.initialize(...)` reverts `Initializable: contract is already initialized`. Deploy behind
an `ERC1967Proxy` to exercise initializer logic. Immutables live in the implementation
bytecode (not proxy storage), so an immutable that no constructor assigns reads as zero
through delegatecall — that is how a fresh-deploy ownership dead-end gets proven.

> Full detail + the recovered-artifact workflow:
> `references/repo-bootstrap-and-onchain-source-recovery.md`



## Companion Skills

- `bug-bounty` — General bounty workflow, scope analysis, reporting
- `exploit-cookbook` — Proven exploitation playbooks (Web2 + Web3)
- `onchain-finding-verification` — Staged verification before reporting on-chain findings
- `live-vs-source-bytecode-forensics` — prove which source is *actually* deployed (verifier-alliance source
  recovery, code-section vs metadata/path comparison, locating the deployed branch, and the Foundry
  build-info workaround that unblocks slither/aderyn/echidna on `forge` ≥1.7)
- `bug-report-delivery` — Final report format and delivery



## Supporting files

- `scripts/deployed_vs_source_selector_diff.py` — measures whether the deployed contract is the
  source you were handed (source `methodIdentifiers` vs live `cast code`; prints the selectors
  missing on chain). Run it before reporting anything sourced from a bundle.
- `references/auditing-a-vendor-source-bundle.md` — setting up a Foundry project around a vendor
  source ZIP / `/source/` page (remappings, dependency install, `via_ir` and its compile-cost rules,
  self-contained-vs-fork PoC choice, the approve-the-staked-token pitfall, capturing live state as
  evidence).
