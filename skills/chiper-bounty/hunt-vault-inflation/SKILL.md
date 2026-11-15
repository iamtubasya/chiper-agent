---
name: hunt-vault-inflation
description: Hunt ERC-4626 vault and share-price manipulation — first-depositor/donation inflation, rounding direction, rebasing and fee-on-transfer tokens, virtual-share bypasses, and the single-vs-multi-party kill test. Use when a target is any vault, staking receipt, LRT, or pool that mints shares against deposited assets.
metadata:
  hermes:
    tags: [web3, erc-4626, vault, inflation-attack, donation, rounding, share-price, critical]
    related_skills: [web3-audit, hunt-amm-hooks, hunt-restaking-lrt, hunt-business-logic, onchain-finding-verification]
---

# Hunt — Vault Inflation & Share-Price Manipulation

ERC-4626 made vaults composable and made the **first depositor** the most dangerous position in
DeFi. This skill is the systematic version of the inflation attack plus the kill tests that stop
it being reported as a false positive.

## When to use

- Target is any vault: ERC-4626, staking receipt, LRT, LP receipt, yield token.
- Target mints shares against deposited assets and has a `convertToShares`/`convertToAssets`.
- Target accepts a **donation** or has any path that moves assets in without minting shares.
- Target supports rebasing, fee-on-transfer, or non-standard ERC-20 tokens.

---

## Phase 0 — The kill test FIRST (single-party vs multi-party)

Before any inflation analysis, answer: **is this vault multi-party at all?**

```bash
rg -n "public\(address\)|public\(HashMap" -A 2          # a single named party var?
rg -n "msg.sender == self\.(lender|owner|vault|borrower)" -B 2 -A 2
rg -n "function .*\(\) .*view.*returns" -A 4 | rg -n "empty\(Struct\)|address\(0\)"
```

If deposit and withdraw are both gated to one address, and the funds getter returns an empty
struct for everyone else, the vault is **single-party**. An inflation attack there lands on the
same person who performs it. **Kill the claim** — or downgrade to a centralisation note.

Verified case (Zharta OTC `claim()`): a lender claims the NFT without paying, the accounting
shrinks the pool total, and in a multi-lender pool that would be a dilution bug. It was not a
finding: OTC pools hold exactly one lender, set once in `initialize()` with no setter.

---

## Phase 1 — First-depositor / donation inflation

The classic shape:

```
1. Attacker mints 1 wei of shares (deposit 1 asset)
2. Attacker donates 1e18 assets directly to the vault (transfer, not deposit)
3. totalAssets jumps; totalShares stays 1
4. Victim deposits 1e18 assets -> rounds down to 0 shares
5. Attacker redeems 1 share -> takes everything
```

Checks in order:

| # | Check | Fix shape |
|---|---|---|
| 1 | Is there a minimum first deposit / dead-shares burn? | Mint `1e3`/`1e6` dead shares to `address(0)` on first deposit |
| 2 | Are virtual shares/assets used in the ratio? | `+1` to both numerator and denominator (OZ `_decimalsOffset`) |
| 3 | Does a direct `transfer` to the vault move `totalAssets`? | `totalAssets` must be an internal counter, not `token.balanceOf(this)` |
| 4 | Is rounding direction correct? | Deposit: round shares **down**. Withdraw: round assets **down**. |
| 5 | Can the attacker donate *and* deposit in the same tx to beat a dead-share floor? | Dead shares must be large enough that the donation cost exceeds the gain |

```bash
rg -n "totalAssets|totalSupply" -B 2 -A 4
rg -n "balanceOf\(address\(this\)\)|balanceOf\(this\)" -B 2 -A 2   # BAD: live balance as totalAssets
rg -n "decimalsOffset|virtualShares|DEAD_SHARES|MIN_SHARES" -B 2 -A 2
rg -n "mulDiv|Math.mulDiv" -B 2 -A 2 | rg -n "Rounding"
```

**Economics gate:** compute attacker cost (donation + gas) vs gain (victim deposit). If the
donation required exceeds the extractable amount, the attack is not profitable and the finding is
a hardening note. Show the arithmetic.

---

## Phase 2 — Rounding in conversion

Every `convertToShares` / `convertToAssets` is a rounding decision.

| Bug | Probe |
|---|---|
| Rounding up on deposit | Attacker deposits dust repeatedly, gains a share each time |
| Rounding down on withdraw | Victim loses dust on every withdrawal |
| Asymmetric rounding between `deposit` and `mint` | `mint(shares)` and `deposit(assets)` give different rates for the same value |
| Rounding applied before the fee instead of after | Fee is rounded away to zero on small amounts |
| Precision loss on low-decimal tokens | 6-decimal token with 18-decimal share math |

Probe: on a fork, deposit 1 wei, 2 wei, … 20 wei and record the shares minted each time. Any
monotonic gain per unit beyond 1:1 is a rounding leak. Then withdraw the same dust and record
assets returned.

---

## Phase 3 — Non-standard token support

| Token type | Bug shape | Probe |
|---|---|---|
| Fee-on-transfer | Vault credits `amount` but receives `amount - fee` → `totalAssets` overcounts | Deposit, then compare `balanceOf(vault)` delta vs credited |
| Rebasing (stETH-style) | `totalAssets` counter drifts from the real balance | Accrue a positive rebase, check the counter |
| Rebasing negative | Balance decreases without a withdrawal → last redeemer eats the loss | Trigger a negative rebase |
| ERC-777 hooks | `tokensReceived` callback re-enters the vault | Deposit with a hook-enabled token and a re-entering receiver |
| Double-entry (token lists itself) | Vault accepts its own share token as the asset | Deposit the share token into itself |
| ERC-20 with blocklist | A blocked recipient bricks withdrawals for everyone | Block a holder, attempt a full withdrawal |

```bash
rg -n "safeTransferFrom|safeTransfer" -B 2 -A 2
rg -n "balanceOf\(address\(this\)\)" -B 3 -A 3
rg -n "feeOnTransfer|deflationary|rebasing" -i -B 2 -A 2
```

---

## Phase 4 — Share/asset desync paths

The invariant is `totalShares × price == totalAssets`. Any path that breaks one side:

| Path | Check |
|---|---|
| `mint()` bypasses a check `deposit()` has | Compare the two functions line by line (MetaPool pattern) |
| Donation path updates assets but not shares | Direct transfer vs `deposit` |
| Slash/penalty reduces assets but not the rate used for redemption | Restaking LRT |
| Harvest/compound credits assets to the vault but not to `totalAssets` | Strategy profit not accounted |
| A second vault wraps this one and double-counts | Recursive wrapping |

```bash
rg -n "function (deposit|mint|withdraw|redeem)\(" -A 20
# diff deposit vs mint, withdraw vs redeem — the missing require is the bug
```

---

## Phase 5 — Prove the loss before reporting

An inflation pattern LOOKS like theft but frequently is not. Before filing:

1. **Compute the pool's price invariant.** In a constant-price/linear pool the mint→burn
   round-trip returns ~the same tokens regardless of prior inflation — the victim gets fewer
   *shares* but redeems ~the same *tokens*. No fund loss.
2. **Compute attacker P&L:** `claim − (initial_mint + injected + gas)`. Net ~0 = not reportable.
3. **Check duplication:** if the team already fixed the same root cause (git history, CHANGELOG,
   an audit PDF in the PR), a sibling path is a **known issue → out of scope**.
4. **Check single-party** (Phase 0).

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Single-party vs multi-party kill test (`public(address)` + gated deposit/withdraw) | Kill claim sebelum buang waktu |
| 2 | First-depositor: mint 1 wei → donate → victim deposit → cek share victim | Inti inflation attack |
| 3 | Rounding sweep: deposit 1..20 wei + withdraw 1..20 wei, catat rate | Rounding leak terukur |
| 4 | Non-standard token: fee-on-transfer delta + rebase drift + ERC-777 hook | totalAssets desync |
| 5 | Attacker P&L eksplisit + duplication check (git history/CHANGELOG) | Tanpa net loss = hardening note |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret: *"Penyerang mint 1 wei share, mendonasikan 10.000 USDC langsung ke vault, lalu
korban deposit 9.999 USDC dan menerima **0 share**; penyerang redeem dan mengambil seluruh
19.999 USDC."*
Bukan lolos gate: "tidak ada dead shares", "konversi memakai pembulatan ke bawah".
Sebutkan urutan panggilan persisnya.

**2. Apa yang hilang dari korban, dan berapa?**
Harus berupa **kerugian deposit korban yang terukur**: *"Korban kehilangan 9.999 USDC (100% dari
depositnya)."*
Kalau korban hanya mendapat share lebih sedikit tapi tetap proporsional (mis. 0,3% lebih sedikit)
→ itu rounding dust, bukan inflation attack; turunkan atau buang. **Attacker P&L wajib positif
setelah gas** — kalau negatif, tidak ada insentif, bukan temuan.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] Tiga aktor di dalam test: attacker, korban, dan vault dengan token nyata
- [ ] Share korban + saldo attacker dihitung **sebelum vs sesudah** (angka)
- [ ] Duplication check: grep git history / CHANGELOG / audit report — kalau sudah dilaporkan
      atau sudah dimitigasi (dead shares, virtual offset), itu bukan temuan baru
- [ ] Kalau `totalSupply == 0` dilarang oleh kontrak → attack vector ini tertutup, catat negatif

**Single-party test dulu** (`public(address)`, deposit/withdraw tanpa gate) — kalau satu pihak
tidak bisa memicu, buang lebih awal sebelum menyusun PoC panjang.

## Eskalasi wajib

**Primitif:** share price manipulable / rounding leak / totalAssets desync.
**Rantai:** inflation → victim dapat 0 share → attacker redeem semua → vault insolvency.
Fee-on-transfer desync → `totalAssets` overcount → last redeemer tidak bisa redeem.
**Eskalasi ke:** `web3-audit` (kelas 6 ERC4626), `hunt-amm-hooks`, `hunt-restaking-lrt`,
`hunt-business-logic`, `onchain-finding-verification`.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<RPC>; V=<VAULT_ADDR>; A=$(cast wallet address --private-key 0xA11CE)

# 1) single-party kill test FIRST — can one actor even move the share price?
cast call $V 'totalSupply()(uint256)' --rpc-url $RPC
cast call $V 'totalAssets()(uint256)' --rpc-url $RPC
cast call $V 'deposit(uint256,address)(uint256)' 1 $A --from $A --rpc-url $RPC 2>/dev/null
# if deposit(0-supply) is blocked or dead-shares exist, this vector is closed

# 2) conversion rate — the number the attack moves
cast call $V 'convertToShares(uint256)(uint256)' 1000000000000000000 --rpc-url $RPC
cast call $V 'previewDeposit(uint256)(uint256)' 1000000000000000000 --rpc-url $RPC

# 3) donation path — can you just transfer tokens in (no deposit)?
cast send $TOKEN 'transfer(address,uint256)' $V 10000000000000000000000 \
  --private-key 0xA11CE --rpc-url $RPC --dry-run

# 4) rounding sweep — 1..20 wei in and out, watch the rate drift
for i in $(seq 1 20); do
  printf 'wei=%s rate=' $i
  cast call $V 'convertToShares(uint256)(uint256)' $i --rpc-url $RPC
done

# 5) non-standard token effects
cast call $TOKEN 'totalSupply()(uint256)' --rpc-url $RPC
cast call $V 'asset()(address)' --rpc-url $RPC
# fee-on-transfer / rebase: compare the vault's stored balance vs token balanceOf
```

**Report gate:** lab proof = `test/VaultInflationCalibration.t.sol`. Run
`test_Probe0_SinglePartyKillTest` first, then `test_Probe4_AttackerPnL_EconomicsGate`
— no positive P&L after gas means no finding.

---

## By-design calibration

- Dead shares / decimals offset / virtual shares = the fix.
- `totalAssets` sebagai internal counter (bukan `balanceOf(this)`) = correct.
- Single-party vault = inflation attack lands on the attacker, kill the claim.
- **Par-denominated ERC-4626 wrapper (shares = Par, not a fraction) = inflation attack N/A — kill the
  claim.** When `balanceOf`/`totalSupply` return the money-market's interest-adjusted **Par** balances and
  `convertToShares(x)` = `weiToPar(x)` / `convertToAssets(x)` = `parToWei(x)` are driven by the interest
  index (NOT a `totalAssets/totalSupply` ratio), a direct donation moves *neither* `totalSupply` (par) nor
  `totalAssets` (`parToWei(totalSupply)`), so the first-depositor/donation inflation cannot shift the share
  price at all. Live case: Dolomite `DolomiteERC4626` (dToken) — shares are par balances, rounding/lossy-xfer
  handled by a `_getIsLossy` vaporize mechanism, no dead-shares/virtual-offset needed. Grep the kill signal:
  `convertToShares`/`convertToAssets` calling `weiToPar`/`parToWei` and `totalAssets()` returning
  `parToWei(totalSupply())` instead of `token.balanceOf(this)`.
- Constant-price pool di mana mint→burn round-trip mengembalikan ~token yang sama = no fund loss.
- Rounding yang terdokumentasi dan konsisten (selalu ke bawah untuk user) = desain.

## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Kondisi | Severity |
|---|---|
| First-depositor/donation inflation → victim deposit dapat 0 share → drain vault | Critical |
| `totalAssets` desync (fee-on-transfer/rebasing) → last redeemer tidak bisa redeem | Critical |
| Rounding leak yang terakumulasi → insolvency bertahap | High-Critical |
| Single-party pool dengan asimetri yang sama | Info (kill claim) |
| Rounding 1 wei per operasi tanpa jalur akumulasi | Low |

**Kalibrasi wajib:** hitung attacker P&L eksplisit (`claim − (initial + injected + gas)`). Net ~0
= hardening note. Cek juga apakah tim sudah memperbaiki akar masalah yang sama (git history,
CHANGELOG, audit PDF di PR) — sibling path = known issue → out of scope.

## 2026 sweep

- **ERC-7540 async vault (request/redeem/claim)** — deposit tidak langsung mint share; antara
  request dan claim ada window di mana exchange rate bisa bergerak. Cek rate mana yang dipakai
  (request time vs claim time) dan apakah bisa di-manipulasi di antaranya.
- **ERC-7579 + vault** — vault yang dipech smart account; module bisa memanggil `redeem` dengan
  parameter yang dipilih module, bukan owner.
- **Fee-on-transfer + `totalAssets` counter** — counter naik sebesar `amount` padahal vault hanya
  menerima `amount - fee`; setiap deposit meng-overcount, dan last redeemer tidak bisa redeem
  penuh. Ini tetap bug #1 pada vault 2026.
- **Multi-token vault (ERC-4626 multi-asset)** — `convertToShares` dengan weighted basket;
  satu token yang di-donate menggeser berat dan harga share.
- **Vault-of-vault (recursive)** — vault B memegang share vault A; `totalAssets` B dihitung dari
  `convertToAssets` A yang bisa berubah antara blok; reentrancy lewat callback token A.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 6/6 probes passed)

Diuji pada vault ERC-4626 rentan yang dibangun khusus (`test/VaultInflationCalibration.t.sol`).
Yang berubah dari dugaan awal:

- **Probe 1 (inflation) — angka sebenarnya bukan "attacker ambil semua".** Donation 1000e18 +
  victim deposit 500e18: attacker net gain **500e18 (50% efisiensi)**, victim kehilangan **seluruh
  500e18 (0 share)**. Klaim yang benar di laporan adalah *"victim loses X"*, bukan *"attacker
  steals X"*. Menulis "attacker stole 500" padahal dia menanam 1000 = laporan yang bisa dipatahkan
  triager.
- **`require(shares > 0)` adalah pertahanan nyata.** Kalau vault punya guard itu, attack path
  probe-1 mati di deposit victim — tapi probe-2 (rounding leak) masih hidup karena dust deposit
  mengembalikan 0 share DAN mengambil aset. Dua bug, dua severity, dua laporan.
- **Probe 2 mengukur persis:** deposit 1 → 0 share, 2 → 1, 3 → 2, 5 → 4, 7 → 6, 11 → 10. Setiap
  deposit kehilangan ~1 wei share. Itu rounding leak yang terukur, bukan dugaan.
- **Probe 3 (fee-on-transfer) mendarat di tempat yang berbeda dari dugaan.** Vault menerima
  990e18 tapi meng-kredit 1000e18 share → `totalAssets` = 990e18 dan victim yang redeem terakhir
  **hanya dapat 664e18 dari 1000e18** yang disetor. Kerugian ~33%, bukan "dust".
- **Probe 0 (single-party kill test) bekerja seperti tertulis** — dan itu yang menyelamatkan
  waktu: kalau pool single-party, seluruh analisis inflation di atas jadi tidak relevan.

**Trap harness yang wajib diingat:** `sload(0)` di dalam test membaca storage TEST contract, bukan
target. Selalu `vm.load(address(target), slot)`.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

forge test --match-path test/VaultInflationCalibration.t.sol -vvv
forge test --match-test test_Probe1_FirstDepositorInflation -vvvv
```

| | |
|---|---|
| file | `test/VaultInflationCalibration.t.sol` |
| suite | `VaultInflationCalibration` |
| probes | `test_Probe0_SinglePartyKillTest` · `test_Probe1_FirstDepositorInflation` · `test_Probe2_RoundingSweep` · `test_Probe3_FeeOnTransferDesync` · `test_Probe4_AttackerPnL_EconomicsGate` |
| control | `test_Control_CorrectVaultDoesNotFire` |

Run `test_Probe0_SinglePartyKillTest` **first** — it kills the claim before you spend time on a
PoC. `test_Probe4_AttackerPnL_EconomicsGate` is the report gate: no positive attacker P&L after
gas means no finding.

