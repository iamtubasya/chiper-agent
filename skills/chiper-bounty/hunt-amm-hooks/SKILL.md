---
name: hunt-amm-hooks
description: Hunt Uniswap v4 hooks, Balancer v3, and concentrated-liquidity AMM bugs — hook callback access control, dynamic fee manipulation, singleton storage collisions, JIT liquidity abuse, and tick-boundary rounding. Use when a target runs a hook-enabled AMM, a singleton pool manager, or any pool whose swap path invokes a caller-supplied contract.
metadata:
  hermes:
    tags: [web3, amm, uniswap-v4, hooks, balancer, jit-liquidity, price-manipulation, critical]
    related_skills: [web3-audit, hunt-business-logic, hunt-race-condition, onchain-finding-verification]
---

# Hunt — AMM Hooks & Modern Pool Architecture

v4-style AMMs moved pool logic into a **singleton** and made the swap path call a
**caller-supplied hook contract**. Both changes create bug classes that did not exist in v2/v3.

## When to use

- Target runs `PoolManager`, `swap(`, `modifyLiquidity(`, or a singleton pool contract.
- Target has hook callbacks: `beforeSwap`, `afterSwap`, `beforeInitialize`, `afterInitialize`,
  `beforeAddLiquidity`, `afterAddLiquidity`, `beforeDonate`, `afterDonate`.
- Target is a Balancer-v3-style vault with custom pool logic.
- Target docs mention "hooks", "custom pool logic", "singleton", "flash accounting".

---

## Phase 0 — The singleton changes everything

In a singleton, all pools share one contract and are keyed by `PoolKey` (a hash of
`currency0, currency1, fee, tickSpacing, hooks`). Two consequences:

1. **Storage is per-pool-id, not per-contract.** A bug that writes to the wrong slot corrupts a
   *different* pool. Check every `mapping` key includes the full pool id.
2. **`hooks` is part of the pool identity.** Two pools identical except for the hook address are
   different pools — and the hook is attacker-choosable at initialize time unless restricted.

```bash
rg -n "struct PoolKey" -A 12
rg -n "beforeSwap|afterSwap|beforeInitialize|beforeDonate" -B 2 -A 6
rg -n "hooks" -B 2 -A 2 | rg -n "address\.zero|require|=="
```

---

## Phase 1 — Hook access control (the Critical primitive)

The core question: **can an attacker deploy a pool with a hook they control, and does the
protocol trust that hook?**

| Probe | Decisive result |
|---|---|
| 1. `initialize()` a pool with `hooks = ATTACKER_CONTRACT` | If accepted → attacker hook runs in every swap on that pool |
| 2. In the hook, call back into `PoolManager.swap()` | Reentrancy into the singleton mid-swap |
| 3. In `beforeSwap`, return a delta that the manager trusts | Price override |
| 4. In `afterDonate`, donate to inflate a share price used elsewhere | Donation attack amplifier |

```solidity
// the shape that must NOT exist: a hook that can move the pool's own accounting
function afterSwap(...) external {
    // if the manager applies a hook-returned delta without checking the caller is a registered pool
}
```

**Rule:** a hook is only safe if (a) the pool id binds the hook address, (b) the manager verifies
`msg.sender`/context is the pool being swapped, and (c) hook return values are bounded. Missing
any one is a finding; show the concrete manipulation.

---

## Phase 2 — Dynamic fee manipulation

If `fee` is mutable (hooks can change it, or a governance path changes it):

- **Fee change mid-swap** — `beforeSwap` sets fee to max, swap executes, `afterSwap` resets.
  Attacker pays nothing, victims pay max on the same block.
- **Fee change between quote and execution** — a router quotes at 0.05%, the pool is at 1% by
  execution time. Check whether the router re-validates.
- **Protocol fee skim on manipulated fee** — if protocol fee is a % of the pool fee, inflating
  the pool fee inflates the skim.

Probe: quote a swap, change the fee, execute the swap, compare. Also: two swaps in one tx with a
fee change between them.

---

## Phase 3 — JIT liquidity (just-in-time)

JIT is not automatically a bug — it is a strategy. It becomes a finding when the protocol's fee
distribution lets a JIT position capture fees disproportionate to its risk, or when the
"position must exist for N blocks" rule is unenforced.

| Check | Finding shape |
|---|---|
| Add liquidity → swap → remove liquidity in one tx | Fee capture with zero time-at-risk |
| Fee accrual uses `feeGrowthGlobal` snapshot at add time | JIT captures fees accrued *before* it arrived |
| No minimum liquidity duration | Position can be minted and burned in the same block |

Probe: in one transaction, mint a maximal-range position, trigger a large swap, burn the
position, and compute the fee earned vs. capital committed vs. time held. If the APR is
absurd and the duration is zero, the fee accounting is broken — but **prove the victim's loss**,
not just the attacker's gain.

---

## Phase 4 — Tick boundary & rounding

Concentrated liquidity moves the rounding bugs to tick edges.

```bash
rg -n "tickSpacing|tickNext|tickPrevious" -A 4
rg -n "getSqrtPriceAtTick|mulDiv|unsafeDiv" -B 2 -A 2
```

- **Off-by-one at tick boundary** — a position exactly at `tickLower`/`tickUpper` included or
  excluded inconsistently between mint and swap.
- **Rounding direction asymmetry** — `mulDiv` rounding down on the input side and down on the
  output side lets an attacker extract value over many tiny swaps.
- **`tickSpacing` not enforced** — a position initialised at a non-aligned tick corrupts the
  tick bitmap.

Probe: mint at the exact boundary tick, swap 1 wei, check the position's active state. Repeat
with `tickSpacing ± 1`.

---

## Phase 5 — Flash accounting settlement

Singleton AMMs use "flash accounting": deltas accumulate and settle at the end of the unlock.
The bug is a delta that is never settled, or settled against the wrong currency.

```bash
rg -n "unlock|settle|take\(|sync\(" -A 6
rg -n "currencyDelta|delta0|delta1" -B 2 -A 4
```

Checks:
- Is the delta checked to be zero at lock release?
- Can a delta be carried across two separate `unlock` calls?
- Is `take` restricted to the locker?

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `initialize` pool dengan hook address attacker | Inti kelas — hook trust model |
| 2 | Hook reentrancy: callback ke `swap()` dari dalam `beforeSwap`/`afterSwap` | Singleton reentrancy = korupsi lintas pool |
| 3 | Fee mutation mid-swap + quote-vs-execute diff | Dynamic fee abuse |
| 4 | JIT round-trip dalam satu tx, hitung P&L + durasi | Fee capture tanpa risiko |
| 5 | Tick boundary exact + `tickSpacing ± 1` + flash-accounting settle check | Rounding & settlement |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret: *"Penyerang mendaftarkan hook sendiri lewat `initialize` pool baru, lalu hook itu
memanipulasi fee pada `beforeSwap` sehingga taker membayar 40% lebih banyak dan selisihnya masuk
ke hook."* Bukan lolos gate: "hook tidak memvalidasi caller", "dynamic fee bisa diubah".
Sebutkan fungsi + argumen persis yang dipanggil penyerang.

**2. Apa yang hilang dari korban, dan berapa?**
Untuk kelas AMM, kerugian hampir selalu **LP atau taker**, bukan protokol. Nyatakan siapa yang
bayar dan berapa: *"LP pool X kehilangan 8,2% dari TVL ($410k) karena swap dirutekan lewat harga
yang dimanipulasi dalam satu blok."*
Kalau yang terbukti hanya "fee bisa diubah oleh pemilik hook" tanpa ada pihak yang dirugikan →
itu **by-design** (hook memang milik integrator), bukan temuan.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] Pool + likuiditas dibuat di dalam test (bukan mengandalkan state fork yang rapuh)
- [ ] Perubahan harga/fee diukur **sebelum vs sesudah**, dengan angka
- [ ] Attacker P&L positif setelah gas + fee; kalau negatif → hardening note

**JIT liquidity:** wajib tunjukkan P&L bersih dalam satu tx (fee earned − gas − risiko inventory).
Kalau hanya "bisa JIT" tanpa net profit → bukan temuan.

## Eskalasi wajib

**Primitif:** hook attacker-controlled / fee mutable / delta tidak settle.
**Rantai:** hook → price override → oracle manipulation → liquidation of another protocol that
reads this pool. JIT → fee drain → LP insolvency.
**Eskalasi ke:** `web3-audit` (oracle & ERC4626 classes), `hunt-race-condition`,
`onchain-finding-verification`.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<RPC>; PM=<POOL_MANAGER>

# 1) is the hook address a contract, and does its permission bitmap match the flags?
cast code $HOOK --rpc-url $RPC | head -c 20        # 0x = EOA hook (red flag)
cast call $HOOK 'getHookPermissions()(bool,bool,bool,bool)' --rpc-url $RPC

# 2) pool state + fee (hook-mutated fee shows up here)
cast call $PM 'getSlot0(bytes32)(uint160,int24,uint24,uint24)' $POOL_ID --rpc-url $RPC
cast call $PM 'getLiquidity(bytes32)(uint128)' $POOL_ID --rpc-url $RPC

# 3) quote vs execute — the fee-mutation differential
cast call $PM 'swap(...)' --rpc-url $RPC 2>/dev/null || true
# better: use forge for the round-trip, since a quote needs a simulated swap:
forge test --match-test test_Probe3_FeeMutatedMidSwap -vvvv

# 4) singleton cross-pool reach — both pools share $PM?
cast call $PM 'poolManager()(address)' --rpc-url $RPC 2>/dev/null
cast logs --from-block -1000 --address $PM --rpc-url $RPC 2>/dev/null | grep -i initialize | head

# 5) hook permission bitmap decode (the address encodes its own permissions)
python - <<'PY'
import os
addr = os.environ.get("HOOK", "0x0")
n = int(addr, 16) & 0x3FFF
bits = ["beforeInitialize","afterInitialize","beforeAddLiquidity","afterAddLiquidity",
        "beforeRemoveLiquidity","afterRemoveLiquidity","beforeSwap","afterSwap",
        "beforeDonate","afterDonate","beforeSwapReturnDelta","afterSwapReturnDelta",
        "afterAddLiquidityReturnDelta","afterRemoveLiquidityReturnDelta"]
print([b for i, b in enumerate(bits) if n >> i & 1])
PY
```

**Report gate:** lab proof = `test/AmmHooksCalibration.t.sol`. The finding is an
**extraction with a harmed counterparty** (LP/taker), measured in the fork test.

---

## By-design calibration

- Hook allowlist enforced at initialize (only registered hooks accepted) = the fix.
- JIT liquidity in a pool explicitly designed for it (with fee rules that account for it) = a
  strategy, not a bug.
- `tickSpacing` enforced with a bitmap = correct.
- Flash accounting that asserts zero delta at unlock = correct.
- A hook that can only *read* and return a bounded delta = low risk, downgrade.

## 2026 sweep

- **`beforeDonate` as an inflation primitive** — donate langsung ke pool menggeser `sqrtPrice`;
  kalau protokol lain membaca pool ini sebagai oracle, donation = price manipulation.
- **Hook `beforeInitialize` returning a modified `sqrtPrice`** — pool di-init pada harga yang
  sudah dimanipulasi sebelum likuiditas pertama masuk.
- **Singleton cross-pool reentrancy** — hook memanggil `swap()` pada pool **lain** di singleton
  yang sama saat unlock masih terbuka; delta antar pool tercampur.
- **Dynamic fee + protocol fee compounding** — hook menaikkan fee, swap besar terjadi, protocol
  fee dihitung dari fee yang sudah di-inflate.
- **`modifyLiquidity` dengan tick range kosong** — menambah likuiditas di rentang yang tidak
  mencakup harga saat ini; posisi langsung inactive tapi tercatat sebagai likuiditas.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Hook attacker-controlled di pool initialize → price override; singleton cross-pool reentrancy → korupsi lintas pool; fee mutasi mid-swap. Kalibrasi: hook allowlist enforced = the fix; JIT di pool yang memang dirancang untuknya = strategi, bukan bug.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 5/5 probes passed)

Diuji pada singleton pool manager (`test/AmmHooksCalibration.t.sol`). Yang terkonfirmasi:

- **Probe 1 (hook tanpa allowlist) — pool terinit dengan hook attacker, tanpa revert.** Kontrak
  aman menolak dengan `HookNotApproved`. Perhatikan bahwa kontrak rentan **mengabaikan kegagalan
  callback** (`ok` dibuang) sehingga hook yang revert pun tidak menghalangi inisialisasi — pola
  yang lebih halus daripada "tidak ada allowlist".
- **Probe 2 (cross-pool reentrancy) berhasil di singleton.** Hook memanggil `swap()` pada pool
  **lain** saat swap pertama masih berjalan. Tidak ada reentrancy lock. Kontrak aman revert
  `Reentrancy`. Ini bug yang hanya ada di arsitektur singleton — di v2/v3 per-pool tidak muncul.
- **Probe 3 (fee mutasi mid-swap) terukur:** fee 3000 → 500000 (0.3% → 50%) di dalam satu swap.
  Temuan penting: hook harus tahu **pool key-nya sendiri** untuk menaikkan fee pool yang benar —
  `keccak256(abi.encode(key))` berbeda kalau field `hooks` berbeda. Ini jebakan nyata saat menulis
  PoC: menaikkan fee pool yang salah terlihat seperti "tidak berpengaruh".
- **Probe 5 (flash accounting) — delta tidak pernah di-settle.** `unlock()` kembali tanpa cek
  delta nol. Kontrak aman revert `delta0 not settled`.

**Trap harness:** `unlock()` memanggil `msg.sender.call(data)`, jadi caller harus mengekspos fungsi
yang dituju. Dan delta dibukukan ke **pemanggil swap** — kalau swap dari test contract lalu unlock
dari helper, delta-nya tidak terlihat. Swap dan unlock harus dari kontrak yang sama.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

forge test --match-path test/AmmHooksCalibration.t.sol -vvv
forge test --match-test test_Probe2_SingletonCrossPoolReentrancy -vvvv
```

| | |
|---|---|
| file | `test/AmmHooksCalibration.t.sol` |
| suite | `AmmHooksCalibration` |
| probes | `test_Probe1_UnrestrictedHookInstall` · `test_Probe2_SingletonCrossPoolReentrancy` · `test_Probe3_FeeMutatedMidSwap` · `test_Probe5_UnsettledDelta` |
| control | `test_Control_ApprovedHookWorks` |

Cross-pool reentrancy is the one that only exists in a **singleton** design — if your fork test
shows no cross-pool effect, check that both pools really share the manager before writing it off.

