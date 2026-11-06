# Cross-chain deployment parity + privileged-role forensics

Two on-chain checks that turn "the source looked fine" into a defensible statement about what is
actually deployed and who can move what. Both were run on the Vana Data Portability contracts
(chainId 1480 mainnet, 14800 Moksha; 2026-10) with nothing but public RPC + an explorer API.

## 1. Cross-chain parity: is the testnet running the code you audited?

Deployments are usually CREATE2-deterministic, so **the same proxy address appears on both chains
while the implementation address differs** (different CREATE2 salt/order). That is expected — do not
call it a finding. What matters is whether the *bytecode* matches.

```
# proxy on both chains at the same address, implementation differs
eth_getStorageAt <proxy> 0xREDACTED_********  # EIP-1967 impl slot
  mainnet -> 0x0DE07F128B3a127Cae1AD6E8d44f2F6A6C3A9611   (11355 bytes)
  moksha  -> 0xe442e154c96a90e819865b7586fb457da4692d00   (11355 bytes)
eth_getCode <impl> latest      # eth_getCode on the WRONG chain returns 0x - check before concluding
```

Diff the two `eth_getCode` results. When the build is identical the diff collapses to the immutable
`__self` address (20 bytes x2 for a UUPS implementation) plus nothing else — same length, tiny diff
set. Report it as: *"the testnet runs a byte-identical build apart from the immutable self-address"*.
If the diff is larger, you have either different compiler settings (check `viaIR`, `bytecodeHash`,
optimizer runs — see the main SKILL.md) or genuinely different code; do not guess which.

**Explorer-env confusion is a trap, not a finding.** `api.moksha.vanascan.io` returned *mainnet* data
for the escrow (same address, same creation tx, same balance). Confirm before writing anything:

```
GET <explorer-A>/api/v2/blocks/<height>   -> hash
GET <explorer-B>/api/v2/blocks/<height>   -> hash
# identical hashes on two different chainIds == the "testnet" API host is serving mainnet data
```
Verify chain identity with `eth_chainId` on each RPC (1480 vs 14800 here). The honest write-up is an
*observation to confirm with the vendor* ("this host appears to serve mainnet/mixed data"), never a
vulnerability claim — you cannot tell an alias from a misconfig from outside.

## 2. Privileged-role forensics: who can move funds, who can upgrade

Finding the code path ("FACILITATOR_ROLE can redirect any balance") is half a finding. The impact
half is *who holds that role* and *is that key protected*. Recipe, all public calls:

```
# role hashes (keccak256 of the role string; pycryptodome: Crypto.Hash.keccak, or eth_hash)
FACILITATOR_ROLE        = eth_call hasRole selector 0x91d14854 + role32 + addr32
DEFAULT_ADMIN_ROLE      = 0x00..00
ACCESS_RECORDER_ROLE / MAINTAINER_ROLE / PERMISSION_MANAGER_ROLE -> hash them from the source strings

# history: RoleGranted/RoleRevoked in the proxy's creation window
RoleGranted(bytes32,address,address)  topic0 0xREDACTED_********
RoleRevoked(bytes32,address,address)  topic0 0xREDACTED_********
```

**Three practical gotchas, each of which cost a round of debugging:**

1. **`eth_getLogs` on these RPCs is capped at a 10,000-block range** ("eth_getLogs is limited to a 10,000
   range"). Do NOT scan from 0x0. Instead: read the proxy's `creation_transaction_hash` from the explorer
   (`/api/v2/addresses/<a>`), resolve its block (`/api/v2/transactions/<hash>`), then query
   `[creation-2, creation+9990]` — the initial grants and the handover all happen there.
2. **A nested topic array returns empty, not an error.** `"topics":[[GRANT,REVOKE]]` yielded `[]` on all
   six proxies and looked like "no role events exist". Send **one topic per query** (`"topics":[GRANT]`,
   then `"topics":[REVOKE]`) and merge — that immediately returned the real grant/revoke history.
3. **Explorer log pages beat block-scanning for recent activity**, but their `next_page_params` paging can
   walk past old blocks; the RPC creation-window query is what surfaces constructor/first-tx grants.

Then answer "what is that address?":

```
eth_getCode <holder> latest        # 0x == EOA (a single private key); non-empty == contract
eth_getBalance <holder> latest     # a hot key usually holds gas money
# if it is a contract, probe the multisig surface:
getThreshold()  0xe75235b8   getOwners() 0xa0e67e2b   masterCopy() 0xa619486e
# masterCopy 0x29fcb43b46531bca003ddc8fcb67ffe91900c762 == Gnosis Safe v1.4.1 singleton
# explorer /counters gives transactions_count -> tells you how long-lived/hot the key is
```

Real result that made the report land: escrow `FACILITATOR_ROLE` = an **EOA with 2.17M transactions**
(no contract code) while `DEFAULT_ADMIN_ROLE` (= `_authorizeUpgrade`) = a **3-of-7 Gnosis Safe**; the
deployer EOA had granted itself both roles at creation and was later fully revoked. Write that contrast
explicitly — *the weakest privileged role is the money path while the strongest guards upgrades* — and
quantify exposure from the chain (native balance + `eth_getTokenBalances` from the explorer), not from
the docs. If a new holder appears after your report was sent, that is addendum material, not a new
finding: one short follow-up email, same subject family, with the verification commands inlined.

**Also worth capturing:** the escrow proxy's `creator_address_hash` was
`0x4e59b44847b379578588920cA78FbF26c0B4956C` (Arachnid's CREATE2 deployer) — deterministic-address
deployments mean the same address on every chain, which is exactly why the cross-chain check above
needs to compare *implementations*, not proxies.

## Reporting rules that fall out of this

- "Who holds role X" is a fact you can verify with two RPC calls; state the block/height and the call
  you made, so the vendor can re-check after a rotation.
- A single-EOA privileged role is a *custody* statement, not a compromise. Say "a single key controls
  this", never "this key is compromised".
- If the docs claim an invariant the role can break, that mismatch is the finding; the role-holder data
  is the severity argument (and it is what upgrades a Low "doc mismatch" toward Medium in practice).
