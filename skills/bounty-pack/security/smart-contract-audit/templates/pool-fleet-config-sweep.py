"""Fleet sweep: find every deployed instance of a protocol and check where a finding is REACHABLE.

Use when a defect is config-gated (reward on/off, limit set, flag true) and the in-scope instance has
it disabled. Permissionless-factory protocols deploy many instances with independent config; Immunefi's
Primacy of Impact covers in-scope impacts on unlisted assets, so enumerate the fleet before concluding
"no impact".

Verified working 2026-10 against DeXe Protocol on BSC (228 GovPools found; 21 had the vulnerable path
live). Deliberately uses raw JSON-RPC + manual ABI word decoding instead of `cast call`, because
`cast` mis-orders structs whose last member is dynamic (it reported duration = 0 on a struct the
contract forbids from being 0).

HOW TO ADAPT
  1. RPC           -> your chain
  2. ENUMERATOR    -> however the protocol lists instances:
                        registry: countPools(string) + listPools(string,uint256,uint256)
                        factory : DaoPoolDeployed-style logs via eth_getLogs
                        subgraph: GraphQL
  3. probe(pool)   -> resolve the instance's config contract and pull the fields the finding needs.
                      Replace the `settings(uint256)` read below with whatever getter you need, and
                      keep the offset self-check.

Requires: eth-hash  (pip install eth-hash[pycryptodome])
"""
import json
import urllib.request

from eth_hash.auto import keccak

# ---------------------------------------------------------------- adapt these
RPC = "https://bsc-dataseed.binance.org/"
REGISTRY = "0x0000000000000000000000000000000000000000"   # enumerator contract
POOL_KIND = "GOV_POOL"                                    # registry name for the instance class
ZERO_ADDR = "0x" + "0" * 40
# ---------------------------------------------------------------------------


def sel(sig):
    return "0x" + keccak(sig.encode()).hex()[:8]


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as fh:
        return json.load(fh)


def call(to, data):
    d = rpc("eth_call", [{"to": to, "data": data}, "latest"])
    if "error" in d:
        raise RuntimeError(d["error"])
    return d["result"]


def words(h):
    x = h[2:]
    return [x[i:i + 64] for i in range(0, len(x), 64)]


def enc_str(s):
    b = s.encode()
    return ((32).to_bytes(32, "big").hex()
            + len(b).to_bytes(32, "big").hex()
            + b.hex().ljust((len(b) + 31) // 32 * 64, "0"))


def enc_u256(v):
    return v.to_bytes(32, "big").hex()


def address_of(word):
    """Last 20 bytes of a 32-byte word, as a 0x address."""
    return "0x" + word[24:]


def balance_of(token, holder):
    return int(call(token, sel("balanceOf(address)") + enc_u256(int(holder, 16))), 16)


def list_instances():
    n = int(call(REGISTRY, sel("countPools(string)") + enc_str(POOL_KIND)), 16)
    raw = call(REGISTRY, sel("listPools(string,uint256,uint256)")
               + enc_str(POOL_KIND) + enc_u256(0) + enc_u256(n))
    w = words(raw)
    off = int(w[0], 16) // 32                      # offset to the dynamic address[]
    return [address_of(w[off + 1 + i]) for i in range(int(w[off], 16))]


def probe(pool):
    """Return (reachable, at_risk_balance, detail). EDIT the body per target.

    The DeXe shape below: pool -> getHelperContracts()[0] = settings -> executorToSettings(pool)
    -> settings(id). Struct layout of GovSettings.ProposalSettings (repo-authoritative):
        w0 earlyCompletion | w1 delegatedVotingAllowed | w2 validatorsVote
        w3 duration | w4 durationValidators | w5 executionDelay
        w6 quorum | w7 quorumValidators | w8 minVotesForVoting | w9 minVotesForCreating
        w10 rewardToken | w11 creationReward | w12 executionReward | w13 voteRewardsCoefficient
        w14 offset to executorDescription (string)
    """
    hc = words(call(pool, sel("getHelperContracts()")))
    settings = address_of(hc[0])
    stid = int(call(settings, sel("executorToSettings(address)") + enc_u256(int(pool, 16))), 16)
    raw = words(call(settings, sel("settings(uint256)") + enc_u256(stid)))

    # SELF-CHECK: head is N words, so the dynamic member's offset word must read exactly N*32.
    # 15 words here. If this fails your field count is wrong -> fix the mapping, do not trust the rest.
    if int(raw[14], 16) != 15 * 32:
        return (None, 0, "LAYOUT MISMATCH - mapping wrong, skipping")

    validators_vote = int(raw[2], 16) != 0
    reward_token = address_of(raw[10])
    execution_reward = int(raw[12], 16)

    # REACHABILITY = every precondition of the finding is true on this instance.
    reachable = validators_vote and execution_reward > 0 and reward_token != ZERO_ADDR
    at_risk = balance_of(reward_token, pool) if reachable else 0
    detail = (f"validatorsVote={validators_vote} rewardToken={reward_token} "
              f"executionReward={execution_reward} poolBalance={at_risk}")
    return (reachable, at_risk, detail)


def main():
    pools = list_instances()
    print(f"{POOL_KIND} instances: {len(pools)}\n")
    shortlist = []
    for p in pools:
        try:
            reachable, at_risk, detail = probe(p)
        except Exception as exc:  # noqa: BLE001
            print(f"{p}  ERROR {exc}")
            continue
        if reachable is None:
            print(f"{p}  {detail}")
        elif reachable:
            print(f"{p}  REACHABLE  {detail}")
            shortlist.append((at_risk, p, detail))

    print("\n=== SHORTLIST (finding reachable), ranked by at-risk balance ===")
    for at_risk, p, detail in sorted(shortlist, reverse=True):
        print(f"  {p}  atRisk={at_risk}  {detail}")
    if not shortlist:
        print("  (none) -> the defect is dormant across the whole fleet; state that explicitly")


if __name__ == "__main__":
    main()
