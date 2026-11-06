# Scanner triage on mature, audited DeFi — the FP catalogue + the mandatory audit diff

On a continuously-audited protocol (UMA has 14 OpenZeppelin reports + a continuous audit;
similar shape: Morpho, Aave, Uniswap) `slither` + `aderyn` will report **hundreds** of hits and
**near-zero** real bugs. That is the expected result, not a failure — but it is also not "done".
This file is how to turn that noise into a defensible ledger.

## Rule 0 — open the body of every hit and WRITE THE VERDICT DOWN

A tool's self-label is not a finding (`[critical]`/`H-1` labels are triage hints only). For each
value-flow-relevant hit: read the code, decide, and record `FP / INFO / candidate` + the one-line
reason. Highest-class noise categories and their usual verdicts:

| scanner class | usual verdict | what actually decides it |
|---|---|---|
| `abi.encodePacked` hash collision | **FP** | Are the packed parts self-delimiting or length-derivable? UMA `AncillaryData` appends UTF-8 with explicit prefixes; a collision needs adversary-chosen concatenation. Read the encoder before calling it. |
| "contract locks Ether (no withdraw)" | **FP** | Governor / cross-chain messengers hold ETH *on purpose* to pay for proposal execution. Check whether the ETH is spent via an internal call, not "withdrawn". |
| "deletion from a nested mapping" | **FP** | The real question is **can the key repeat?** UMA `VotingV2` `delete priceRequests[id]` leaves `voteInstances` (a mapping) intact — but it is keyed by `roundId`, rounds are monotonic, and deletion only fires after `rollCount` exceeds a threshold (many rounds). A re-created request votes in `getRoundIdToVoteOnRequest(currentRoundId+1)` → strictly later round → stale mapping never read. Storage bloat only. |
| `int128` / unsafe integer cast | **FP/INFO** | Compute the bound. A slash bounded by `uint128 stake × rate / 1e18` is ~1e24 wei, orders of magnitude below `int128` max (~1.7e38). Do the arithmetic; don't hand-wave. |
| reentrancy-eth (state after external call) | **FP** | Verify `nonReentrant()` is actually applied to *that function* AND an access-control `require` guards it (UMA `EmergencyProposer.executeEmergencyProposal` has both). |
| `unchecked-transfer` | **FP/INFO** | For a standard OZ `ERC20` (reverts on failure) ignoring the bool is benign. Only escalate if the token can *return false* without reverting. |
| `ecrecover` malleability | **FP (hardening)** | FP when a strictly-increasing nonce/timestamp makes replay impossible (`CoinbaseOracle`: `require(timestamp > latestTimestamp)`). Still recommend OZ `ECDSA.recover` (rejects high-s) as defence-in-depth. |
| weak randomness | **check the path** | If the flagged file is under `examples/`, it is not production — drop it. |
| `divide-before-multiply` in fee math | **INFO** | Documented rounding; only worth escalating if you can name an exploitable delta. |

Also worth a dedicated manual pass (scanners routinely miss these, and they are where real bugs hide
on an audited oracle): a **hash-committed "skinny" request** — confirm the commitment covers the WHOLE
struct (`keccak256(abi.encode(request))`) and not a hand-picked field list; and **cross-chain messengers**
— confirm the `target`/payload param is only reachable under `onlyFromCrossDomainAccount(parent)` style
bridge+source-account auth.

## Rule 1 — the MANDATORY audit-exclusion diff (scope gate, not optional)

Many self-hosted programs list **"any points listed in an audit report"** as OUT of scope (UMA's exact
wording). That makes the vendor's own audit PDFs the *scope gate*:

> Before writing up **any** candidate: download the audit reports the program lists, extract their
> findings, and confirm your candidate is not among them.

A candidate that already appears in an audit report is **not reportable** — say so and drop it. Skipping
this step risks submitting something the triager rejects in one line ("known, in the OZ report"), which
costs reputation and the bounty. Do the diff **before** severity work, not after.

## Rule 2 — a shallow tool's clean run is weak evidence

`mythril` "No issues were detected" on layered DeFi logic has already missed a real finding in a prior
engagement. Record it as a tool result with that caveat; never read it as proof of absence. Likewise, a
tool that **errored before analysing** (e.g. mythril `FileNotFoundError: ''` inside
`check_run_integer_module`, or a slither `FileNotFoundError: out/build-info/...`) is a **tooling
failure**, not a result — label the artifact as such in the directory README so a stale failure log is
never read as an analysis outcome.

## Rule 3 — the ledger's shape (negatives are deliverables)

One row per tool: `tool | scope | result | artifact path`. Explicitly include:

- **NOT RUN** rows (a ledger with no gaps is implausible on a real target).
- **BLOCKED / tooling-failure** rows, distinguished from "found nothing".
- **FP verdicts** with the reason, so they cannot be double-counted later.
- An explicit *static-only* warning when no dynamic analysis has landed yet.

Then say the honest thing out loud: on a mature audited protocol the expected outcome may be
**zero findings**, and padding the ledger with FPs dressed up as findings is worse than reporting clean.
