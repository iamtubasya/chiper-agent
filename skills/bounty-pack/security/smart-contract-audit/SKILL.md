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
| **audit apa pun yang punya `nonReentrant`** — cek apakah guard-nya DEPTH-COUNTED (guard tak berkedalaman = dana in-flight bisa dicuri; ada template PoC 3-test + jebakannya) | `references/reentrancy-guard-depth-counting.md` |
| **sebelum menulis klaim "novel"** — grep repo target utk kelas bug-nya (test/commit bisa menyebutnya), baca **apa yang audit terbitan benar-benar cakup** (VM/bahasa bisa beda), dan pisahkan deployment yang sudah digantikan dari yang masih live | `references/protocol-recon-before-claiming-novelty.md` |
| **kontrak yang menyimpan dana** — kalau akuntansinya HANYA lewat event (tak ada mapping saldo), maka `depositor`/`id` yang dikendalikan pemanggil = atribusi bisa dipalsukan gratis. Juga: mencari kontrak-dana yang TIDAK ada di repo (via API protokol sendiri) | `references/event-only-accounting-and-attribution.md` |
| **protokol multi-chain / CREATE2** — enumerasi SEMUA deployment, uji perilaku bytecode per-chain via fork (registry ≠ yang live), label verdict yang bisa terbalik, jebakan hex/RPC | `references/multi-deployment-scope-verification.md` |
| **protokol intent/bridge yang MENURUNKAN alamat deposit per-order dari kunci master** (TEE/MPC, path BIP32 non-hardened dari field order) — sebelum menuduh "collision → dana dicuri": cek (1) apakah field yang bebas itu benar-benar memberi JALUR KORBAN (field bebas = alamat penyerang sendiri, bukan collision), (2) **asal `salt`** — `randomBytes(32)` memblokir, counter/timestamp tidak, (3) apakah order-binding (`getOrderId`, signature solver, `derivationFields.solver`) sudah ada. Juga: pisahkan temuan DERIVASI dari temuan AKUNTANSI, jangan digabung | `references/intent-order-derivation-review.md` |
| **kontrak yang bersandar pada tanda tangan / attestation off-chain** (pricing oracle, resolver payload, deposit-address manager, `try/catch` "pakai oracle on-chain kalau bisa") — tiga bentuk cacat nyata: (1) **field yang ditandatangani tapi TIDAK pernah divalidasi** (`publishTime` di digest, nol pembacaan), (2) **`catch` menelan SEMUA revert** → jalur fallback bisa dipilih pemanggil, "prefer" jadi tak bisa ditegakkan, (3) **docstring bilang "downstream consumers CAN verify"** → kontrak on-chain cuma pencatat; cari konsumennya, kalau tak ada di repo **jangan klaim exploit** — label hardening. Termasuk kasus cermin: potongan di luar commitment yang ternyata terikat hal lain (jangan dilaporkan sebagai celah) | `references/oracle-signed-message-and-commitment-review.md` |
| **kapan pun sebuah tes GAGAL, kompilasi error, atau log tampak berhenti** — sebelum menyalahkan target: kontrol merah = rig rusak (EOA-dipakai-sebagai-kontrak → returndata kosong → decode revert) · `Yul stack too deep` = optimizer-mu mati, cerminkan `foundry.toml` mereka · log diam ≠ run mati (cek penghitung bukti + state file) · label verdict bisa terbalik (baca arah assertion) · `patch` yang menghapus baris `def` tetap lolos `ast.parse` (grep simbolnya kembali) | `references/harness-artifacts-vs-target-defects.md` |
| **klaim severity apa pun soal role/admin/upgrade** (\"facilitator bisa pindahkan dana\", \"admin bisa upgrade\") — sumber cuma bilang KEMAMPUAN; yang menentukan severity adalah PEMEGANGNYA sekarang: EOA vs Safe vs timelock, plus eksposur terukur. Resep: hash role → `eth_getLogs` di jendela deployment (cap 10k blok, ⛔ topik nested bisa balik 0 tanpa error) → `hasRole` untuk state sekarang → `eth_getCode` untuk klasifikasi pemegang (EOA / Gnosis Safe 3-of-7) → saldo native+ERC20 | `references/onchain-privileged-role-and-deployment-forensics.md` |
| **menjalankan fuzzer (medusa/echidna) pada kontrak upgradeable + role-gated, atau menulis "fuzzer bersih"** — harness WAJIB di `contracts/` (di `test/` ia tak dikompilasi crytic: medusa *"no property found"*, echidna *"contract not found"*) · impl UUPS `_disableInitializers()` perlu proxy ERC1967 (30 baris cukup) · harness pegang DEFAULT_ADMIN utk fixture (mis. `setTokenWhitelisted` sebelum `depositToken`, kalau tidak revert `AssetNotSupported`) sedangkan role yang diuji alamat lain · ⛔ falsifikasi yang trace-nya TIDAK menyentuh kontrak = bug SPESIFIKASI, bukan temuan · log ke path ABSOLUT + buktikan hidup via delta CPU, bukan ukuran log | `references/invariant-fuzzing-campaigns.md` |
| **kontrak yang source-nya TIDAK ada di repo** — harus di-recover dari chain (Uniswap-V4 module, proxy+beacon) | `references/uniswap-v4-module-audit.md` |
| **kontrak UNVERIFIED di Etherscan + heimdall source-gen (beta) gagal** — ABI tetap bisa didapat dari heimdall; uji access-control TIAP fungsi via `eth_call` dari address arbitrary (REVERT=gated / OK=calon unprotected); Etherscan **V2** (V1 deprecated); batas jujur: sig-verification/replay/accounting TETAP butuh source | `references/unverified-contract-abi-ethcall-recon.md` |
| **target Solana/Anchor — perlu BUKTIKAN on-chain accept/reject tanpa fee/mainnet** (LiteSVM setup, .so extraction, account cloning, Borsh args, discriminator dari IDL, Windows OpenSSL/vcpkg, API pitfalls) | `references/solana-litesvm-onchain-exploit-testing.md` |
| **menyiapkan scanner suite (slither/aderyn/mythril/echidna) di host Windows lewat WSL** — shim `forge` untuk crytic-compile, flag per tool (`--solc-remaps` satu argumen comma-separated; mythril TANPA remap flag), crash `pyth_unchecked` yang muncul di akhir run, path tanpa spasi | `references/wsl-scanner-toolchain-windows-host.md` |
| **membuat harness Foundry end-to-end untuk stack DeFi ber-governance** (hub→vault→controller→diamond→oracle), MockPyth window, timing round, pitfall `vm.prank` habis oleh staticcall argumen, getter struct tuple penuh | `references/foundry-poc-harness-defi-stack.md` |
| **target pakai circom / Groth16 / Halo2 / zkVM guest (SP1, RISC Zero) — atau repo-nya pakai `pragma` solc yang BELUM dirilis sehingga forge/slither tak bisa compile** — cek (1) padding slot, (2) witness↔public equality, (3) **lubang `isOld0` di circomlib `SMTVerifier`** (tanpa `smtIsOld0*(smtIsOld0-1)===0` prover bisa buktikan nullifier TERPAKAI sebagai "belum ada"), (4) range bound `LessThan`, (5) guest *re-derive* vs *trust* public field, (6) read-path liveness sweep + teknik **revert-selector → custom error** untuk target yang tak bisa dikompilasi | `references/zk-circuit-and-guest-review.md` |
| **program bounty-nya DISCRETIONARY** (bayar hanya untuk impact set bernama: fund-loss / unauthorised mint / admin takeover / pricing-accounting manipulation; griefing + theoretical + privileged-access di-exclude) — ubah tiap klausa reward jadi INVARIAN yang bisa dites, lalu buktikan/bantah | `references/discretionary-scope-defi-invariant-audit.md` |
| butuh daftar lengkap split / arsip | `references/_split/_INDEX.md`, `references/_split/_full-archive.md` |


# Smart Contract Audit — Solidity/EVM DeFi

## ⛔ DELIVERABLE CADENCE (user-stated, every engagement)

User, verbatim: *"tulis dl dlm draft utk oN, lengkap poc pdf, baru lanjut oN+1"* — and the
standing rule *"1 temuan = 1 draft/email/PDF/PoC"*.

So the order is **per finding, not per engagement**: finish the finding's own complete artifact
(PoC that runs → evidence image → report PDF → staged Gmail draft, verified) **before** starting
the next finding. Do not batch several findings and write the reports at the end; the user sends
each one as it lands, and a finding with no PDF is not delivered.

Corollaries learned the hard way:
- **Never silently re-create an artifact the user already consumed.** A draft id that 404s has
  usually been *sent* (Gmail deletes the draft on send). Treat that as "delivered", mark it
  loudly (`<-- RECREATED: tracked draft was missing (already sent?)`), and sweep the mailbox for
  duplicates per attachment at the end of staging. Silent self-healing on a consumed id is how a
  duplicate lands in the user's outbox.
- **Do not delete a stray/duplicate draft without asking.** State the situation and let the user
  decide.
- **Evidence that arrives AFTER the report was sent → stage a FOLLOW-UP, never a re-send.** Order-of-work
  reality: the operator sends finding N the moment it is verified, and *then* a deeper pass produces sharper
  proof for the same finding (worked case: on-chain role holders for an escrow finding — FACILITATOR_ROLE held
  by a plain EOA with 2.17M txs vs DEFAULT_ADMIN_ROLE on a 3-of-7 Gnosis Safe, plus the current escrow balance).
  Do not rewrite the sent draft and do not create a second finding for the same root cause. Stage **one**
  addendum email (`[SECURITY][Follow-up] <contract> — <what the new evidence answers>`), body = what it adds →
  who holds what now (with the exact `eth_call`/`eth_getLogs` to reproduce) → what you did NOT do (no tx, no key,
  no brute force) → remediation unchanged; attach a small PDF built to the same rule (rebuild until the layout
  QA is clean). Then verify the staged draft the same way as any other: exactly one draft for that subject,
  attachment sha256 == the local file. Mark it in the engagement log as *post-report material*, unsent until the
  operator says so — the operator submits, always.
- A per-finding negative result still gets written down (finding → result → reason), but it does
  not need a PDF.



## ⛔ DeFi/crypto target = TWO-SIDED (smart contracts PRIMARY, web2 frontend secondary)

A DeFi/crypto bounty — lending/money-market, DEX, perp, ve-token/tokenomics, staking, restaking,
bridge, ERC-4626 vault — is PRIMARILY a smart-contract target. The "platform" frontend/API is
usually thin and only yields Low/Info (bundle secrets, open proxy, subgraph auth). Getting called
out for "you didn't check the web3 side" means you treated a DeFi target as a web2 target: you
read the bug-bounty page and swept app.<x>.io's JS bundle + api.* while never opening the
contract repos. Attack ORDER (do BOTH, never stop at the frontend):

1. on-chain: clone BOTH contract repos (Core immutable + Modules), run slither/aderyn + `cast`
   live-state forensics (owner, risk params, oracle addresses, numMarkets), and MANUALLY review
   the money-path — deposit/withdraw/borrow/liquidate + solvency invariant, price oracle, ERC-4626
   vault (par-denominated ⇒ first-depositor inflation is N/A, run the multi-party kill-test),
   wrapper/unwrapper traders (cross-vault theft guard), vesting/claims/airdrop. "No bug" is
   claimable only after the tool-coverage ledger + FP-adjudication pass, NOT after reading the frontend.
2. web2: bundle secrets, open proxy, subgraph API auth — nice-to-have, seldom above Low.

Report/draft delivery for this class: one `.md` per finding; the email body carries the FULL report
(location + impact + repro + remediation), and the `.md` is attached — NEVER a summary-pointer body
plus an attachment. ("isi full donk, kok nanggung" — the user wants the whole report in the body.)

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

**Complete workflow for auditing Solidity smart contracts on Ethereum/EVM chains.**
Covers: source acquisition, Foundry setup, static analysis, PoC development, finding verification.

## ⛔ ENUMERATE THE WHOLE REPO BEFORE AUDITING ANY OF IT

On a monorepo, `packages/` is frequently the *support* code (SDKs, ABIs, indexers, Lit
actions, deployment JSONs) while the contracts live in a **sibling top-level directory**. Cost
of getting this wrong is the whole first half of an engagement: on relay-settlement I audited
`packages/*` — SDK message types, an Express indexer, attestation helpers — for hours, and only
found `smart-contracts/contracts/**` (177 `.sol` files: funding pools, resolvers, oracles,
payload builders) much later. Everything I had analysed was periphery; the money-path
contracts were one directory over.

**Do this first, always, before reading a single contract:**

```bash
# 1. top-level layout — not just packages/
ls -d */ ; ls -d */*/ 2>/dev/null | head -30

# 2. where do the .sol files ACTUALLY live, and how many per root?
find . -name '*.sol' -not -path '*/node_modules/*' -not -path '*/lib/*' \
  | cut -d/ -f2 | sort | uniq -c | sort -rn
#   a small count under packages/ + a large one under smart-contracts/ = you were about to audit the wrong tree

# 3. the money-path entry points, by name, wherever they are
find . -name '*.sol' -not -path '*/node_modules/*' \
  | grep -iE 'pool|vault|router|deposit|oracle|resolver|bridge|factory' | sort
```

**Also check for a nested monorepo** — `packages/<x>/packages/<y>/src/` is how `ethereum-vm`
contracts hide inside a `packages/depository/` that looks like a sub-package. And ABI
directories are a trap: `packages/abis/src/abis/<name>.sol/` often holds **only
`<name>.json`**, so `find -name '*.sol'` matches a *directory* and reads as "source present"
when there is none. Confirm a hit is a file with content (`wc -l`), not a dir.

**Rule:** name the directory that holds the money-path contracts, and the count of contracts
in it, in your ledger before you start. A coverage claim that does not say *which tree* it
covers is not a coverage claim.




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
7. **Two explorer hosts can serve the SAME chain's data — verify chain identity before trusting an
   explorer, and never infer "deployed on the testnet" from an explorer record alone.** On Vana the
   documented Moksha explorer API (`api.moksha.vanascan.io`) returned **mainnet** data: the same escrow
   record AND an identical block hash at the same height as the mainnet explorer, while the two chains are
   genuinely distinct (`eth_chainId` 1480 vs 14800, different implementation addresses). Decisive check,
   ~10 s: compare one block hash across both explorer hosts
   (`/api/v2/blocks/<height>` → `hash`) and read `eth_chainId` from each RPC. A coincidental match is
   impossible — same hash = same chain data, whatever the hostname says. Related: the SAME CREATE2 address
   can exist on both chains with DIFFERENT implementations, so read the EIP-1967 slot **per chain** and
   then diff the runtime bytecode (an identical build differs only in the `__self` immutable — 4 groups of
   hex, not a different program).

### ⛔ A `view` interface function is a STATICCALL — no reentrancy through it
Before writing "malicious X re-enters Y", check the callee's declared mutability. If the interface
declares the hook `view` (e.g. `ISSVWhitelistingContract.isWhitelisted`, `ICSSVToken.balanceOf`),
solidity compiles that call to STATICCALL and **any** state change inside the callee reverts, so the
hypothesis is impossible — one read of the interface file kills it. A function that merely lacks
`nonReentrant` is not vulnerable when every external call it makes is a staticcall or a transfer of a
fixed, trusted ERC-20.

### ⛔ A `msg.sender`-keyed guard is a FLAG, not a depth counter — check the exit path
A guard that stores `msg.sender` and allows the contract to reenter itself will be **disarmed** if its
clear step runs unconditionally: a nested frame that is allowed (a `cleanup*` call whose `target` is the
router itself — the documented multicall recipe) passes, then zeroes the slot on exit, and every later
entry in that transaction passes the `storedSender != address(0)` check. The protected asset is the
contract's **transient balance**, i.e. in-flight funds. Grep the fix shape too
(`if (isOutermostCall) _nonReentrantAfter();`): if the repo has it and the deployed code does not, that
difference *is* the finding. Full detection, PoC discipline, and the "read the vendor's own test suite
for a `VIG###` known-issue ID" step: `references/reentrancy-guard-and-approval-defects.md`.

- **Never pass `--solc 0.8.28`** to slither — it treats the value as an executable path and
  dies with `FileNotFoundError: [WinError 2]` / `InvalidCompilation`. Let forge select solc.
- **Single-file slither on a yarn-workspaces/hardhat(+foundry) monorepo that fails auto-detection — skip the
  framework, force `solc` directly.** `slither <contract.sol> --compile-force-framework solc` with
  `--solc-remaps` pointing at ABSOLUTE `node_modules` paths resolves imports without a full build. On MSYS the
  repo root is `$(cygpath -w $(pwd))`:
  ```
  slither packages/tokenomics/contracts/VestingClaims.sol \
    --compile-force-framework solc \
    --solc-remaps "@openzeppelin/=$(cygpath -w $(pwd))/node_modules/@openzeppelin/ @dolomite-exchange/=$(cygpath -w $(pwd))/node_modules/@dolomite-exchange/ @chainlink/=$(cygpath -w $(pwd))/node_modules/@chainlink/" \
    --exclude-dependencies --json out.json
  ```
  Failure modes this bypasses: hardhat auto-detect → `artifacts/build-info is not a directory` (it wants a
  real `npx hardhat compile` first); foundry auto-detect → `Compiler run failed … "@dep/x.sol" not found`
  (incomplete `foundry.toml` remappings — e.g. a monorepo that remaps only `@openzeppelin` and one sibling
  package while imports reference many more `@org/*` scopes). Correctly CAPPING solc on a top-heavy
  monorepo: resolve the remapping AND run one contract at a time, because imports pull the whole closure.
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

- `references/zk-circuit-and-guest-review.md` — **target ber-proof (circom/Groth16/Halo2/SP1 guest) atau repo yang `pragma`-nya belum dirilis**: urutan lapisan yang harus dibaca (guest > circuit > kontrak > indexer JS), teknik **revert-selector → custom error** untuk target yang tak bisa dikompilasi, **read-path liveness sweep** (freeze collateral + liquidation mati = Medium, dan bagian struktural mana yang bertahan saat vendor bilang "itu ops"), ⛔ **umur freeze diukur dari storage, BUKAN dari sweep accessor** (`sampleOf()` atas indeks yang diharapkan balik 0 walau ring 128/128 penuh — hitung `behind = expected - newest`), 12-item checklist circuit (padding slot, witness↔public, **lubang `isOld0` circomlib SMTVerifier**, range `LessThan`, floor+remainder, accumulator off-by-one, nullifier binding, sigma lintas-kurva, dan **tes ikat public-input lewat titik `IC` di verifying key** — titik identity = input tak terikat), ⛔ **crate kripto murni bisa `cargo test` native walau solc tak ada** + **setiap tes negatif WAJIB punya positive control** (verifier yang selalu `false` lolos semua negatif), checklist guest (re-derive vs trust, enumerasi field per lane `btcHomed`, titik choke nullifier, "skips never panics" sebagai griefing), dan apa yang TIDAK dilaporkan.
- `references/discretionary-scope-defi-invariant-audit.md` — **program bounty DISCRETIONARY**: baca klausa reward sebagai SPEC lalu ubah tiap klausa jadi invariant yang bisa dites · **privilege-chain reachability** (bangun graf role: entry permissionless → sink privileged, dan tulis KILL-nya, bukan cuma rantainya) · **no-arbitrage sweep** (swapQuote.minted vs retireQuote.cost untuk SEMUA class × sweep rapat, 3× jalan; plus varian split-swap) · ⛔ **arah anomali wajib ditulis** (snapshot rate-limiter basi-tinggi = arah AMAN karena denominator `max(real, effective)`) · enumerasi surface permissionless + gate yang menyembunyikan sisanya (guard inverted `if (!flag) revert` — baca flag-nya) · disiplin negative-result sebagai deliverable utama + bagian coverage-gap · jebakan scope (peta deployment ada di repo bukan docs; "third-party" bisa ternyata protocol-owned — cek `owner()`; verifikasi deployed==source via PUSH4 scan) · ⛔ **asimetri ordering/first-of-day** = trace SYMMETRI tiap branch untuk KEDUA path dulu sebelum klaim \"lead\" (§6: symmetric branch = kedua jalur konvergen; divergence = fallback gated dormansi yang bikin prekondisinya sendiri unreachable).
- `references/wsl-scanner-toolchain-windows-host.md` — **cara menjalankan slither/aderyn/mythril/echidna di host Windows via WSL**: shim `forge` (WAJIB ditulis dari sisi Windows atau `"$@"`-nya dimakan quoting), flag per tool, crash `pyth_unchecked` slither 0.11.6 yang muncul di AKHIR run (output sebelumnya valid), dan disiplin karantina `_FAILED_TOOLING/` + README pembeda.
- `references/foundry-poc-harness-defi-stack.md` — **pola harness Foundry end-to-end untuk stack DeFi ber-governance**: urutan deploy (hub→vault→controller→diamond→oracle), party harus kontrak, config market di Judge DAN controller, MockPyth window `[t, t+2]` + `prevPublishTime < min`, timing slot 5-menit, dan pitfall **`vm.prank`/`expectRevert` habis oleh staticcall di argumen** (hoist semua read di atas cheatcode).
- `references/reentrancy-guard-and-approval-defects.md` — **guard yang bisa dilucuti** (`_nonReentrantAfter()`
  menulis 0 tanpa syarat → self-call bersarang melucuti guard untuk sisa transaksi → dana transit
  dicuri) + **approval menggantung** di `cleanup*` permissionless. Berisi bentuk bug vs bentuk fix,
  pemicu (cleanup self-call yang didokumentasikan sendiri), disiplin PoC (pasangan kontrol/klaim,
  ⛔ *test bisa lulus karena alasan salah* — payload harus SUKSES bila guard mengizinkan), verifikasi
  di bytecode **live** via fork (`evm_version = "cancun"`), peringkat pemicu eksternal-murni vs
  kooperatif, dan ⛔ **grep test suite vendor untuk ID known-issue** lalu cek apakah fix-nya sudah
  ter-deploy.
- `scripts/deployed_vs_source_selector_diff.py` — measures whether the deployed contract is the
  source you were handed (source `methodIdentifiers` vs live `cast code`; prints the selectors
  missing on chain). Run it before reporting anything sourced from a bundle.
- `references/auditing-a-vendor-source-bundle.md` — setting up a Foundry project around a vendor
  source ZIP / `/source/` page (remappings, dependency install, `via_ir` and its compile-cost rules,
  self-contained-vs-fork PoC choice, the approve-the-staked-token pitfall, capturing live state as
  evidence).
- `references/onchain-privileged-role-and-deployment-forensics.md` — **siapa PEMEGANG role sekarang**
  (bukan siapa yang bisa): keccak role hash, jendela deployment untuk `eth_getLogs` (cap 10k blok +
  jebakan topik nested yang diam-diam balik 0), `hasRole` untuk state, `eth_getCode` untuk EOA vs
  Gnosis Safe (+ `getThreshold/getOwners/masterCopy` = Safe v1.4.1), eksposur native+ERC20, dan
  paritas bytecode lintas-chain (testnet = build yang sama, hanya immutable `__self` yang beda).
- `references/invariant-fuzzing-campaigns.md` — **kampanye medusa + echidna pada kontrak nyata**
  (upgradeable + role-gated): harness wajib di `contracts/harness/` (bukan `test/` — crytic tidak
  mengompilasinya, dan gejalanya menyamar sebagai "no property found" / "contract not found"), proxy
  ERC1967 minimal untuk impl UUPS, wiring role supaya harness memegang DEFAULT_ADMIN untuk fixture
  sementara role yang diuji dipegang alamat lain, properti harus ada dalam dua prefix (`invariant_*` +
  `echidna_*`), perintah + budget campaign di host 4-vCPU, dan ⛔ **falsifikasi dengan trace yang tidak
  menyentuh kontrak = bug spesifikasi** (contoh nyata: `deposit_more` melakukan mint ke harness sendiri →
  properti diperketat `<= baseline + mintedByHarness`, lalu dijalankan ulang; cacat kedua: `ErrorRevert`
  dengan call-sequence KOSONG = overflow aritmetika harness dari input tak dibatasi → **batasi tiap input**
  `amt = amt % 1_000_000 ether` + hitung lewat variabel lokal; ada tabel triage verdict/trace). Termasuk
  konvensi bukti:
  log ke path absolut, liveness via delta CPU, dan baris ledger untuk fuzzer.


## 2026 sweep 3 (dork pass 2026-10-18 — web3/AI, 2 repo)

- Bonzo Finance oracle manipulation (Jul 2026) — **zero BLS signature** (point-at-infinity on the BLS curve) accepted by the Supra pull-oracle verifier, letting the attacker forge a price. Both submissions carried the *identical* fabricated value, proving a pre-crafted payload; funds were laundered via DEX swaps and cross-chain bridges.
  - The attacker then rapidly laundered the funds through DEX swaps, cross-chain bridges (LayerZero, Axelar/Squid), and LetsExchange.
  - Supra has officially published their incident report confirming this cryptographic bypass: [Security Incident Report: Hedera Pull-Oracle Verifier](https://supra.com/news/
- evm-hack-registry (★61) — offline-runnable archive of DeFi exploit PoCs, one Forge project per exploit with its own `anvil_state.json`. Use it to replay a real exploit end-to-end before testing the same pattern on a live target.
  - `0.8.x`, and they live together in one umbrella repo. A whole-project `forge build` fails to
  - Missing contract source code.** The exploits call into victim contracts whose bytecode is

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `forge build` + `slither .` baseline — siapa bilang "0 temuan" tanpa artefak ini = klaim | Analyzer output is not evidence, tapi TANPA analyzer = bukan audit |
| 2 | Selector census deployed bytecode vs source (`cast code` → diff fungsi) | Repo main ≠ deployed; patched upstream ≠ patched on-chain |
| 3 | Inheritance chain walk sampai storage/base contract (bukan cuma `contracts-upgradeable` import) | `unprotected-upgrade` FP klasik — slither gagal resolve modifier inherited |
| 4 | Single-party vs multi-party pool check (`public(address)` + `msg.sender == self.lender`) | Kill test untuk klaim dilution/write-off sebelum difile |
| 5 | `forge test` PoC satu perintah dengan `assertEq` pada balance/state yang diklaim | Immunefi auto-reject submission tanpa PoC; PoC multi-step = downgrade |
| 6 | **Read-path liveness sweep** — untuk tiap fungsi money-path, `eth_call` SEMUA external `view` yang dia panggil ke deployment LIVE (bukan cuma baca kode). Satu read yang revert = satu jalur yang SUDAH beku. ⛔ Lalu **decode storage-nya**, jangan percaya accessor: `latest()==0` / `sampleOf()==0` di seluruh sweep TIDAK membuktikan array kosong — di Tacit ring-nya justru 128/128 terisi tapi basi 541 interval (3.76 hari), karena sweep-nya di-anchor ke indeks yang DIHARAPKAN, bukan ke record TERBARU. Hitung `behind = expected - newest_in_storage` → itulah umurnya, dan itu beda temuan dari \"tidak pernah ada\". Resep: `onchain-finding-verification` → `references/storage-ring-and-accessor-negatives.md` | Auditor membaca write-path; freeze tinggal di read-path. Contoh nyata: oracle `latest()==0` + `depthMin()` wajib 100% coverage → `withdraw`/`borrow`/`liquidate`/`bid`/`redeem` revert, dana terkunci. Tidak ada analyzer yang menemukan ini |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## 2026 sweep (bug class yang masih dibayar)

- **ERC-7579 modular account** — validator/module registry tanpa allowlist = arbitrary delegatecall. Probe: module install dengan address attacker, cek `onInstall` revert vs silent accept.
- **EIP-7702 delegation** — EOA yang delegate ke implementation attacker-controlled; `tx.origin`-based auth jadi sink. Probe: cek setiap `tx.origin` guard di kontrak yang bisa dipanggil oleh 7702-delegated EOA.
- **Permit2 / ERC-3009** — signature replay lintas domain: cek `chainId` + `verifyingContract` + nonce di setiap permit. Permit2 `allowance` tidak di-reset setelah transfer = double-spend.
- **Uniswap v4 hooks** — `beforeSwap`/`afterSwap` callback tanpa access control = price manipulation via hook contract. Probe: hook address attacker-controlled di pool initialize?
- **Restaking / LRT (EigenLayer-style)** — operator-set slashing condition yang bisa dipicu attacker; withdrawal delay bypass via queue manipulation.
- **Donation attack / first-depositor inflation** — ERC-4626 vault kosong, `deposit(1, 0)` → inflate share price → victim deposit rounding ke 0 share.
- **Sequencer-uptime oracle** — L2 app yang percaya `sequencerUptimeFeed` tanpa grace period = stale price saat sequencer down.
- **EIP-2535 diamond** — `diamondCut` tanpa `onlyOwner` pada facet replacement; storage collision antar facet.
- **zkVM proof verification** — public input yang tidak di-bind ke verification key; recursive proof reuse.


## Critical severity anchor (apa yang membuat temuan dari skill ini Critical)

Skill ini menghasilkan *audit pass*, bukan temuan. Yang membuat temuan Critical adalah kalau
ada **fund-loss path** yang bisa dicapai penyerang tanpa hak istimewa:

| Temuan | Severity |
|---|---|
| Drain vault / mint arbitrer tanpa authz | Critical |
| Oracle manipulation → likuidasi paksa posisi sehat | Critical |
| Accounting desync → insolvency (share > backing) | Critical |
| Reentrancy yang memindahkan dana | Critical |
| Access control pada fungsi privileged (upgrade, pause, fee) | High-Critical tergantung siapa yang bisa panggil |
| Missing event / gas inefficiency / style | Info |

**Kalibrasi wajib:** severity mengikuti **Immunefi VSS v2.3** per domain (Smart Contracts /
Blockchain-DLT / Websites-and-Apps), BUKAN CVSS. Batas yang menentukan triage: *principal vs
unclaimed yield* (Critical vs High) dan *temporary vs permanent freeze*. Baca program brief
sebelum klaim Critical — matriksnya mengunci pada persentase kerugian ekonomi langsung terhadap TVL.
