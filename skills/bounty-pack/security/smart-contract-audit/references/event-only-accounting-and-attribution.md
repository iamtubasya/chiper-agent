# Event-only accounting: when the contract keeps no record, ATTRIBUTION is the attack surface

A reusable class found live on Relay's `RelayDepository`
(`0x4cD00E387622C35bDDB9b4c962C136462338BC31`, Base, ~9 ETH held) on 2026-10-08.

## The pattern

The contract's only record of a deposit is an **event**, with the credited party taken from a
**caller-supplied parameter**:

```solidity
// no per-depositor state anywhere in the contract
function depositNative(address depositor, bytes32 id) external payable {
    address who = depositor == address(0) ? msg.sender : depositor;
    emit RelayNativeDeposit(who, msg.value, id);     // funds stay in the contract
}

function depositErc20(address depositor, address token, uint256 amount, bytes32 id) public {
    token.safeTransferFrom(msg.sender, address(this), amount);   // paid by msg.sender
    emit RelayErc20Deposit(who, token, amount, id);              // credited to `depositor`
}
```

Note the split: **the funds come from `msg.sender`, the attribution comes from a parameter.**
Nothing binds them.

## Why it is a finding, not a nitpick

The contract exposes no `balanceOf(depositor)`, no accounting mapping, no withdraw. Its entire
output is the event. Therefore **the backend must reconcile deposits from those events alone** —
there is nothing else to read. That makes event fields an unauthenticated input to the credit
decision:

- `depositor` is arbitrary ⇒ a deposit can be **attributed to any address**.
- `id` is arbitrary and unvalidated ⇒ an attacker can **choose** the id, including one that
  collides with a genuine pending deposit.
- If `id` is deterministic (derived from the user's intent) it is computable from the mempool ⇒
  the attack is a **front-run**: emit a colliding id first, and the genuine deposit is masked.

The overload that reads `allowance(msg.sender, this)` makes it **free**: with no approval the
amount is `0`, the transfer of 0 succeeds, and the event still fires.

## Proof shape (proved on the live contract via Base fork)

```
[PASS] test_zeroCostErc20EventSpoof              // no balance, no approval -> event still emitted
[PASS] test_arbitraryDepositorAndIdOnNativeDeposit   // victim named, chosen id, 1 wei
```

Minimal probe: a contract with 0 token balance and 0 allowance calls
`depositErc20(<victim>, token, <chosen id>)` and asserts the call did **not** revert. Assert on
the observable (did it revert / did the event fire), never on intent.

## How to detect it on any target

```
grep -n "emit " <Contract>.sol | grep -iE "deposit|credit|receiv|fund"
grep -nE "mapping.*=>.*(uint|Balance)" <Contract>.sol    # is there ANY accounting state?
```

Ask: **if I only had this contract's events, could I tell who owns what?** If yes, and any field in
that event is caller-supplied, attribution is forgeable.

## Honesty boundary — state it, do not skip it

Impact depends on the backend, which you cannot see. Say exactly that:

> The forgeability is proven on-chain. Whether it becomes fund loss or a stuck deposit depends on
> how the backend keys reconciliation (by `id`? by `depositor`?) — unverified.

Do **not** upgrade "attribution is forgeable" to "funds are stealable" without the backend spec.
Do **not** dismiss it because you cannot see the backend either — forgeable attribution on a
contract holding funds is reportable on its own.

## Adjacent checks that pay off in the same pass

Same contract, same session, worth a look whenever you are here:

- **No `withdraw`/`rescue` at all** ⇒ if the trusted signer key is lost, funds are locked forever.
  Design risk, not an exploit — but worth a line in the report.
- **Permissionless `execute` + arbitrary `calls`** ⇒ verify the EIP-712 binding: the domain must
  include `chainId` **and** `address(this)`, and the struct hash must bind *every* field. Solady's
  `_hashTypedData` does both; confirm rather than assume, and confirm the replay guard is written
  **before** the external calls.
- **Hardcoded gas stipend in a send helper** (`call(100000, to, value, ...)`) ⇒ if the recipient's
  `receive` needs more, every deposit reverts. Test with a gas-hungry receiver.

## Where the money actually is — the repo is not the system

The contract holding the funds was **not in the protocol's repo**. It was found by taking the
deposit address out of a live API response:

```bash
curl -s -X POST https://api.<protocol>/quote -H 'Content-Type: application/json' -d '{...}' \
 | grep -oE '0x[a-fA-F0-9]{40}' | sort -u
```

then pulling its verified source from Sourcify and reading it. Treat `addresses.json` and the repo
as an index of *candidates*; the **live API tells you what is actually in use**. On this target the
two disagreed, and the repo did not contain the money contract at all.
