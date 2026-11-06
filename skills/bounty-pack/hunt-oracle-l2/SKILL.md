---
name: hunt-oracle-l2
description: Hunt L2 oracle and sequencer-uptime bugs — stale price during sequencer downtime, missing grace period, confidence-interval ignored, cross-chain oracle replay, and the Chainlink/Pyth integration mistakes that still pay in 2026. Use when a target is an L2 app, a lending/perp protocol reading a sequencer feed, or any contract with an oracle integration.
metadata:
  hermes:
    tags: [web3, oracle, sequencer-uptime, l2, chainlink, pyth, staleness, critical]
    related_skills: [web3-audit, hunt-amm-hooks, hunt-restaking-lrt, onchain-finding-verification]
---

# Hunt — L2 Oracles & Sequencer Uptime

An oracle bug is only exploitable when someone can *act* on the bad price. The 2026 shapes are:
sequencer downtime with no grace period, confidence intervals ignored, and cross-chain oracle
replay.

## When to use

- Target runs on an L2 (Base, Arbitrum, Optimism, Scroll, zkSync, or a chainlist entry).
- Target reads `sequencerUptimeFeed`, `answer`, `latestRoundData`, `getPriceUnsafe`, or `price.conf`.
- Target is a lending, perp, or liquidation engine with any price dependency.
- Target bridges a price from another chain.

---

## Phase 0 — Read the integration, not the oracle

The oracle is usually fine. The *integration* is the bug. For every price read, write down:

1. Which function is called (`latestRoundData` vs `getPriceUnsafe` vs `latestAnswer`).
2. Which fields are checked (`updatedAt`, `answeredInRound`, `confidence`, `sequencerGracePeriod`).
3. Who can act on the price (borrow, liquidate, mint, settle).

```bash
rg -n "latestRoundData|latestAnswer|getPrice|getPriceUnsafe|getPriceNoOlderThan" -B 3 -A 12
rg -n "sequencerUptimeFeed|isSequencerUp|gracePeriod|GRACE_PERIOD" -B 2 -A 4
rg -n "updatedAt|answeredInRound|roundId|confidence" -B 2 -A 2
```

---

## Phase 1 — Sequencer uptime (the L2-specific Critical)

On an L2, when the sequencer goes down, users cannot submit txs to exit, but **price feeds keep
updating** (or freeze). A protocol that lets borrowing/liquidation proceed during downtime is
exploitable: the user cannot defend their position.

The correct integration:
```solidity
(address roundAddress, int256 answer) = sequencerUptimeFeed.latestRoundData();
require(answer == 0, "Sequencer is down");           // 0 = up, 1 = down
uint256 timeSinceUp = block.timestamp - roundStartedAt;
require(timeSinceUp >= GRACE_PERIOD, "Grace period not over");
```

| Bug | Probe |
|---|---|
| No uptime check at all | Read the sequencer feed status, then attempt a borrow during a simulated downtime |
| Uptime checked but no grace period | Price is stale-from-before-downtime; borrow against it |
| Grace period checked against the wrong timestamp | `block.timestamp - updatedAt` instead of `- roundStartedAt` |
| Uptime feed address hardcoded to the wrong chain | Feed always returns "up" |
| Downtime detected but only `revert`s on mint, not on liquidate | Liquidation during downtime |

Probe (fork): set the uptime feed to "down", advance time past the grace period, attempt the
privileged action. Then set it to "down" and attempt *before* the grace period. Both must revert.

---

## Phase 2 — Staleness & round completeness (Chainlink)

```bash
rg -n "latestRoundData" -A 15
```

The four checks that are usually missing:

| Check | Consequence if missing |
|---|---|
| `answer > 0` | Zero/negative price → free assets |
| `updatedAt != 0` and recent | Stale price from a frozen feed |
| `answeredInRound >= roundId` | Round is incomplete; the answer is from a previous round |
| `block.timestamp - updatedAt < heartbeat × 2` | Price older than the feed's update cadence |

Probe: on a fork, set `updatedAt` to `block.timestamp - 10 days` and attempt the privileged
action. Must revert.

---

## Phase 3 — Pyth confidence interval

Pyth returns `(price, conf, expo)`. `conf` is the uncertainty band. A contract that reads only
`price` accepts a price with arbitrarily wide uncertainty.

```bash
rg -n "getPriceUnsafe|getPriceNoOlderThan|\.conf\b|confidence" -B 2 -A 6
```

| Bug | Probe |
|---|---|
| `getPriceUnsafe` used (no staleness check at all) | Read a price with an old `publishTime` |
| `conf` ignored | Find a price with `conf / price > 5%` and use it |
| `expo` sign mishandled | Price off by 10^18 |
| No `price` sanity bound (e.g. `price <= MAX_PRICE`) | A corrupted feed reports an absurd price |

Probe: obtain a Pyth update with a wide confidence band, submit it, and check whether the
contract accepts it. Also submit an update with a `publishTime` far in the past.

---

## Phase 4 — Cross-chain oracle replay

A price bridged from chain A to chain B:

| Bug | Probe |
|---|---|
| Bridged price not bound to a chain id | Replay a mainnet price on an L2 |
| No "source chain is live" check | Mainnet halted, L2 keeps using the last price |
| Bridge delay not accounted for | Price is N minutes old by the time it lands |
| Single relayer pushes the price | Compromised relayer = arbitrary price |

```bash
rg -n "chainId|sourceChain|srcChainId" -B 2 -A 2
rg -n "onlyRelayer|onlyOracle|pushedBy" -B 2 -A 2
```

---

## Phase 5 — The exploitation gate (do not skip)

A bad price read is a **primitive**. Before reporting, prove someone can act on it:

| Action | Must be reachable by the attacker |
|---|---|
| Borrow against an inflated collateral price | Yes / No |
| Liquidate a healthy position with a depressed price | Yes / No |
| Mint with a stale price | Yes / No |
| Settle a perp at a manipulated mark | Yes / No |

If no privileged action reads the manipulated price, it is a hardening note. Say so.

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Sequencer uptime: down + sebelum grace, down + sesudah grace, up | Inti kelas L2 |
| 2 | Staleness: `updatedAt` lampau + `answeredInRound < roundId` + `answer <= 0` | Chainlink round completeness |
| 3 | Pyth: `getPriceUnsafe` + `conf` lebar + `publishTime` lampau | Confidence & staleness |
| 4 | Cross-chain replay: price chain A dipakai di chain B / fork | Under-bound bridged price |
| 5 | Exploitation gate: aksi privileged yang membaca harga manipulasi | Tanpa ini = hardening note, bukan temuan |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harga yang basi **bukan** temuan sampai ada yang bisa bertindak atasnya. Bentuk yang lolos:
*"Saat sequencer down, `latestRoundData()` masih mengembalikan harga 2 jam lalu tanpa check
`SequencerUptimeFeed`. Dalam window itu penyerang memakai harga basi untuk meminjam 180 ETH
terhadap kolateral yang sebenarnya sudah turun 40%."*
Bukan lolos gate: "tidak ada staleness check", "grace period tidak diimplementasikan".

**2. Apa yang hilang dari korban, dan berapa?**
Kelas oracle hampir selalu berujung ke **bad debt protokol** atau **likuidasi tidak adil**:
*"Protokol menanggung 180 ETH bad debt"* atau *"12 posisi dilikuidasi pada harga yang tidak pernah
ada di pasar, kerugian user 63 ETH."*
Kalau tidak ada aksi privileged yang membaca harga itu → ini **hardening note**, bukan temuan.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] State oracle dimanipulasi di dalam test (`vm.mockCall` pada feed / `vm.warp` untuk staleness)
- [ ] Aksi privileged dijalankan **dan** dampak finansialnya dihitung
- [ ] Untuk sequencer: tiga kondisi diuji (down+sebelum grace, down+sesudah grace, up)

**Jangan pakai harga "basi" dari fork yang tidak di-refresh sebagai bukti.** Kalau feed di fork
memang sudah lama tidak update, itu artefak fork, bukan bug target — refresh atau mock secara
eksplisit.

## Eskalasi wajib

**Primitif:** harga stale / conf diabaikan / uptime tidak dicek / replay lintas chain.
**Rantai:** uptime tidak dicek → borrow saat sequencer down → user tidak bisa defend → likuidasi
paksa. Staleness → borrow terhadap harga beku → undercollateralised.
**Eskalasi ke:** `web3-audit` (kelas oracle), `hunt-amm-hooks` (pool sebagai oracle),
`hunt-restaking-lrt`, `onchain-finding-verification`.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<L2_RPC>; C=<CONSUMER_ADDR>; FEED=<CHAINLINK_FEED>

# 1) the integration: does it read the sequencer uptime feed at all?
cast call $C 'sequencerUptimeFeed()(address)' --rpc-url $RPC 2>/dev/null || echo "NO UPTIME FEED READ"
cast call $C 'GRACE_PERIOD()(uint256)' --rpc-url $RPC 2>/dev/null || echo "NO GRACE PERIOD"

# 2) staleness — read the round directly
cast call $FEED 'latestRoundData()(uint80,int256,uint256,uint256,uint80)' --rpc-url $RPC
cast block latest --field timestamp --rpc-url $RPC
# updatedAt far behind block.timestamp, and the consumer does not check it = candidate

# 3) round completeness
cast call $FEED 'getRoundData(uint80)(uint80,int256,uint256,uint256,uint80)' $ROUND --rpc-url $RPC
# answeredInRound < roundId = incomplete round accepted

# 4) Pyth variant — unsafe read + confidence
cast call $PYTH 'getPriceUnsafe(bytes32)((int64,uint64,int32,uint256,uint256))' $PRICE_ID --rpc-url $RPC
cast call $PYTH 'getPrice(bytes32)((int64,uint64,int32,uint256,uint256))' $PRICE_ID --rpc-url $RPC

# 5) the exploitation gate — is the price actually consumed by a privileged action?
cast call $C 'borrow(uint256)' $AMOUNT --from $ATTACKER --rpc-url $RPC 2>/dev/null || \
  cast call $C 'liquidate(address)' $VICTIM --from $ATTACKER --rpc-url $RPC
```

**Report gate:** lab proof = `test/OracleL2Calibration.t.sol`. A stale price with
**nothing reading it** is a hardening note; `test_Probe5_ExploitationGate` is the
deciding probe.

---

## By-design calibration

- Uptime + grace period + staleness + round completeness + conf + sanity bound, semua dicek = correct.
- `getPriceUnsafe` dipakai di path yang **tidak** memindahkan dana (UI display) = by design.
- Oracle dengan heartbeat wajar dan `updatedAt` dicek = the fix.
- Centralisation note (satu relayer) tanpa fund-loss path = Info.
- "On-chain discoverable = not confidential" — jangan lapor eksposur harga on-chain.

## 2026 sweep

- **Pyth pull-oracle dengan BLS signature point-at-infinity** — verifier menerima signature nol
  (Bonzo Finance, Jul 2026): penyerang memalsukan harga. Cek apakah verifier menolak
  point-at-infinity pada kurva BLS.
- **Supra pull-oracle** — model pull butuh submit update; cek apakah update tanpa signature valid
  bisa di-push, dan apakah harga bisa di-submit oleh siapa saja.
- **Sequencer feed yang balas "up" saat chain halted** — uptime feed sendiri adalah kontrak di L2;
  kalau L2 halt, feed ikut berhenti dan nilainya beku di "up".
- **L2 app membaca oracle L1 tanpa delay** — harga L1 yang di-bridge tanpa delay; L1 bisa reorg.
- **Multi-oracle median dengan satu sumber poison** — median dari 3 sumber di mana 1 bisa
  dimanipulasi; median tetap aman hanya kalau manipulasi tidak menggeser nilai tengah. Cek
  apakah ada sumber yang bisa digeser ekstrem oleh satu aktor.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Sequencer uptime tidak dicek → borrow saat downtime → likuidasi paksa; staleness/conf diabaikan → harga beku; bridged price replay lintas chain. Kalibrasi: uptime + grace + staleness + conf + sanity bound semua dicek = correct; `getPriceUnsafe` di path non-dana = by design.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 9/9 probes passed)

Diuji pada lending consumer yang membaca price feed + uptime feed
(`test/OracleL2Calibration.t.sol`). Yang terkonfirmasi dan yang perlu dikoreksi:

- **Probe 1 (uptime) adalah probe paling tajam di kelas ini.** `borrow()` tanpa cek uptime
  berhasil saat sequencer DOWN, sementara `borrowSafe()` (bentuk FIX) revert. Dua fungsi di
  kontrak yang SAMA, satu bocor satu tidak — itulah differential yang harus ditunjukkan.
- **Probe 1b (grace period) butuh mock yang benar.** Mock uptime feed yang cuma balik
  `(roundId, answer)` membuat `startedAt` = 0 → `block.timestamp - 0` selalu > grace → cek
  grace **lolos palsu**. Chainlink's real uptime feed balik 5-tuple
  `(roundId, answer, startedAt, updatedAt, answeredInRound)`. **Verifikasi bentuk return mock-mu
  sebelum menyimpulkan konsumen aman** — ini persis kelas FP yang skill ini coba cegah.
- **Probe 2c (harga negatif) tetap bug meski aritmatika kebetulan aman.** `answer = 0` bikin
  `maxBorrow = 0` sehingga revert — terlihat "aman". Tapi `answer = -1` yang di-cast ke `uint256`
  **underflow** dan revert dengan panic, bukan pesan. Konsumen tidak pernah mengecek `answer > 0`;
  dia selamat karena kebetulan, bukan karena kontrol.
- **Probe 5 (exploitation gate) yang menentukan apakah ini laporan atau catatan.** Harga
  dimanipulasi 10x → `borrow()` terhadap harga itu → utang tercatat 10.000e18. Tanpa probe ini,
  semua temuan di atas cuma hardening note.

**Trap harness:**
- Foundry default `block.timestamp` = 1. Setiap `block.timestamp - N` underflow. Selalu
  `vm.warp(<epoch realistis>)` di `setUp()`.
- Feed 8-desimal vs collateral 18-desimal: tanpa scaling (`× 1e10`) semua perbandingan LTV
  jadi tak bermakna dan test "gagal" karena aritmatika, bukan karena bug.
- `depositCollateral` yang membukukan ke `msg.sender` membuat test yang deposit sebagai test
  contract lalu borrow sebagai `user` membaca collateral NOL. Pakai helper `depositCollateralFor`
  atau `vm.prank` yang konsisten.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

forge test --match-path test/OracleL2Calibration.t.sol -vvv
forge test --match-test test_Probe1_NoUptimeCheckOnBorrow -vvvv
```

| | |
|---|---|
| file | `test/OracleL2Calibration.t.sol` |
| suite | `OracleL2Calibration` |
| probes | `test_Probe1_NoUptimeCheckOnBorrow` · `test_Probe1b_GracePeriodMissing` · `test_Probe2_StalePriceAccepted` · `test_Probe2b_IncompleteRoundAccepted` · `test_Probe2c_NegativePriceUnderflows` · `test_Probe3_ConfidenceIgnored` · `test_Probe3b_PublishTimeIgnored` · `test_Probe5_ExploitationGate` |
| control | `test_Control_SafeConsumerPassesHealthyState` |

`test_Probe5_ExploitationGate` is the one that matters: a stale price with **no privileged
action reading it** is a hardening note. If that probe does not fire on your target, you have
a note, not a finding.

