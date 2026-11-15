---
name: hunt-diamond-proxy
description: Hunt EIP-2535 diamond, proxy, and upgradeability bugs — facet selector collision, unguarded diamondCut, storage collision across facets, beacon/implementation swap, and initializer replay. Use when a target is upgradeable, uses delegatecall, has facets, or has an implementation slot.
metadata:
  hermes:
    tags: [web3, diamond, eip-2535, proxy, upgradeability, storage-collision, critical]
    related_skills: [web3-audit, smart-contract-audit, hunt-aa-modular, onchain-finding-verification]
---

# Hunt — Diamond, Proxy & Upgradeability

Upgradeability is a deliberate delegatecall to mutable code. The bug classes are: **who can
upgrade**, **what the upgrade can reach**, and **what the storage layout breaks**.

## When to use

- Target has `diamondCut`, `facet`, `loupe`, or an EIP-2535 implementation.
- Target has `upgradeTo`, `upgradeToAndCall`, `_authorizeUpgrade`, or an implementation slot.
- Target uses `delegatecall` anywhere.
- Target has `initialize(` with an `initializer` modifier.

---

## Phase 0 — Identify the pattern

```bash
rg -n "diamondCut|facetCut|IDiamond|IDiamondLoupe" -l
rg -n "upgradeTo|upgradeToAndCall|_authorizeUpgrade|UUPS|Transparent|Beacon" -l
rg -n "delegatecall" -B 3 -A 3
rg -n "ERC1967|implementation.*slot|0x360894a13ba1a3210667c828492db98dca3e2076" -B 2 -A 2
```

| Pattern | Where the bug lives |
|---|---|
| EIP-2535 diamond | `diamondCut` access control + facet selector collision + storage layout |
| UUPS | `_authorizeUpgrade` + `selfdestruct`/`delegatecall` in the implementation |
| Transparent proxy | admin/implementation confusion (mostly solved by OZ, check the version) |
| Beacon | beacon address mutability + beacon implementation |
| Minimal proxy (EIP-1167) | implementation immutability (usually safe) |

---

## Phase 1 — `diamondCut` access control

```bash
rg -n "function diamondCut" -A 25
rg -n "onlyOwner|onlyGovernance|msg.sender ==" -B 3 -A 3
```

| Probe | Decisive result |
|---|---|
| 1. Call `diamondCut` from a non-owner | Revert = guarded |
| 2. Is the owner an EOA, a timelock, or a multisig? | EOA owner = single point of failure (severity depends on program scope) |
| 3. Can `diamondCut` add a facet whose function **replaces** an existing selector? | Selector hijack — a new facet silently takes over `transfer` |
| 4. Can `diamondCut` remove the facet that contains `diamondCut` itself? | Bricking / self-removal |
| 5. Is there a timelock on the cut? | Instant upgrade = no user defence window |

**Rule:** an unguarded `diamondCut` is Critical only if you show what the replacement facet can
do (drain, mint, seize). "Owner can upgrade" with a timelocked multisig owner is a centralisation
note.

---

## Phase 2 — Facet selector collision & hijack

EIP-2535 dispatches by selector. Two facets registering the same selector: the **last registered
wins** (implementation-dependent).

```bash
rg -n "selectorToFacet|facetAddresses|facetFunctionSelectors" -A 8
```

| Probe | Finding shape |
|---|---|
| Register a facet with a selector that already exists | Silent override of an existing function |
| Remove a facet but leave its selector mapped | Calls to a removed facet revert or hit a stale address |
| `diamondCut` with `_action = Replace` on a core selector (`diamondCut`, `owner`) | Takeover of the upgrade mechanism itself |
| Selector registered to `address(0)` | Calls revert; griefing |

Probe: enumerate `facetFunctionSelectors` for duplicates. Then, on a fork, `diamondCut` a new
facet over an existing selector and confirm the new code runs.

---

## Phase 3 — Storage collision across facets

Diamond storage must be namespaced per facet. The classic bug: two facets use slot 0.

```bash
rg -n "^\s*(uint|address|bool|mapping|bytes32)\s+(public\s+)?\w+\s*[;=]" --include='*.sol' -n
rg -n "DIAMOND_STORAGE_POSITION|storagePosition|keccak256\(.*storage" -B 2 -A 4
```

| Check | Finding shape |
|---|---|
| Facet A declares `address owner` at slot 0, facet B declares `uint256 fee` at slot 0 | Writing `fee` overwrites `owner` |
| Inheritance order differs between facets | Same-named variable, different slot |
| A facet inherits a base contract whose variables are not namespaced | Third-party base writes into facet storage |
| Upgrade adds a variable **before** existing ones | All subsequent slots shift |

Probe: on a fork, write to the suspected colliding variable in facet A, then read the variable
in facet B. If the value changed, collision confirmed.

---

## Phase 4 — Initializer replay & uninitialized implementation

```bash
rg -n "function initialize" -A 15
rg -n "initializer|_initialized|_constructing" -B 2 -A 2
```

| Bug | Probe |
|---|---|
| `initialize` callable on the implementation contract directly | Call `initialize` on the impl, become owner of the implementation |
| `initialize` callable twice on the proxy | Re-run initialisation, reset ownership |
| No `_disableInitializers()` in the implementation constructor | Implementation left initializable |
| `constructor` sets state that the proxy never gets | Implementation-only state assumed present |

Probe: call `initialize` on the **implementation address** directly. If it succeeds, the
implementation is hijackable — and depending on the delegatecall path, that can reach the proxy.

---

## Phase 5 — UUPS / beacon specifics

| Bug | Probe |
|---|---|
| Implementation contains `selfdestruct` or `delegatecall` to a mutable target | Upgrade to a facet that self-destructs the proxy |
| `_authorizeUpgrade` is `onlyOwner` but the owner is the proxy itself | Circular authority |
| Beacon address is mutable by a weak role | All proxies pointing at the beacon upgrade at once |
| Beacon implementation is uninitialised | Same as Phase 4 |
| `upgradeToAndCall` with attacker-controlled `data` | Delegatecall into arbitrary init logic |

```bash
rg -n "selfdestruct|suicide" -B 2 -A 2
rg -n "_authorizeUpgrade" -A 8
rg -n "beacon|Beacon" -B 2 -A 4
```

---

## Phase 6 — Static-analysis false positives (do not report these)

`unprotected-upgrade` from slither/aderyn is the classic FP: the analyzer cannot resolve an
`initializer` modifier **inherited** from a dependency reached via a storage base contract.

Verified FP: `initialize(...) external onlyImpl initializer` where
`onlyImpl = require(msg.sender == _implementation())`. Calling through a public `Multicall`
(delegatecall sets `msg.sender == proxy`) still reverts. FP.

**Always walk the inheritance chain to the storage/base contract and read the real modifier
definition** under `node_modules/.pnpm/<pkg>@<ver>/node_modules/...` before reporting.

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `diamondCut`/`upgradeTo` dari non-owner | Inti kelas — upgrade authority |
| 2 | Selector collision: enumerate `facetFunctionSelectors` untuk duplikat | Facet hijack |
| 3 | Storage collision: tulis di facet A, baca di facet B (fork) | Korupsi lintas facet |
| 4 | `initialize` pada implementation address langsung + double-init pada proxy | Implementation hijack |
| 5 | Inheritance walk sampai base contract untuk setiap analyzer hit | FP `unprotected-upgrade` klasik |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret: *"Penyerang memanggil `diamondCut` karena `facetAddress(0)` tidak memeriksa
`msg.sender`, mengganti facet `withdraw` dengan implementasi saya, lalu menarik seluruh saldo."*
Bukan lolos gate: "tidak ada event emitted", "storage layout berpotensi bentrok".
Sebutkan selector atau facet yang berhasil diganti.

**2. Apa yang hilang dari korban, dan berapa?**
Kelas ini bisa Critical **hanya** kalau upgrade path menguasai dana atau izin:
*"Semua 340 ETH di kontrak berhasil ditarik ke penyerang setelah facet diganti."*
Kalau yang terbukti hanya "bisa mengganti fungsi view" atau "storage slot bertabrakan tapi tidak
ada efek teramati" → Medium/hardening, bukan Critical.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] `diamondCut`/`upgradeTo` dipanggil dari akun **tanpa** role, bukan dari owner
- [ ] Saldo sebelum vs sesudah dicatat (angka, bukan klaim)
- [ ] Untuk storage collision: tulis di facet A lalu baca di facet B **di fork**, bukan dari
      pembacaan `solc --storage-layout` saja (analyzer sering FP — lihat Phase 6)

**Analyzer hit (`unprotected-upgrade`, `delegatecall-loop`) bukan bukti.** Wajib inheritance walk
sampai base contract dulu; kalau modifier ada di base, hit itu false positive.

## Eskalasi wajib

**Primitif:** upgrade tanpa guard / selector collision / storage collision / impl hijack.
**Rantai:** unguarded `diamondCut` → replace facet dengan kode attacker → drain. Storage
collision → overwrite `owner` → jadi admin. Impl hijack → delegatecall ke impl yang di-`initialize`.
**Eskalasi ke:** `web3-audit` (kelas proxy), `hunt-aa-modular` (module install mirip),
`smart-contract-audit`, `onchain-finding-verification`.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<RPC>; D=<DIAMOND_ADDR>

# 1) upgrade authority — try diamondCut from a NON-owner key
cast call $D 'owner()(address)' --rpc-url $RPC 2>/dev/null
cast call $D 'facetAddress(bytes4)(address)' 0x1f931c1c --rpc-url $RPC
cast send $D 'diamondCut((address,uint8,bytes4[])[],address,bytes)' '[]' 0x0 0x \
  --private-key 0xA11CE --rpc-url $RPC --dry-run     # does it revert?

# 2) selector collision — enumerate and look for duplicates across facets
cast call $D 'facets()((address,bytes4[])[])' --rpc-url $RPC 2>/dev/null | head -40
# duplicate selectors = last-registered wins -> facet hijack candidate

# 3) storage collision — the addresses() map tells you which slots are used
cast call $D 'addresses()(address[])' --rpc-url $RPC 2>/dev/null | head

# 4) initializer on the implementation + double-init on the proxy
IMPL=$(cast call $D 'facetAddress(bytes4)(address)' 0x00000000 --rpc-url $RPC 2>/dev/null)
cast call $IMPL 'owner()(address)' --rpc-url $RPC        # unprotected impl?
cast send $D 'initialize()' --private-key 0xA11CE --rpc-url $RPC --dry-run

# 5) inheritance walk before believing an analyzer hit
#    for each `unprotected-upgrade` hit, print the whole chain:
cast inspect <ADDR> inheritance --rpc-url $RPC 2>/dev/null || \
  forge inspect <ContractName> inheritance
```

**Report gate:** lab proof = `test/RestakingIntentDiamondCalibration.t.sol --match-contract
DiamondProxyCalibration`. Analyzer output is a lead; the finding is a facet swapped
by a non-owner with funds moving.

---

## By-design calibration

- `diamondCut` dengan timelocked multisig + selector collision dicek = the fix.
- `_disableInitializers()` di constructor implementation = correct.
- Storage yang di-namespace per facet (`DIAMOND_STORAGE_POSITION`) = correct.
- UUPS dengan `_authorizeUpgrade` governance-only = desain yang wajar (catat sebagai
  centralisation note kalau program mengecualikannya).
- Transparent proxy OZ versi terkini = admin/impl confusion sudah di-solve.

## 2026 sweep

- **EIP-7702 sebagai "proxy untuk EOA"** — EOA yang di-delegasi ke kontrak dengan storage;
  `eth_getStorageAt` pada EOA sekarang balik nilai. Kontrak yang menganggap EOA tidak punya
  storage jadi salah.
- **Diamond + ERC-7579** — diamond sebagai smart account dengan module; `diamondCut` menambah
  facet yang merupakan module attacker.
- **Minimal proxy clone dengan implementation yang bisa di-selfdestruct** — EIP-1167 clone yang
  menunjuk implementation yang mengandung `selfdestruct`; upgrade impl → clone mati.
- **Beacon proxy chain** — beacon menunjuk beacon kedua yang menunjuk implementation; satu
  tingkat yang lemah = semua proxy terdampak.
- **`upgradeToAndCall` dengan `data` yang bukan init function** — delegatecall ke fungsi biasa
  dengan `msg.sender` = proxy; kalau fungsi itu privileged dan hanya cek `msg.sender`, attacker
  bisa memanggilnya lewat upgrade path.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

`diamondCut` tanpa guard → replace facet → drain; selector collision → facet hijack; storage collision → overwrite `owner`; `initialize` pada implementation langsung. Kalibrasi: timelocked multisig + `_disableInitializers()` = the fix; owner EOA tanpa fund-loss path = centralisation note.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 4/4 probes passed)

Diuji pada EIP-2535 diamond (`test/RestakingIntentDiamondCalibration.t.sol`, kontrak
`DiamondProxyCalibration`). Yang terkonfirmasi:

- **Probe 1 (`diamondCut` tanpa guard) — penyerang mengganti facet.** `selectorToFacet[setTotalA]`
  berpindah ke `FacetB` dari address attacker. Tidak ada `onlyOwner`.
- **Probe 2 (selector hijack) — `setTotalA()` diam-diam dirutekan ke FacetB** setelah cut kedua pada
  selector yang sama. Cut tidak menolak duplikat; yang terakhir menang.
- **Probe 3 (storage collision) — terbukti numerik:** tulis `FacetA.setTotalA(111)`, baca
  `FacetB.getFeeB()` → **111**. Kedua facet mendeklarasikan state variable pertama di slot 0.
  Inilah bukti yang selama ini saya tulis sebagai teori; sekarang ada angkanya.
- **Probe 4 (initializer replay) — `initialize()` bisa dipanggil berkali-kali,** owner diambil alih
  dua kali berturut-turut oleh dua address berbeda. Tidak ada `initializer` modifier dan tidak ada
  `_disableInitializers()`.

**Trap harness:** untuk memanggil fungsi facet lewat diamond, **setiap** selector yang dipakai harus
di-cut (`setFeeB` DAN `getFeeB`). Kalau hanya `setFeeB` yang di-cut, `getFeeB()` jatuh ke fallback
tanpa facet dan `staticcall` mengembalikan garbage — yang terlihat seperti "collision tidak terjadi"
padahal harness-nya kurang satu selector.

**Pelajaran paling transferable:** jangan asumsikan layout storage. Deklarasikan, cut, tulis lewat
satu facet, baca lewat facet lain, bandingkan angkanya. Teori collision tanpa angka = tidak
terbukti.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

# diamond probes live in the restaking/intent/diamond file (3 suites)
forge test --match-path test/RestakingIntentDiamondCalibration.t.sol --match-contract DiamondProxyCalibration -vvv
forge test --match-test test_Probe3_StorageCollision -vvvv
```

| | |
|---|---|
| file | `test/RestakingIntentDiamondCalibration.t.sol` |
| suite | `DiamondProxyCalibration` |
| probes | `test_Probe1_UnprotectedDiamondCut` · `test_Probe2_SelectorHijack` · `test_Probe3_StorageCollision` · `test_Probe4_InitializerReplay` |

`--match-contract DiamondProxyCalibration` is required: the file holds three suites
(Restaking / Intent / Diamond). Running the whole file also works but mixes classes.

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/rce-surface-atlas.md`) — the 10 RCE entry points (7 web2 + 3 web3 analogues): where to look, what proves execution, severity per surface. This skill is the payload depth; the atlas is the coverage checklist.
