---
name: hunt-aa-modular
description: Hunt ERC-7579 modular smart accounts and EIP-7702 delegated EOAs. Use when a target ships a smart account, module registry, validator, plugin system, or an EIP-7702 delegation designator. Covers arbitrary-delegatecall via module install, validator bypass, hook/executor abuse, 7702 tx.origin sinks, and the by-design calibration that stops a module registry reading as a vulnerability.
metadata:
  hermes:
    tags: [web3, smart-account, erc-7579, erc-4337, eip-7702, delegatecall, access-control, critical]
    related_skills: [web3-audit, smart-contract-audit, hunt-access-control, hunt-auth-bypass, onchain-finding-verification]
---

# Hunt — Modular Smart Accounts (ERC-7579 / EIP-7702)

Modular accounts moved the attack surface from "the account contract" to **"who can install a module
and what that module is allowed to do"**. A registry without an allowlist is arbitrary code
execution over every account that trusts it. That is the Critical-class primitive this skill hunts.

## When to use

- Target ships `installModule`, `uninstallModule`, `setValidator`, `setExecutor`, `setHook`.
- Target ships a module registry / plugin manager / "smart account" SDK.
- Target chain has EIP-7702 active and any contract still guards on `tx.origin` or `ecrecover`.
- Target docs mention "modular", "plugins", "validators", "executors", "hooks", "7702".

---

## Phase 0 — Map the module surface before reading any logic

```bash
# selector census on the account + registry
rg -n "installModule|uninstallModule|setValidator|setExecutor|setHook|replaceModule" -A 6
rg -n "function .*\(.*(uint256|bytes4|bytes32).*\) .*(external|public)"   # moduleType / moduleId args
rg -n "onlyOwner|onlyEntryPoint|onlySelf|require\(msg.sender" -B 3 -A 3  # who may install
```

Answer three questions in writing before going further:

1. **Who can call `installModule`?** The account itself (via `validateUserOp`), the owner, or anyone?
2. **Is the module address validated against a registry/allowlist, or accepted raw?**
3. **What privileges does a module get** — `delegatecall` (storage write as the account) or
   `call` (external only)?

`delegatecall` + no allowlist = game over, that is the finding. `call` + no allowlist = still
serious (the module can move the account's tokens) but a different severity.

---

## Phase 1 — The four primitives

### Primitive 1 — Unrestricted module install (the big one)

```solidity
// VULNERABLE SHAPE
function installModule(uint256 moduleType, address module, bytes calldata data) external {
    modules[moduleType].push(module);          // no allowlist, no owner check beyond entryPoint
    IModule(module).onInstall(data);           // attacker-controlled target, delegatecall inside
}
```

Probe sequence (each is independently decisive):

| # | Probe | Decisive result |
|---|---|---|
| 1 | Call `installModule(1, ATTACKER_ADDR, "0x")` from a controlled account | Revert with `ModuleNotApproved`/`NotInRegistry` = allowlist holds |
| 2 | If it succeeds, `onInstall` runs in the account's context | Any state write / token move = Critical confirmed |
| 3 | Check whether the registry is itself mutable (`addModule` by a role) | Mutable registry + weak role = chain, not a single bug |
| 4 | Check `uninstallModule` — can a *stale* module be re-installed after removal? | Re-install of a previously-approved-then-removed module = allowlist bypass |
| 5 | Check module **type confusion** — install a VALIDATOR address as an EXECUTOR | Type field is trusted, not enforced = privilege confusion |

**Rule:** never report "module install is unrestricted" without proving the module can *do*
something. A registry that accepts any address but whose `onInstall` is a no-op stub is a
hardening note. Show the delegatecall target or the token movement.

### Primitive 2 — Validator bypass (4337 + 7579)

The validator decides whether a UserOp is authorised. Bugs here are direct account takeover.

```bash
rg -n "validateUserOp" -A 25
rg -n "require\(.*signature|ecrecover|ECDSA.recover" -B 4 -A 4
```

Checks:
- **Signature malleability** — does it accept both `s` values (no low-s check)? Then two valid
  signatures per message, and a replay-amplification primitive.
- **Empty signature acceptance** — `if (sig.length == 0) return 0;` as a "session key" path that
  never checks the session key is registered.
- **Validator swap without owner auth** — `setValidator` callable by the entryPoint alone during
  a UserOp whose validation the *old* validator passed. If the old validator is compromised or
  over-permissive, the swap succeeds.
- **`validateUserOp` returning `0` on failure instead of reverting** — ERC-4337 spec says revert;
  a `return 1` from a failed path is silent acceptance.

### Primitive 3 — EIP-7702 `tx.origin` / `ecrecover` sinks

7702 lets an EOA point at an implementation. Contracts written before 7702 assumed
`tx.origin == EOA` and `ecrecover` on an EOA-controlled key. Both assumptions break.

```bash
rg -n "tx\.origin" -B 3 -A 3        # every one is now suspect
rg -n "ecrecover" -B 3 -A 3         # is the recovered address assumed to be an EOA?
rg -n "EXTCODEHASH|extcodesize|code\.length" -B 2 -A 2   # EOA detection that 7702 defeats
```

The sink shape:
```solidity
// pre-7702 "safe" check that 7702 breaks
require(tx.origin == owner, "not owner");
// owner is now a 7702-delegated EOA whose implementation is attacker-controlled,
// and tx.origin still == owner.
```

Probe: on a 7702-active chain, sign an authorization from the owner EOA pointing at an
attacker implementation, then call the guarded function. If it passes, the guard is dead.

By-design calibration: `tx.origin == msg.sender` (reentrancy-style guard) is unaffected. Only
guards that *assume* `tx.origin` is a key-holder are broken.

### Primitive 4 — Executor / hook reentrancy into the account

Executors run `execute(to, value, data)` from the account. If the executor is a module and the
account's storage is written *before* the external call, a malicious `to` can re-enter.

```bash
rg -n "function execute" -A 15
rg -n "nonce\+\+|_nonce|executed\[" -B 2 -A 2   # is the replay guard before or after the call?
```

Check ordering: nonce increment must happen **before** `to.call{value}(data)`. After = replay.

---

## Phase 2 — Registry-level attacks

The registry is a single point of failure for every account using it.

| Attack | Probe | Impact |
|---|---|---|
| Registry add is role-gated weakly | Who is `registryAdmin`? EOA? Timelock? | Compromised admin = malicious module in every account |
| Module metadata spoofing | Can `moduleName`/`moduleAudit` be set by the module author? | Users install a "audited" module that isn't |
| Registry upgrade without notice | Is the registry itself a proxy? | Silent swap of the allowlist |
| Cross-account module persistence | Module installed on account A, account B delegates to A | Shared-state confusion |

---

## Phase 3 — Grep seeds

```
rg -n "installModule|uninstallModule" -A 12 | rg -n "delegatecall|\.call\("
rg -n "isModuleApproved|approvedModules|moduleAllowlist" -B 2 -A 2   # the FIX shape — look for absence
rg -n "function validateUserOp" -A 30 | rg -n "return 1|return 0"
rg -n "tx\.origin" -B 3 -A 3
rg -n "ecrecover" -B 4 -A 4 | rg -n "==|require"
rg -n "0xef0100" -B 2 -A 2      # 7702 delegation designator prefix in bytecode/calldata
rg -n "EXTCODEHASH|extcodesize" -B 2 -A 2
```

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `installModule` dengan address attacker dari akun terkontrol | Inti kelas — allowlist ada atau tidak |
| 2 | Validator: signature malleability + empty-signature path | ATO langsung kalau lolos |
| 3 | `tx.origin`/`ecrecover`/`extcodesize` census + 7702 live test | Sink 7702 tidak terlihat dari source saja |
| 4 | Executor nonce ordering (sebelum vs sesudah external call) | Replay kalau salah urutan |
| 5 | Registry mutability + admin posture (EOA/timelock/multisig) | Menentukan severity: satu admin lemah = chain |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret dan sudah dieksekusi, bukan "mungkin bisa": *"Akun 0xATTACKER memanggil
`installModule(0xEVIL_MODULE, ...)` pada akun milik korban dan berhasil — module terpasang
(terbukti dari event `ModuleInstalled`), lalu `execute()` meneruskan delegatecall ke kode saya."*
Bukan lolos gate: "validator sepertinya tidak mengecek signature", "registry bisa diubah admin".

**2. Apa yang hilang dari korban, dan berapa?**
Sebutkan aset + jumlah yang benar-benar berpindah di fork: *"Seluruh saldo ETH + 3 token ERC-20
di akun korban (total 12,4 ETH) berpindah ke penyerang dalam satu tx."*
Kalau module hanya bisa dipasang tapi tidak bisa mengeksekusi, atau hanya mengubah state yang
tidak menguasai dana → turunkan ke hardening note, jangan dipaksa jadi Critical.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <mainnet> --match-test test_exploit -vvvv` lulus dari nol
- [ ] Setup hanya: fork, dua akun (korban + penyerang), satu module attacker
- [ ] Tx penyerang adalah **satu** `execute`/`installModule` (bukan butuh 5 langkah manual)
- [ ] Attacker P&L positif setelah gas (hitung eksplisit, bukan "drain semua")

**Kalau butuh precondition yang tidak dimiliki penyerang nyata** (korban harus install module
jahat secara manual dulu, atau admin harus lebih dulu compromised) → itu **bukan** Critical;
tulis precondition-nya verbatim dan turunkan severity, atau buang.

## Eskalasi wajib

**Primitif:** module install tanpa allowlist → arbitrary delegatecall → drain akun.
**Rantai:** validator bypass → install module → drain. Atau: 7702 sink → bypass `tx.origin` guard →
panggil fungsi privileged.
**Eskalasi ke:** `hunt-rce` (kalau module bisa menjalankan kode arbitrer), `hunt-ato`,
`web3-audit` (kelas access control), `onchain-finding-verification` (gate sebelum lapor).

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes (cast = foundry) ─────────────────────────────────────────
export RPC=<ARCHIVE_RPC>; A=<ACCOUNT_ADDR>; ATTACKER=$(cast wallet address --private-key 0xA11CE)

# 1) who can install a module? read the guard
cast call $A 'isModuleInstalled(uint256,address,bytes)' 1 $ATTACKER 0x --rpc-url $RPC
cast call $A 'entryPoint()(address)' --rpc-url $RPC
# then attempt the install FROM the attacker key (forks only, or a local deploy):
cast send $A 'installModule(uint256,address,bytes)' 1 $EVIL_MODULE 0x \
  --private-key 0xA11CE --rpc-url $RPC --dry-run

# 2) storage-slot probing for the slot-0 takeover shape
for s in 0 1 2 3; do
  printf 'slot %s: ' $s; cast storage $A $s --rpc-url $RPC
done
# compare: does slot 0 hold `owner`, and is it an immutable address (no slot at all)?

# 3) validator / signature path
cast call $A 'isValidSignature(bytes32,bytes)(bytes4)' 0x$(printf '0%.0s' {1..64}) 0x --rpc-url $RPC

# 4) 7702 delegation check (EIP-7702 accounts)
cast code $A --rpc-url $RPC | head -c 60          # 0xef0100<address> = delegated

# 5) registry admin posture
cast call $REGISTRY 'owner()(address)' --rpc-url $RPC
cast call $REGISTRY 'getCodeHash(address)(bytes32)' $ATTACKER --rpc-url $RPC
```

**Report gate:** the lab proof is `forge test --match-path test/AAModularCalibration.t.sol`
(see *How to run this lab*). A `cast call` that shows a missing guard is a
**hypothesis**; the finding needs the install to succeed and the account to be
controlled.

---

## By-design calibration (jangan lapor sebagai temuan)

- Registry dengan allowlist ketat + timelock pada `addModule` = positive observation.
- `tx.origin == msg.sender` reentrancy guard = tidak terpengaruh 7702.
- Module yang cuma bisa `call` (bukan `delegatecall`) dan token approval sudah di-scope = risiko
  terbatas, turunkan severity.
- Session-key path yang benar-benar cek `sessionKey == registeredKey` = by design.
- 7702 delegation ke implementation yang **audited dan immutable** = fitur, bukan bug.

## 2026 sweep

- **EIP-7702 batch authorization (type 0x05)** — satu tx bisa mendelegasi banyak EOA. Cek apakah
  kontrak yang membaca `extcodesize`/`EXTCODEHASH` untuk deteksi EOA sekarang salah klasifikasi.
- **ERC-7579 module type 4 (signature validator) vs type 2 (executor)** — installer yang tidak
  enforce tipe = validator bisa di-install sebagai executor dan sebaliknya.
- **Registry upgrade tanpa notice** — module registry sebagai proxy; swap allowlist secara senyap.
- **Safe 7579 module** — Safe sebagai account dengan module 7579; `setModule` guard vs
  `execTransactionFromModule` guard berbeda.
- **Session key dengan `validUntil` di masa depan** — key yang sudah expired tapi masih diterima
  karena cek `block.timestamp` dilakukan di hook yang bisa di-skip.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Module install tanpa allowlist + delegatecall → drain akun; validator bypass → ATO; 7702 `tx.origin` sink → bypass guard. Kalibrasi: module yang hanya bisa `call` + approval ter-scope = turunkan severity; registry dengan allowlist + timelock = positive observation.


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 8/8 probes passed)

Diuji pada modular account rentan (`test/AAModularCalibration.t.sol`). Tiga koreksi besar
terhadap framing awal skill:

- **Primitive 1 lebih kuat dari yang ditulis.** Saya kira butuh module "berbahaya" dengan payload
  khusus. Ternyata **module APA PUN yang punya state variable pertama di slot 0 langsung
  mengambil alih akun** — `AttackerModule` biasa (cuma `address public victim`) sudah menimpa
  `owner` saat `onInstall` jalan via delegatecall. Tidak perlu payload purpose-built.
- **Nilai yang ditulis adalah `address(this)` = AKUN, bukan alamat module.** Jadi setelah install,
  `account.owner()` = alamat akun itu sendiri: akun "memiliki dirinya sendiri", owner asli hilang,
  dan setiap guard `msg.sender == owner` bisa dipenuhi dengan akun memanggil dirinya. Ini bentuk
  takeover yang lebih bersih daripada "module jadi owner".
- **Primitive 4 (nonce-after-call) TIDAK otomatis jadi replay.** Percobaan reentrant naif GAGAL:
  re-entrant `execute()` datang dengan `msg.sender` = callee, bukan owner, jadi guard menolak.
  Ordering bug-nya nyata dan terukur (nonce masih 0 **di dalam** call, jadi 1 setelah return),
  tapi eksploitasinya butuh jalur yang membawa `msg.sender` yang sama — entryPoint batching
  beberapa `execute()` dalam satu UserOp, atau multicall yang delegatecall balik. **Menulis
  "nonce-after-call = replay" tanpa menunjukkan jalur kedua itu = klaim yang bisa dipatahkan.**

**Trap harness yang wajib diingat:**
- `immutable` TIDAK menempati storage. Kalau kontrak punya `address immutable entryPoint`, maka
  slot 0 adalah state variable non-immutable pertama (`owner`), bukan entryPoint.
- Verifikasi layout dengan `vm.load(address(target), slot)`, JANGAN dengan `sload(slot)` di test
  (itu membaca storage test contract). Dump slot 0..5 dulu sebelum menulis assertion.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

# your probe (8 tests, ~21 ms)
forge test --match-path test/AAModularCalibration.t.sol -vvv

# single probe
forge test --match-test test_Probe1_UnrestrictedModuleInstall -vvvv
```

| | |
|---|---|
| file | `test/AAModularCalibration.t.sol` |
| suite | `AAModularCalibration` |
| probes | `test_Probe1_UnrestrictedModuleInstall` · `test_Probe1b_DelegatecallRunsInAccountContext` · `test_Probe2_EmptySignatureAccepted` · `test_Probe3_NonceIncrementedAfterCall` · `test_Probe3b_NaiveReentrantReplayIsBlocked` · `test_Probe4_RegistryAdminPosture` · `test_Probe5_ModuleTypeConfusion` |
| control | `test_Control_UninstallWorks` (must pass — proves the harness isn't always-on) |

Read the `-vvvv` trace when a probe **fails to fire**: that is the calibration signal (the
framing in this skill is wrong, not the target). A probe that fires while its control also
fires means the harness is broken — fix the harness before trusting any negative.

