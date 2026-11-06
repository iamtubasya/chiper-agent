# On-chain privileged-role & deployment forensics (who can move the money, right now)

Trigger: any finding that says "role X can move/redirect funds", "admin can upgrade", or any severity
claim about privileged behaviour. The source tells you the **capability**; the chain tells you the
**holder**, and the holder (EOA vs multisig, hot key vs timelock) is usually what decides severity.
Case study: Vana Data Portability escrow (chainId 1480, 2026-10) — one `eth_call` turned a generic
"facilitator can redirect balances" into "a single EOA hot key can".

## 1. Turn role names into hashes locally

```python
from Crypto.Hash import keccak
k = lambda s: "0x" + (lambda h: (h.update(s.encode()), h.hexdigest())[1])(keccak.new(digest_bits=256))
FACILITATOR = k("FACILITATOR_ROLE")   # 0xREDACTED_********
DEFAULT_ADMIN = "0x" + "00"*32
```
Grep the source first (`bytes32 constant ([A-Z_]+ROLE) = keccak256("…")`) so you hash the *same* string
the contract uses; AccessControlUpgradeable's `DEFAULT_ADMIN_ROLE` is the zero hash.

## 2. Find the real grants — the creation window, not the whole chain

Event topics (constant, no need to derive):
- `RoleGranted(bytes32,address,address)` topic0 = `0xREDACTED_********`
- `RoleRevoked(bytes32,address,address)` topic0 = `0xREDACTED_********`

Most RPCs cap `eth_getLogs` at a 10,000-block span
(`{"code": -32614, "message": "eth_getLogs is limited to a 10,000 range"}`). Do **not** binary-search
history: the first admin grant happens inside `initialize()` at proxy creation, so:

```
GET /api/v2/addresses/{proxy}            → creation_transaction_hash
GET /api/v2/transactions/{that hash}     → block_number
eth_getLogs {address: proxy, topics:[GRANT], fromBlock: block-2, toBlock: block+9990}
```

⛔ **PITFALL — a nested topic array can return ZERO events with no error.** `topics: [[GRANT, REVOKE]]`
(OR across topic0) silently yielded `[]` on this node while `topics: [GRANT]` returned 6 events in the
same range. **Always issue one query per topic and treat an empty result as suspect until a
single-topic query agrees.** A silent zero here reads exactly like "no roles were ever granted" — the
most dangerous false negative in this workflow.

⛔ **PITFALL — Blockscout `/api/v2/addresses/{a}/logs` has no `topic0` filter**
(`Unexpected field: topic0`). Page it and filter client-side on `topics[0]`, and remember the same
endpoint returns `Invalid format. Expected ~r/^0x([A-Fa-f0-9]{40})$/` if a proxy address in your list
is subtly wrong — verify every address against the explorer before concluding "0 events".

A typical handover shows up as a clean story: deployer grants itself `DEFAULT_ADMIN_ROLE` only, the
operational role goes to a service key, then the deployer's admin is granted to the real admin contract
and **revoked from the deployer** (two adjacent blocks). Always re-check with hasRole — grants are not
current state.

## 3. Current state = `hasRole`, always

```
eth_call {to: proxy, data: 0x91d14854 + role(32B, no 0x) + account(32B, left-padded lowercase)} → 1/0
```
(`hasRole(bytes32,address)` selector `0x91d14854`.) Run it for every candidate you found in the logs
**and** for the deployer, so "the deployer has nothing left" is measured rather than inferred.

## 4. Classify the holder — this is the severity decision

```
eth_getCode   {account} → "0x" (len 2)  ⇒ EOA / single private key
                        → non-empty     ⇒ contract; probe it
```
For a contract, ask what it is before assuming "multisig = safe":
```
getThreshold() 0x04e9d5d5 · getOwners() 0xa0e67e2b · masterCopy() 0xa619486e · VERSION() 0xffa1ad74
```
A 171-byte proxy whose `masterCopy()` is `0x29fcb43b46531bca003ddc8fcb67ffe91900c762` is a **Gnosis Safe
proxy (v1.4.1 singleton)**; `getThreshold()`/`getOwners()` then give you the real control picture.
`getOwners()` returns an ABI-encoded `address[]`: skip the first two 32-byte words (offset, length)
before slicing owners, or you will print pseudo-addresses like `0x000…020` and `0x000…007`.

Contrast is the finding. Observed shape worth reporting verbatim:
- role that **moves funds** = EOA, `eth_getCode` 0 bytes, **2,168,967 transactions** (an operational hot
  key, and a publicly visible target) — one key compromise = all escrowed funds;
- role that **upgrades** `_authorizeUpgrade` = 3-of-7 Gnosis Safe — better protected than the money path.

Grep `_authorizeUpgrade` in the source: `onlyRole(DEFAULT_ADMIN_ROLE)` is the usual gate, so the admin
holder *is* the upgrade authority — say it explicitly instead of "the admin can upgrade".

## 5. Quantify the exposure (no exposure number = no severity)

```
eth_getBalance                       → native held by the contract
GET /api/v2/addresses/{c}/token-balances → ERC-20 holdings (symbol + value/10**decimals)
```
Quote the number you measured ("escrow holds 1.1 VANA + 239.12 USDC.e"), never "funds could be stolen".

## 6. Cross-chain / testnet parity (cheap, and it closes a scope question)

Same CREATE2 address on two chains can point at *different* implementations — read the EIP-1967 slots
directly instead of trusting an explorer:
- implementation: `0xREDACTED_********`
- admin: `0xREDACTED_********`
```
eth_getStorageAt {proxy, slot} → impl = last 20 bytes
eth_getCode {impl}             → compare mainnet vs testnet code
```
Diff them ignoring immutables (a compiled artifact zeroes `__self`, the chain holds the real address):
identical length + differences confined to the contract's own address slots ⇒ **the same build runs on
testnet**. (Same discipline as `deployed-vs-source` verification — code section, not length.)

⛔ **Verify an explorer's chain before believing it.** `api.moksha.<host>` returned mainnet data
(identical block hash at the same height, mainnet contract record) while the two chains are genuinely
distinct. Two RPCs settle it: `eth_chainId` (1480 vs 14800) + `eth_blockNumber`. Report explorer/host
confusion as an **observation to confirm**, never as a vulnerability.

## 7. Reporting shape for a role-based finding

1. capability (from source, with the function + modifier quoted)
2. holder (address, EOA/contract, contract identity if any) — `hasRole` proven, not inferred
3. contrast with the better-protected role
4. measured exposure (native + tokens)
5. what you did NOT do (never exercised the drain; never used the key) — keeps it a claim, not an act
