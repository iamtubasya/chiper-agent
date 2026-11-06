# On-chain Decode & Probe False Positives — the "my own tool lied" taxonomy

> **CORE RULE: before reporting an on-chain anomaly, prove the anomaly is real and not an
> artifact of your own decode call.** Most "CRITICAL drain" / "escrow underfunded" / "claim
> path bricked" alarms are self-inflicted. Every item below was a real false positive
> reversed inside one session (Base mainnet reward-distributor audit, Sep 2026).

---

## 0. The #1 killer — simulating with the WRONG `from`

**Never run a capability probe with a `from` address that has no business being the caller.**

A `payoutRewards` probe run with `from=0x0` (not the role holder) returned
`AccessControl.MissingRole`. That "proved" the payout path was bricked. It proved nothing —
only that `0x0` lacks the role.

**The decisive test is a REPLAY, not a fabricated `from`:**

```
replay a HISTORICAL SUCCESSFUL tx at the current block:
  eth_call({ from: <original tx.sender>, to: <contract>, data: <original tx.input>, value: 0 })
```

| Outcome | Meaning |
|---|---|
| Reverts with a **later, deeper** error (e.g. `"Invalid proof"`, a business require) | The gate BEFORE it passed → **path is LIVE** |
| Reverts with the **access-control** error | Path genuinely blocked for that caller |
| Succeeds | Path currently live for that caller |

The *position of the revert in the call chain* is the whole signal. Read-only reads
(`balanceOf` etc.) don't enforce `msg.sender`, so they work with any `from` — do not let
that lull you into a bogus `from` for a state-changing signature. A fabricated `from` is
the most common way to invent a dead chain, and a dead chain is INFORMATIONAL, never HIGH.

---

## 1. Decode false positives — every one of these bit in a single session

| Alarm raised | Real cause | Correct handling |
|---|---|---|
| "Escrow underfunded by 1.9M tokens" | Summed **Ended/Cancelled** records (funds already refunded) against a live balance | Reconcile **Active-state records only** against contract balance |
| "Record status = Paused" | Enum label dict **shifted** | Assert the enum order from source; re-derive every label (`Active=0,Paused=1,Ended=2,Cancelled=3`) |
| "`getRoleMemberCount` reverts → can't enumerate roles" | Plain `AccessControl`, **not** `AccessControlEnumerable` | Stop enumerating; verify by direct `hasRole(role, candidate)` on candidate addresses |
| "`merkleRoots(0..9)` all zero → roots never set" | The id is an **ASCII string** (e.g. `"20260826USDT…"`), not a numeric index | Read the raw 32-byte topic from logs; never index by integer |
| "`RoleRevoked` ⇒ operator lost the role ⇒ payouts stopped" | **OZ topic order**: `RoleGranted(bytes32 indexed role, address indexed account, address indexed sender)` → `topics[1]=role`, `topics[2]=account`, `topics[3]=sender`. Swapping role/account inverts grant/revoke | Decode in spec order, then diff against a *later* event proving the path still works |
| "Amounts off by 1e6" | Decimals assumed | **Read `decimals()`** from the token contract |
| "Address X is an EOA holding a privileged role" | `eth_getCode` result mis-parsed in the probe | Re-check `code_len > 0`; a **contract** role-holder changes the whole narrative |
| "Outflow > inflow from a distributor" | Pagination bug — only page 1 fetched | Fix pagination *before* drawing any flow conclusion |
| "Funds went to a random address" | Destination not identified | `eth_getCode` + explorer label: it was a verified `CErc20Delegator` (yield deposit) → benign |

**Meta-rule:** an anomaly that supports your favourite hypothesis deserves *more* scrutiny,
not less. When a decode result is "shocking", the prior is that the decoder is wrong.

---

## 2. Pagination / windowing discipline

- A log scan that returns `created_block = None` and falls back to `latest-60000` is **not**
  evidence of "0 events" — it is evidence of a broken window. Print chunk errors; never let a
  silently-swallowed RPC error become "no activity found".
- Prefer a **paginated explorer log endpoint** (Blockscout v2
  `/api/v2/addresses/<addr>/logs` with `next_page_params`) over `eth_getLogs` chunk-spraying:
  whole history, no timeouts. Timestamp→block bounds (~2 s blocks on Base) bound the scan.
- The explorer's **`decoded` fields** are a cross-check for the fields you compute yourself.
  When your decode and the explorer's `decoded` disagree, assume you are wrong and find out why.

---

## 3. Staged verification order (run in order, stop at the first contradiction)

1. **Role truth** — `hasRole(role, candidate)` for every actor (admin, operator, contract, EOA);
   plus `getRoleAdmin(role)` and whether the admin can re-grant.
2. **Capability** — replay a historical successful call at the current block (§0). Never fabricate `from`.
3. **Actor identity** — `eth_getCode` for every privileged address (contract vs EOA; multisig vs single key).
4. **Magnitude** — the *real* at-risk amount, Active state only, correct decimals.
5. **Destination** — identify every outflow counterparty (verified contract? router? cToken? EOA?).

Only when all five agree do you have a finding. Contradiction between any two = decoder bug, not a vuln.

---

## 4. What the surviving findings actually look like (honest severity floor)

After the false positives above were removed, the residue was **Low/Medium trust-model**, not Critical:

- A reward **escrow** whose `payoutRewards(bytes32,uint256,address)` is gated by a role + budget
  cap but has **no per-recipient proof at the registry layer** → the registry delegates *all*
  validation to the distributor. Provable with a read-only capability probe. This is a
  **trust-assumption / defense-in-depth** item (Low/Medium), NOT an exploit — no attacker
  capability was demonstrated.
- A privileged role held by an **unverified deployed contract** (bytecode-only, not a proxy,
  larger than the verified predecessor) → transparency gap → **Low**.
- All privileged roles in **one EOA** (no multisig) → standard centralization note → **Info**
  unless the program scopes it.

**By-design gate:** check the vendor's own audit-report scope first. If the audit covered a
*different* product surface (e.g. a Compound fork while the finding sits in an un-audited
reward registry), then "already audited, by-design" does not apply — but neither does the
finding become Critical. A capability that requires already-privileged access is a trust-model
note, never a severity-inflated exploit.
