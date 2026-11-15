---
name: hunt-intent-settlement
description: Hunt intent-based protocols — solver/filler allowlists, off-chain attestor trust, settlement-price divergence, partial-fill accounting, and cross-chain intent replay. Use when a target has solvers, fillers, quoters, an off-chain attestor service, or a "signed intent" that an off-chain actor fulfils.
metadata:
  hermes:
    tags: [web3, intent, solver, filler, attestor, settlement, cross-chain, critical]
    related_skills: [web3-audit, hunt-business-logic, hunt-race-condition, chain-to-impact, onchain-finding-verification]
---

# Hunt — Intent Protocols & Solver/Attestor Trust

Intent protocols move the execution decision off-chain: a user signs *what* they want, a solver
or attestor decides *how* it happens. Every Critical bug is a trust placed in the off-chain actor
that the on-chain code does not verify.

## When to use

- Target has `solve(`, `fill(`, `executeIntent(`, `settle(`, or a solver/filler registry.
- Target has an off-chain attestor/oracle service that credits an on-chain vault.
- Target docs mention "intent", "solver", "filler", "RFQ", "quoter", "auction", "batch settlement".
- Target is a bridge or cross-chain settlement where an off-chain signature releases funds.

---

## Phase 0 — Name the trust, then attack it

Write down, before any code review:

1. **Who is allowed to settle?** Anyone, a registered solver, an attestor key?
2. **What does the on-chain code verify about the settlement?** The user's signature only, or
   also the solver's claim about price/amount?
3. **What happens on a partial fill, a failed fill, or an expired intent?**

The recurring Critical shape (verified in real incidents):

> **An externally callable function with no access control that takes an address or bytes
> parameter and passes it into an outbound call, letting a third party execute with the
> protocol's authority.**

---

## Phase 1 — Solver/filler allowlist

```bash
rg -n "function (solve|fill|execute|settle|dispatch|batch)" -A 20 | rg -n "external|public"
rg -n "isApproved|onlySolver|onlyFiller|whitelist|registeredSolver" -B 2 -A 2   # the FIX shape
rg -n "\.(call|delegatecall|staticcall)\(" -B 8 | rg -n "calldata|memory"
```

| Probe | Decisive result |
|---|---|
| 1. Call `solve()` with an arbitrary solver address | `SolverNotApproved` = allowlist holds |
| 2. If accepted, does the solver address get `delegatecall`ed or `call`ed? | delegatecall = storage write as protocol |
| 3. Can a solver register itself? Is registration permissionless? | Permissionless registration = allowlist is decorative |
| 4. Can a de-registered solver still settle a previously-signed intent? | Stale-authority settlement |
| 5. Is the solver address bound into the user's signed intent? | If not, the user authorised a different executor |

**Rule:** "solver address is a parameter and there is no allowlist check" is a finding only after
you show the outbound call and what it can reach. Show the drain.

---

## Phase 2 — Off-chain attestor trust (bridge / intent-settlement)

The pattern: an off-chain service observes chain A and signs "this happened", and chain B credits
a vault. Bugs:

| Bug | Probe |
|---|---|
| Attestor key is a single EOA | Who holds it? Compromise = mint at will |
| Attestation not bound to a chain id | Replay the same attestation on a fork |
| Attestation not bound to a nonce | Replay the same attestation twice |
| Attestation covers "amount" but not "recipient" | Attest for amount, redirect the credit |
| No finality/confirmation requirement | Attest a reorged block |
| Multiple attestors but threshold is 1-of-N | One compromised key is enough |

```bash
rg -n "attestor|relayer|guardian|signature" -B 2 -A 6
rg -n "chainId|domainSeparator|nonce" -B 2 -A 2
rg -n "threshold|requiredSignatures|m of n" -B 2 -A 2
```

Probe: obtain or forge a well-formed attestation, replay it (a) twice, (b) on a fork, (c) with a
different recipient. Any acceptance = the attestation is under-bound.

---

## Phase 3 — Settlement price divergence

The user signs "swap X for at least Y". The solver decides the actual execution. Bugs:

- **Solver reports a price the on-chain code trusts without checking the pool.**
- **Settlement uses the intent's `minOut` as the actual out** — if the solver under-delivers and
  the contract doesn't verify, the user is shorted.
- **Slippage bound is applied to the wrong leg** (input instead of output).
- **Batch settlement averages prices across a manipulated block.**

```bash
rg -n "minOut|minReturn|slippage|amountOutMinimum" -B 2 -A 4
rg -n "getAmountOut|quote|price" -B 2 -A 4
```

Probe: sign an intent with a generous `minOut`, have the solver settle at a worse price, check
whether the on-chain code rejects it.

---

## Phase 4 — Partial fill & expiry accounting

| Bug | Probe |
|---|---|
| Partial fills double-count the filled amount | Fill 50% twice = 100% filled, or 150%? |
| Expired intent still fillable | Fill after `deadline` |
| Cancelled intent still fillable | Fill after cancel |
| Fill amount exceeds the signed amount | Fill more than authorised |
| Unfilled remainder not returned to the user | Dust locked |

```bash
rg -n "filledAmount|remainingAmount|deadline|expiry|cancelled" -B 2 -A 4
```

Probe: fill 50%, fill 50% again, then attempt a third fill. Also fill exactly at `deadline + 1`
(fork + timestamp).

---

## Phase 5 — Cross-chain intent replay

An intent signed on chain A replayed on chain B, or on a fork of A.

| Check | Probe |
|---|---|
| `chainId` in the signed struct | Replay on a fork |
| Destination chain id in the signed struct | Replay on the destination |
| Nonce scoped per (user, intent-type) | Replay a different intent type with the same nonce |
| Intent hash includes the solver/attestor | Replay with a different executor |

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `solve()`/`fill()` dengan solver address arbitrary | Inti kelas — allowlist ada atau tidak |
| 2 | Attestation replay: dua kali + di fork + recipient berbeda | Under-bound attestation = mint at will |
| 3 | Settlement price divergence: intent `minOut` longgar, solver settle lebih buruk | User shorted kalau on-chain tidak verifikasi |
| 4 | Partial fill: 50% + 50% + percaya ketiga; expired & cancelled fill | Accounting & expiry |
| 5 | Cross-chain replay: `chainId`/nonce/solver binding dalam signed struct | Replay lintas chain & fork |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret: *"Penyerang mengirim `fill()` dengan attestation yang sama dua kali — yang kedua
berhasil, sehingga 2× jumlah token dicetak untuk satu intent."*
Bukan lolos gate: "attestor adalah EOA", "tidak ada allowlist solver".
Sebutkan field signed struct mana yang tidak binding.

**2. Apa yang hilang dari korban, dan berapa?**
Nyatakan pihak yang dirugikan: **user** (minOut tidak dihormati), **solver lain** (front-run),
atau **protokol** (mint ganda). Contoh: *"User menerima 62% dari `minOut` karena solver menetap di
harga yang jauh lebih buruk dan kontrak tidak memverifikasi fill."*
Kalau yang terbukti hanya "solver bisa memilih harga" dan itu memang model intent → **by-design**.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] Attestation/signature dibuat oleh helper di dalam test (bukan pre-baked dari prod)
- [ ] Replay/divergence ditunjukkan dengan **dua** eksekusi berurutan atau dua chainId
- [ ] Selisih nilai user atau jumlah mint dihitung eksplisit

**Cross-chain:** kalau bukti replay butuh fork dua chain, tulis batasannya dan buktikan separuh
yang bisa dibuktikan; jangan klaim kedua sisi tanpa menjalankannya.

## Eskalasi wajib

**Primitif:** solver tanpa allowlist / attestation under-bound / price tidak diverifikasi.
**Rantai:** permissionless solve → delegatecall ke target arbitrary → drain vault. Attestation
replay → mint ganda. Price divergence → short semua user di batch.
**Eskalasi ke:** `web3-audit` (kelas 11 cross-chain settlement), `hunt-business-logic`,
`hunt-race-condition`, `onchain-finding-verification`.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<RPC>; S=<SETTLEMENT_ADDR>

# 1) solver allowlist — call fill() from a key that was never approved
cast call $S 'allowedSolvers(address)(bool)' $ATTACKER --rpc-url $RPC 2>/dev/null
cast send $S 'fill(bytes,bytes)' $ORDER_SIG $FILL_DATA \
  --private-key 0xA11CE --rpc-url $RPC --dry-run

# 2) attestation replay — the same signed attestation twice
cast send $S 'settle(bytes)' $ATTESTATION --private-key 0xA11CE --rpc-url $RPC   # 1st
cast send $S 'settle(bytes)' $ATTESTATION --private-key 0xA11CE --rpc-url $RPC   # 2nd: must revert

# 3) minOut enforcement — read what the contract compares it against
cast call $S 'filled(bytes32)(uint256)' $ORDER_ID --rpc-url $RPC 2>/dev/null
cast call $S 'orders(bytes32)(address,uint256,uint256,uint256,uint256)' $ORDER_ID --rpc-url $RPC 2>/dev/null

# 4) partial fill accounting
cast call $S 'remaining(bytes32)(uint256)' $ORDER_ID --rpc-url $RPC 2>/dev/null || \
  cast call $S 'orderStatus(bytes32)(uint8)' $ORDER_ID --rpc-url $RPC

# 5) cross-chain binding — is chainId inside the signed struct?
cast call $S 'DOMAIN_SEPARATOR()(bytes32)' --rpc-url $RPC
cast call $S 'chainId()(uint256)' --rpc-url $RPC 2>/dev/null
```

**Report gate:** lab proof = `test/RestakingIntentDiamondCalibration.t.sol --match-contract
IntentSettlementCalibration`. The finding names **who is harmed** (user / competing
solver / protocol) and by how much.

---

## By-design calibration

- Solver allowlist + bond/slash = the fix.
- Attestation dengan chainId + nonce + recipient + threshold m-of-n = correct.
- `minOut` yang benar-benar dicek on-chain = kontrol bekerja.
- Partial fill yang accounting-nya konsisten = by design.
- "On-chain discoverable = not confidential" — jangan lapor eksposur data on-chain mentah.

## 2026 sweep

- **UniswapX / CoW-style signed order + settlement contract** — order ditandatangani off-chain,
  disettle oleh solver; cek apakah `reactor`/settlement memverifikasi signature DAN output amount.
- **Attestor key rotation tanpa invalidasi tanda tangan lama** — key dirotasi, signature dari key
  lama masih diterima.
- **Solver bond slash untuk settlement gagal** — settlement gagal tapi bond tidak di-slash; solver
  bisa spam order gagal tanpa biaya.
- **Intent `deadline` dalam block number vs timestamp** — campur keduanya = intent kedaluwarsa di
  chain dengan block time berbeda.
- **Cross-chain intent dengan `destinationChainId` yang tidak di-bind ke nonce** — intent yang sama
  bisa di-fill di dua chain tujuan.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Solver tanpa allowlist + outbound call → drain vault; attestation under-bound (chainId/nonce/recipient) → mint ganda; settlement price tidak diverifikasi → short semua user. Kalibrasi: solver allowlist + bond = the fix; 'on-chain discoverable = not confidential'.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 4/4 probes passed)

Diuji pada intent settler (`test/RestakingIntentDiamondCalibration.t.sol`, kontrak
`IntentSettlementCalibration`). Yang terkonfirmasi:

- **Probe 1 (solver tanpa allowlist) — address arbitrer menyelesaikan intent.** Field `solvers`
  ada di kontrak tapi tidak pernah dibaca di `solve()`. Kontrak aman revert `SolverNotApproved`.
  **Pelajaran:** mapping allowlist yang ADA tapi tidak dipakai adalah pola yang lebih umum daripada
  allowlist yang tidak ada — grep untuk deklarasi `mapping(address => bool)` lalu cek apakah
  namanya muncul di fungsi write-path.
- **Probe 2 (attestation replay) — attestation yang sama dikreditkan dua kali,** karena
  `attestationUsed[id]` di-set `false` dan tidak pernah `true`. Kontrak aman revert
  `attestation already used`.
- **Probe 3 (minOut diabaikan) — settle 1 saat user menandatangani minOut 1000.** `minOut` diterima
  sebagai parameter lalu tidak dibandingkan dengan `amountOut`. Kontrak aman revert
  `slippage exceeded`.
- **Probe 4 (overfill) — 3×60e18 = 180e18 terhadap signed amount 100e18.** `filledAmount` naik tanpa
  batas atas. Kontrak aman revert `overfill`.

**Pola lintas probe:** keempat bug punya bentuk yang sama — **parameter/peran yang diterima tapi
tidak pernah divalidasi**. Saat audit target nyata, satu grep untuk "parameter yang tidak muncul
lagi setelah deklarasi" menemukan keempatnya sekaligus.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

forge test --match-path test/RestakingIntentDiamondCalibration.t.sol --match-contract IntentSettlementCalibration -vvv
forge test --match-test test_Probe2_AttestationReplay -vvvv
```

| | |
|---|---|
| file | `test/RestakingIntentDiamondCalibration.t.sol` |
| suite | `IntentSettlementCalibration` |
| probes | `test_Probe1_NoSolverAllowlist` · `test_Probe2_AttestationReplay` · `test_Probe3_MinOutNotEnforced` · `test_Probe4_Overfill` |

No control test in this suite — for a negative, build the safe path yourself (a solver with a
correct allowlist) and show it does NOT fire, otherwise "no bug" is unfalsifiable.

