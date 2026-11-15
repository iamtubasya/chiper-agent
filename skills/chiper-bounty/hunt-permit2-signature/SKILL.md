---
name: hunt-permit2-signature
description: Hunt Permit2, ERC-3009, and signature-based approval bugs — cross-domain replay, nonce reuse, allowance not reset, witness-data smuggling, and the 7702 interaction that turns a "valid signature" into a drain. Use when a target integrates Permit2, uses signed approvals/permits, or accepts any EIP-712 authorisation.
metadata:
  hermes:
    tags: [web3, permit2, erc-3009, eip-712, signature-replay, approval, critical]
    related_skills: [web3-audit, hunt-jwt-crypto, hunt-signature-replay, onchain-finding-verification]
---

# Hunt — Permit2 / ERC-3009 / Signed Approvals

Every signed approval is a bearer instrument. The bugs are always one of: **the signature is
valid for more than the signer intended**, or **the approval is consumed more than once**.

## When to use

- Target imports `permit2` / `ISignatureTransfer` / `SignatureTransfer`.
- Target has `permit(`, `transferWithAuthorization(`, `receiveWithAuthorization(`.
- Target accepts any EIP-712 struct that authorises a value transfer.
- Target has "gasless approval", "meta-transaction", "relayer", "session key".

---

## Phase 0 — Read the domain separator FIRST

```bash
rg -n "PERMIT2_DOMAIN_SEPARATOR|DOMAIN_SEPARATOR|EIP712" -A 6
rg -n "chainId|verifyingContract|salt" -B 2 -A 2 | rg -n "domain"
```

A signature is only bound to what the domain separator binds it to. Missing fields:

| Missing field | Consequence |
|---|---|
| `chainId` | Replay on a fork / another chain with the same address |
| `verifyingContract` | Replay across every contract sharing the struct |
| `salt` / nonce namespace | Replay across deployments of the same contract |
| `token` address (in the signed struct) | Signer authorises token A, spender drains token B |

Probe: build the same signature, submit it to (a) the contract on a fork, (b) a second deployment
at a different address, (c) a different chain with the same address. Any acceptance = replay.

---

## Phase 1 — Permit2 specific

Permit2's model: `permit` grants an allowance, `transferFrom` consumes it. Bugs live in the gap.

### 1.1 Allowance not decremented / not expired

```solidity
// the invariant that must hold
require(allowedAmount >= amount, "insufficient");
allowedAmount -= amount;      // if this is missing or conditional -> double spend
```

Probe: permit 1000, transfer 1000, transfer 1000 again. Second must revert.

### 1.2 `permitWitnessTransfer` — witness data is not validated

`permitWitnessTransfer` lets the caller attach arbitrary witness bytes hashed into the signature.
If the contract hashes the witness into the digest but never *reads* it, a signature intended for
"transfer to Bob with witness=order#123" can be replayed with witness=anything.

```bash
rg -n "permitWitnessTransfer|witness" -A 10
rg -n "_hashTypedData|hashStruct" -B 2 -A 4
```

Probe: obtain a witness signature, resubmit with different witness bytes. If accepted, the
witness is decorative, not binding.

### 1.3 Nonce reuse across token/spender pairs

Permit2 nonces are scoped per (owner, token, spender) in the reference implementation. A fork
that scopes them per owner only allows cross-token replay.

Probe: permit nonce N for token A spender S, then use nonce N for token B spender S.

### 1.4 `invalidateNonces` / expiry bypass

If `sigDeadline` is checked but `nonce` invalidation is skipped on a partial path, a cancelled
permit stays live.

---

## Phase 2 — ERC-3009 `transferWithAuthorization`

```solidity
function transferWithAuthorization(
    address from, address to, uint256 value,
    bytes32 nonce, uint256 validAfter, uint256 validBefore, bytes calldata signature
)
```

| Bug | Probe |
|---|---|
| `authorizationState[from][nonce]` never set to true | Replay the same authorisation N times |
| `validAfter`/`validBefore` not checked | Use an expired authorisation |
| `from` not recovered from signature (trusted from calldata) | Authorise as anyone |
| Nonce not scoped to `from` | Cross-account nonce collision |
| Missing `chainId` in the EIP-712 type | Cross-chain replay |

Probe sequence: (1) execute once, (2) execute again with identical args → must revert
`authorizationAlreadyUsed`. (3) execute with `validBefore` in the past → must revert.

---

## Phase 3 — Generic EIP-712 signed approvals

For any custom signed struct:

1. **Enumerate every field** and ask "can the signer see this value before signing?" A hidden or
   defaulted field the UI never shows is a phishing primitive.
2. **Check `v`/`s` handling** — no low-s check = malleability, two valid signatures per message.
3. **Check signature length** — `sig.length == 0` treated as "valid" on a fallback path.
4. **Check ERC-1271** — if the signer is a contract, `isValidSignature` is called. A contract
   that returns the magic value unconditionally (or a 7702-delegated EOA pointing at one) makes
   every signature valid.
5. **Check the relayer path** — if a relayer submits the signed tx, can the relayer change `to`,
   `value`, or `data` after signing?

```bash
rg -n "isValidSignature|ERC1271|1271" -A 8
rg -n "0x1626ba7e" -B 2 -A 2     # the magic return value
rg -n "sig\.length == 0|sig\.length <" -B 2 -A 2
```

---

## Phase 4 — The 7702 amplifier

A 7702-delegated EOA pointing at a contract that returns `0x1626ba7e` from `isValidSignature`
for any data makes every EIP-712 signature "valid" from that address. Combined with any
"signer is a contract → trust isValidSignature" path, this is a full authorisation bypass.

Probe: delegate an EOA to a stub that always returns the magic value, then submit a signature
from that EOA for a struct it never signed.

---

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Domain separator field census (chainId / verifyingContract / salt / token) | Replay lintas chain & kontrak kalau ada yang hilang |
| 2 | Double-execution dengan nonce/args identik | Inti double-spend; harus revert |
| 3 | Witness resubmission dengan bytes berbeda | Witness tidak binding = signature bisa dipakai ulang |
| 4 | Expired authorisation (`validBefore` lampau) + empty signature path | Boundary + fallback path |
| 5 | ERC-1271 / 7702 stub: signer kontrak yang selalu balas magic value | Bypass otorisasi penuh kalau lolos |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis N/A.
N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

Sebelum menulis report untuk kelas ini, jawab ketiganya. Satu "tidak" = bukan temuan.

**1. Apa yang bisa dilakukan penyerang SEKARANG, on-chain?**
Harus konkret: *"Signature Permit2 milik korban untuk chain A bisa dipakai ulang di chain B karena
`chainId` tidak masuk domain separator, dan `permitTransferFrom` di chain B berhasil menarik 5.000
USDC korban."*
Bukan lolos gate: "nonce tidak pernah di-increment", "witness tidak di-hash".
Sebutkan fungsi + argumen yang dieksekusi penyerang.

**2. Apa yang hilang dari korban, dan berapa?**
Harus berupa **transfer aset yang terukur**: *"5.000 USDC berpindah dari korban ke penyerang."*
Kalau yang terbukti hanya "signature bisa dipakai dua kali tapi allowance-nya 0" → tidak ada
kerugian, jadi bukan temuan. Cek allowance/balance sebelum vs sesudah.

**3. Bisa direproduksi sebagai satu Foundry test di fork dalam 10 menit?**
- [ ] `forge test --fork-url <chain> --match-test test_exploit -vvvv` lulus
- [ ] Signature dibuat di dalam test dengan `vm.sign` memakai private key milik test (bukan
      signature asli dari prod)
- [ ] Double-execution / cross-chain replay dibuktikan dengan **dua** panggilan, dan yang kedua
      harus berhasil (kalau revert → kontrolnya bekerja, catat sebagai negatif)
- [ ] Delta saldo korban dihitung eksplisit

**Domain separator yang "kurang satu field" bukan bug dengan sendirinya** — buktikan bahwa
hilangnya field itu menghasilkan replay yang benar-benar mengeksekusi transfer.

## Eskalasi wajib

**Primitif:** signature valid untuk lebih dari yang dimaksud signer.
**Rantai:** cross-domain replay → drain token di kontrak kedua. Witness tidak binding → order
tampering. 1271/7702 stub → otorisasi penuh.
**Eskalasi ke:** `hunt-aa-modular` (7702), `web3-audit` (kelas signature replay),
`onchain-finding-verification` (gate).

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# ── on-chain probes ────────────────────────────────────────────────────────
export RPC=<RPC>; P2=<PERMIT2_ADDR>

# 1) domain separator — which fields are bound?
cast call $P2 'DOMAIN_SEPARATOR()(bytes32)' --rpc-url $RPC
cast call $P2 'nonceBitmap(address,uint248)(uint256)' $OWNER 0 --rpc-url $RPC

# 2) allowance + replay — read before, replay, read after
cast call $P2 'allowance(address,address,address)(uint160,uint48,uint48)' $OWNER $TOKEN $SPENDER --rpc-url $RPC
cast send $P2 'permitTransferFrom(((address,uint256),bytes),((address,uint256),bytes),address,uint256,bytes)' \
  "$PERMIT" "$TRANSFER" $OWNER $NONCE $SIG --private-key 0xA11CE --rpc-url $RPC
# then repeat the SAME call: a successful second execution = replay

# 3) witness binding — same signature, different witness
cast send $P2 'permitWitnessTransferFrom(((address,uint256),bytes),((address,uint256),bytes),address,bytes32,string,bytes)' \
  "$PERMIT" "$TRANSFER" $OWNER "$WITNESS_HASH" "Witness(address to)" $SIG \
  --private-key 0xA11CE --rpc-url $RPC --dry-run

# 4) expiry boundary
cast call $P2 'allowance(address,address,address)(uint160,uint48,uint48)' $OWNER $TOKEN $SPENDER --rpc-url $RPC
# expiration == block.timestamp: is it still valid at that exact second?

# 5) ERC-1271 / 7702 signer stub — does the checker accept a contract that always returns magic?
cast call $OWNER 'isValidSignature(bytes32,bytes)(bytes4)' $HASH $SIG --rpc-url $RPC
cast code $OWNER --rpc-url $RPC | head -c 40     # 0xef0100 = 7702 delegated
```

**Report gate:** lab proof = `test/Permit2Calibration.t.sol`. A **second successful
execution moving value** is the finding; a revert means the control works (record
as a verified negative).

---

## By-design calibration

- Permit2 reference implementation dengan nonce scoping benar = the fix, not a bug.
- `sigDeadline` yang sudah dicek + nonce yang di-invalidate = kontrol bekerja.
- ERC-1271 pada smart contract wallet yang benar-benar memvalidasi = by design.
- Expiry window yang wajar (jam, bukan detik) = desain, bukan celah.

## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Kondisi | Severity |
|---|---|
| Signature valid lintas domain/chain (chainId atau verifyingContract hilang) | Critical |
| Double-spend via nonce tidak di-consume | Critical |
| Witness tidak binding → order tampering | Critical |
| ERC-1271/7702 stub yang selalu balas magic value → otorisasi palsu | Critical |
| Malleability (dua signature valid per pesan) | High |
| `sigDeadline` tidak dicek | Medium-High |

**Kalibrasi wajib:** signature yang bisa di-replay adalah primitif; severity ditentukan oleh apa
yang bisa ditandatangani penyerang (transfer token? ubah izin? settle order?).

## 2026 sweep

- **Permit2 `PermitBatch` partial revert** — satu permit gagal, batch tidak atomic; cek apakah
  kontrak pemanggil menganggap batch sukses separuh.
- **ERC-3009 + 7702** — `transferWithAuthorization` dari EOA yang di-delegasi; `from` yang
  di-recover bisa jadi kontrak, bukan EOA.
- **Witness typehash collision** — dua struct berbeda dengan field yang sama urutannya; typehash
  identik = signature bisa dipakai lintas tipe.
- **`nonceBitmap` overflow** — Permit2 nonce sebagai bitmap word+bit; bit index melebihi 256.
- **Relayer front-running signed permit** — permit di-mempool, relayer lain pakai dulu; cek
  apakah ada mekanisme anti-front-run (mis. `sigDeadline` ketat + spesifik relayer).


## Lab calibration (2026-10-27 — `D:/isplab/web3-lab`, 7/7 probes passed)

Diuji pada Permit2-shaped system (`test/Permit2Calibration.t.sol`). Yang terkonfirmasi:

- **Probe 1 (no domain binding) adalah probe termurah dan paling menentukan.** Digest yang tidak
  memuat `chainId` maupun `verifyingContract` menghasilkan hash **identik** di dua deployment
  berbeda, dan signature-nya diterima di deployment kedua. Cara mengujinya tanpa asumsi: deploy
  kontrak dua kali, bandingkan `digestOf(struct)` — kalau sama, signature bisa di-replay. Kontrak
  yang aman menghasilkan digest berbeda karena `address(this)` masuk domain separator.
- **Probe 2 (allowance tidak di-decrement) = double spend literal.** Permit 1000e18 → `transferFrom`
  1000e18 dua kali → spender dapat 2000e18. Bukan teori: saldo terukur. Kontrak aman revert
  `insufficient allowance` pada spend kedua.
- **Probe 3 (witness tidak binding) berhasil dengan witness yang benar-benar berbeda.** Owner
  menandatangani `witness = keccak256("order-123-to-Bob")`, penyerang submit dengan
  `keccak256("order-999-to-Attacker")` — diterima. Witness ada di digest tapi tidak pernah
  dibandingkan, jadi murni dekoratif.
- **Probe 4 (ERC-3009 replay) — state tidak pernah di-set.** Authorisation yang sama dieksekusi
  dua kali, attacker dapat 200e18 dari satu authorisation 100e18.
- **Probe 5 (malleability) terbukti dengan twin `(v^1, n-s)`.** Kedua signature recover ke owner.
  Kontrak aman menolak dengan `malleable sig` (low-s check).

**Catatan implementasi:** `transferWithAuthorization` butuh parameter `token` eksplisit kalau
kontraknya bukan token itu sendiri — kalau tidak, `.call()` dipanggil pada `bytes32` dan tidak
compile. Ini juga pengingat: baca signature fungsi aslinya, jangan asumsikan.

#### How to run this lab

```bash
export PATH="$HOME/.foundry/bin:$PATH"
cd D:/isplab/web3-lab

forge test --match-path test/Permit2Calibration.t.sol -vvv
forge test --match-test test_Probe4_Erc3009Replay -vvvv
```

| | |
|---|---|
| file | `test/Permit2Calibration.t.sol` |
| suite | `Permit2Calibration` |
| probes | `test_Probe1_NoDomainBinding` · `test_Probe2_AllowanceNotDecremented` · `test_Probe3_WitnessNotBinding` · `test_Probe4_Erc3009Replay` · `test_Probe4b_ExpiredAuthorisationRejected` · `test_Probe5_NoLowSCheck` |
| control | `test_Probe2b_Control_SafeDecrements` |

`test_Probe4b_ExpiredAuthorisationRejected` is a **negative** probe that should pass on a
correct implementation — it calibrates that your harness can tell a working control from a
broken one.

