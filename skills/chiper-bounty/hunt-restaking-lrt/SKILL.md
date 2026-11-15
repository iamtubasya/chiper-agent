---
name: hunt-restaking-lrt
description: Hunt restaking / liquid-restaking-token (LRT) bugs — operator-set slashing conditions triggerable by an attacker, withdrawal-queue manipulation, exchange-rate desync between the LRT and the underlying, and double-counted stake across strategies. Use when a target issues an LRT, runs an operator/AVS registry, or has a withdrawal queue with a delay.
metadata:
  hermes:
    tags: [web3, restaking, lrt, eigenlayer, slashing, withdrawal-queue, exchange-rate, critical]
    related_skills: [web3-audit, hunt-business-logic, hunt-race-condition, onchain-finding-verification]
---

# Hunt — Restaking & Liquid Restaking Tokens

Restaking adds a second accounting layer on top of staking: **operator sets, slashing conditions,
and withdrawal queues**. The Critical bugs are (a) slashing an honest operator, (b) withdrawing
before the delay, (c) an LRT exchange rate that desyncs from the underlying.

## When to use

- Target issues a liquid restaking token (LRT) / receipt token for restaked stake.
- Target has an operator registry, AVS (actively validated service) registry, or strategy manager.
- Target has a withdrawal queue, exit queue, or unbonding period.
- Target docs mention "restaking", "operator set", "slashing", "AVS", "withdrawal delay".

---

## Phase 0 — Map the two ledgers

Restaking protocols keep **two** balances that must stay consistent:

1. **The underlying ledger** — how much is actually staked/delegated per operator.
2. **The LRT ledger** — how many receipt tokens exist and at what exchange rate.

Every Critical bug is a desync between them. Start by writing both down.

```bash
rg -n "exchangeRate|exchangeRateStored|totalPooledEther|totalShares" -A 4
rg -n "slas|penalt|jail" -B 2 -A 4
rg -n "withdrawal|exitQueue|unbond|delay" -A 4
```

---

## Phase 1 — Slashing conditions (attacker-triggerable slash = Critical)

The question is never "can slashing happen" — it is **"can an attacker cause an honest operator
to be slashed, or slash more than the penalty should be"**.

| Probe | Finding shape |
|---|---|
| 1. Who can submit a slash request? Anyone, a challenger, a committee? | Unauthenticated challenger = griefing |
| 2. Is the challenged task verifiable on-chain, or attested off-chain? | Off-chain attestation with no fraud proof = arbitrary slash |
| 3. Can the same misbehaviour be submitted twice? | Double-slash for one offence |
| 4. Is the slash amount bounded by the operator's stake in *that* AVS, or total stake? | Cross-AVS over-slashing drains unrelated stake |
| 5. Is there a challenge window before the slash executes? | Instant slash = no defence |

```bash
rg -n "function slash" -A 20
rg -n "onlyChallenger|onlyCommittee|onlySlasher|msg.sender ==" -B 3 -A 3
rg -n "slashAmount|penalty" -B 2 -A 2 | rg -n "balanceOf|stake\[|totalStake"
```

Probe sequence: submit a slash request for an operator with a *fabricated but well-formed*
attestation. If it executes, the attestation is not verified. Then submit the same offence twice
and check the second is rejected.

---

## Phase 2 — Withdrawal queue manipulation

The withdrawal delay exists to prevent a bank run. Bugs let an attacker skip it or jump it.

| Probe | Finding shape |
|---|---|
| 1. Can a withdrawal be cancelled and re-queued to reset the delay? | Delay bypass |
| 2. Is the queue FIFO by request time or by arbitrary order? | Queue-jumping |
| 3. Can a withdrawal be split into N small ones that each bypass a minimum? | Threshold bypass |
| 4. Does the LRT burn happen before or after the underlying is released? | Burn-then-fail = LRT holders eat the loss |
| 5. Is the exchange rate updated at request time or at claim time? | Stale rate = free option on the rate |

```bash
rg -n "requestWithdrawal|claimWithdrawal|completeWithdrawal" -A 15
rg -n "queue|head|tail|nextId" -B 2 -A 2
rg -n "MIN_DELAY|WITHDRAWAL_DELAY|delay" -B 2 -A 2
```

The decisive probe: request a withdrawal, then attempt to claim it before the delay elapses
(manipulate block timestamp on a fork). Must revert.

---

## Phase 3 — LRT exchange-rate desync

The LRT price must track the underlying. Desync = free money for one side.

| Desync | Probe |
|---|---|
| Rewards credited to the underlying but not the LRT rate | Compare `totalUnderlying` vs `totalShares × rate` after a reward accrual |
| Slashing reduces the underlying but the LRT rate lags | Slash, then immediately redeem — do you get pre-slash value? |
| Donation to the underlying contract inflates the rate for a first-redeemer | Donate, then redeem as the only holder |
| Rebase/rounding drift over many small deposits | 1000 × deposit(1) vs deposit(1000) |

```bash
rg -n "function exchangeRate|convertToAssets|convertToShares" -A 10
rg -n "totalAssets|totalUnderlying|pooledEther" -B 2 -A 2
```

**Economics gate before reporting:** compute the attacker's P&L explicitly. A rate that is
technically stale but nets the attacker ~0 after fees is a hardening note, not a finding.

---

## Phase 4 — Cross-strategy double counting

Restaking lets the same ETH back multiple AVS positions. The protocol must not count the same
stake twice when computing either (a) the operator's total exposure or (b) the LRT's backing.

| Probe | Finding shape |
|---|---|
| Deposit into strategy A, get an LRT, deposit the LRT as collateral elsewhere | Recursive collateralisation |
| Operator delegates the same stake to two AVS sets | Slashing exposure undercounted |
| LRT is accepted as its own underlying in a second deposit | Infinite mint loop |

Probe: trace one unit of stake through every registry it can enter and count how many times it
is counted as backing. More than one = double count.

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Slash request dengan attestation fabric → eksekusi atau tidak | Inti kelas: slash bisa dipicu attacker |
| 2 | Double-slash: offence sama disubmit dua kali | Over-slashing = drain stake tidak terkait |
| 3 | Withdrawal claim sebelum delay (fork + timestamp manip) | Delay bypass = bank run |
| 4 | Exchange rate: underlying vs LRT setelah reward & setelah slash | Desync = free money satu sisi |
| 5 | Satu unit stake dilacak melalui semua registry → hitung backing | Double count = insolvency |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret: *"Penyerang memicu `slash()` dengan offence yang sama dua kali (attestation tidak
punya nonce), sehingga 2× stake operator dipotong dan LRT holder menanggung 2× kerugian."*
Bukan lolos gate: "withdrawal delay hanya 1 blok", "exchange rate tidak di-refresh".
Sebutkan fungsi dan argumen persisnya.

**2. Apa yang hilang dari korban, dan berapa?**
Kelas ini menyentuh **dana pihak ketiga** (holder LRT, delegator, operator). Nyatakan angka:
*"Holder LRT kehilangan 3,1% NAV; 890 ETH berpindah dari delegator ke penyerang."*
Kalau yang terbukti hanya desync rate sementara yang bisa di-arbitrase balik tanpa kerugian bersih
→ hardening note, bukan Critical.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] Stake/registry state dibuat di dalam test lewat interface nyata (bukan mock kosong)
- [ ] Slash / withdrawal / exchange-rate dihitung **sebelum vs sesudah** dengan angka
- [ ] Attacker P&L bersih positif setelah gas; kalau negatif → bukan temuan
- [ ] Untuk double-count: lacak **satu** unit stake melewati semua registry dan tunjukkan
      total backing < total supply

**"Bisa bikin bank run" tanpa angka insolvensi bukan bukti.** Tunjukkan selisih backing vs
kewajiban.

## Eskalasi wajib

**Primitif:** slash tanpa verifikasi / delay bypass / rate desync / double count.
**Rantai:** double count → LRT over-minted → redeem untuk underlying yang tidak ada → insolvency.
Attacker-triggered slash → operator jujur kehilangan stake → protokol kepercayaan runtuh.
**Eskalasi ke:** `web3-audit` (accounting desync, ERC4626), `hunt-race-condition`,
`hunt-business-logic`, `onchain-finding-verification`.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<RPC>; LRT=<LRT_ADDR>; REG=<REGISTRY_ADDR>

# 1) the two ledgers — delegation vs asset backing (the primitive)
cast call $LRT 'totalSupply()(uint256)' --rpc-url $RPC
cast call $LRT 'totalAssets()(uint256)' --rpc-url $RPC
cast call $LRT 'convertToAssets(uint256)(uint256)' 1000000000000000000 --rpc-url $RPC
# totalAssets < totalSupply-equivalent backing = insolvency candidate

# 2) slashing — who can trigger it?
cast call $REG 'owner()(address)' --rpc-url $RPC 2>/dev/null
cast send $REG 'slash(address,uint256)' $OPERATOR 1000000000000000000 \
  --private-key 0xA11CE --rpc-url $RPC --dry-run

# 3) double-slash — same offence twice
cast call $REG 'slashed(bytes32)(bool)' $OFFENCE_ID --rpc-url $RPC 2>/dev/null || \
  cast call $REG 'offenceProcessed(bytes32)(bool)' $OFFENCE_ID --rpc-url $RPC
# a false/false before AND after a second slash = double-slash

# 4) withdrawal delay
cast call $LRT 'withdrawalDelay()(uint256)' --rpc-url $RPC 2>/dev/null
cast call $LRT 'pendingWithdrawals(address)(uint256)' $USER --rpc-url $RPC 2>/dev/null
cast send $LRT 'claimWithdrawal(uint256)' 0 --private-key 0xA11CE --rpc-url $RPC --dry-run

# 5) trace ONE unit of stake through every registry (double-count check)
cast call $REG 'getOperatorStake(address)(uint256)' $OPERATOR --rpc-url $RPC
cast call $REG 'totalStaked()(uint256)' --rpc-url $RPC
```

**Report gate:** lab proof = `test/RestakingIntentDiamondCalibration.t.sol --match-contract
RestakingLRTCalibration`. "Bank run possible" without an insolvency number
(totalAssets vs obligations) is a hardening note.

---

## By-design calibration

- Slashing gated on a committee + challenge window + on-chain-verifiable task = correct.
- Withdrawal delay yang konsisten dan tidak bisa di-reset = the fix.
- Exchange rate yang update di claim time **dengan** rate bounds = desain yang wajar.
- Satu ETH di banyak AVS dengan slashing exposure yang dihitung agregat = fitur restaking, asal
  agregasinya benar.
- Centralisation observation (admin bisa pause) tanpa fund-loss path = Info, bukan Critical.

## 2026 sweep

- **Operator-set migration tanpa slashing carry-over** — operator pindah set, riwayat slash lama
  tidak dibawa; exposure lama hilang dari perhitungan.
- **LRT sebagai collateral di protokol pinjaman lain** — LRT di-deposit sebagai collateral sementara
  underlying-nya di-slash; protokol pinjaman tidak tahu → undercollateralised loan.
- **Withdrawal credential split** — sebagian stake masuk lewat jalur native, sebagian lewat LRT;
  hitungan `totalPooled` menggabungkan keduanya tanpa deduplikasi.
- **Reward claiming race** — reward bisa diklaim dua kali karena `claimRewards` tidak menandai
  epoch sebagai sudah diklaim.
- **EigenLayer-style `queueLength` manipulation** — memindahkan antrean sehingga withdrawal
  attacker diproses sebelum grace period protokol lain berakhir.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Slash tanpa verifikasi → operator jujur kehilangan stake; withdrawal delay bypass; LRT rate desync; double-count stake → insolvency. Kalibrasi: committee + challenge window + on-chain-verifiable task = correct; admin pause tanpa fund-loss path = Info.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 5/5 probes passed)

Diuji pada restaking vault (`test/RestakingIntentDiamondCalibration.t.sol`, kontrak
`RestakingLRTCalibration`). Yang terkonfirmasi:

- **Probe 1 (slash tanpa verifikasi) adalah Critical yang paling langsung.** Penyerang tanpa peran
  apa pun memanggil `slash(op, 500e18, keccak256("fabricated-offence"))` dan stake operator jujur
  turun 1000 → 500. Tidak ada proof, tidak ada committee, tidak ada challenge window. Kontrak aman
  revert `not committee`.
- **Probe 2 (double slash) — offence yang sama dipakai dua kali, stake jadi 400.** Dedupe tidak
  ada. Kontrak aman revert `offence already used`.
- **Probe 3 (delay bypass) — withdrawal 7 hari bisa diklaim instan.** Bukan "reset clock", lebih
  buruk: `claimWithdrawal` tidak mengecek delay sama sekali. Kontrak aman revert `delay not elapsed`.
- **Probe 4 (rate desync) butuh angka yang benar.** Pool 7000e18 (5000 seed + 2000 deposit) di-slash
  1000e18 → 6000e18, tapi `rateSnapshot` masih 1e18 sehingga 1000 share dibayar 1000e18 padahal
  nilai wajarnya 3000e18. **Selisih inilah kerugian yang harus ditulis di laporan** — bukan
  "attacker dapat lebih banyak", tapi "redeemer terakhir tidak bisa redeem penuh".

**Trap harness:** `totalPooled -= slashAmt` underflow kalau pool belum di-seed. Selalu deposit dulu
di `setUp()` sebelum menguji slash, dan hitung ulang angka harapan setelah seed — jangan pakai
angka dari skenario tanpa seed.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

forge test --match-path test/RestakingIntentDiamondCalibration.t.sol --match-contract RestakingLRTCalibration -vvv
forge test --match-test test_Probe2_DoubleSlash -vvvv
```

| | |
|---|---|
| file | `test/RestakingIntentDiamondCalibration.t.sol` |
| suite | `RestakingLRTCalibration` |
| probes | `test_Probe1_AnyoneCanSlash` · `test_Probe2_DoubleSlash` · `test_Probe3_WithdrawalDelayBypass` · `test_Probe4_RateDesyncAfterSlash` |
| control | `test_Control_SafeLrtBehaves` |

`test_Probe4_RateDesyncAfterSlash` measures the exchange-rate delta, not just its existence —
that number is what your report needs. "Rate desyncs" without a figure is a hardening note.

