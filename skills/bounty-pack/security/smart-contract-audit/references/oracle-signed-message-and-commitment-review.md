# Auditing signed-message, oracle-attested, and commitment flows

Applies to any contract whose security rests on an off-chain signature or attestation:
pricing oracles, intent/bridge settlement, resolver payloads, deposit-address managers.
The bug in this class is almost never "the signature is forgeable" — EIP-712 + OZ
`SignatureChecker` is standard and correct. The bug is that **the signed payload does not
constrain what actually happens**, or **the enforcement lives somewhere you cannot see**.

Work the three questions below in order. Each one is a real defect shape found in the wild,
not a hypothetical.

---

## Q1 — Enumerate every field in the struct, then ask which are ENFORCED

Take the EIP-712 struct and list its fields. For each, find the line that *acts* on it.
A field that is hashed into the digest but never compared to anything is **decorative**: it
costs the signer nothing and constrains nobody.

Real case (`SignedPricingOracle`):

```solidity
struct SignedPrice {
  string  chainId;           // enforced: compared to the requested currency's chainId
  bytes   currency;          // enforced: compared to the requested currency
  uint256 usdPrice;          // the payload
  uint8   usdPriceDecimals;  // the payload
  uint8   currencyDecimals;  // the payload
  uint256 publishTime;       // >>> SIGNED INTO THE DIGEST, NEVER READ <<<
  uint256 expiration;        // enforced: block.timestamp > expiration -> revert
  bytes   signature;
}
```

`publishTime` appears in `SIGNED_PRICE_TYPEHASH`, in `_hashSignedPrice`, and in the returned
`Price` — and is compared to `block.timestamp` **nowhere**, on-chain or in the off-chain
validator. Combined with `expiration` being chosen by the signer, a price signed once with a
far-future `expiration` is authoritative indefinitely.

**The audit move.** For every signed field, grep for a read that constrains it:

```bash
grep -rn "publishTime" contracts/ packages/*/src/ | grep -vE "typehash|_hash|struct|///"
# zero hits outside the digest = the field is signed but not enforced
```

Report it as: *"`<field>` is bound into the digest but never validated, so `<consequence>`."*
That is a real finding with a precise, checkable claim — much stronger than "the oracle might
be manipulated".

**Do not overreach the other way.** A decorative field is often *low* severity on its own;
state the consequence you actually proved (no freshness bound) rather than the one you imagine
(drain). Pair it with the severity gate in the parent skill.

---

## Q2 — A `try/catch` fallback is caller-selectable, so the "preferred" path is not enforced

```solidity
function resolveUsdPrices(Currency[] calldata currencies, bytes calldata extraData)
    external returns (Price[] memory prices)
{
  try RELAY_PRICE_ORACLE.resolveUsdPrices(currencies) returns (Price[] memory relayPrices) {
    prices = relayPrices;                      // "preferred" path
  } catch {
    SignedPrice[] memory signed = abi.decode(extraData, (SignedPrice[]));
    ...                                        // fallback path
  }
}
```

`catch` swallows **every** revert, including ones the caller causes. The comment says the
oracle is *preferred*; the code makes it *optional*. Concretely:

1. Enumerate what makes the inner call revert. Here `RelayPriceOracle` reverts on
   `FeedRouteNotFound`, `PriceBatchTooLarge`, `ArrayLengthMismatch`, `InvalidProviderId`,
   `InvalidMaxFutureSeconds`, `InvalidPriceFeedAdapter` — an unsupported currency or an
   oversized batch is enough.
2. Ask whether the caller controls that input. If yes, the caller chooses the path.
3. Ask what the fallback path trusts. If it is signed by a party with an interest in the
   outcome (here: the solver whose own price it is), the "prefer on-chain" design is advice,
   not a control.

```bash
grep -nE "revert|require" <PreferredOracle>.sol     # how easy is it to force the fallback?
```

**Framing.** Do not claim the fallback is attacker-controlled if the signer is the caller —
that is a trust boundary, not a break. Claim what is true: *"the preference is unenforceable;
any caller can select the fallback by supplying input the oracle rejects."* Then let severity
follow from whether the fallback signer is adversarial to the user.

---

## Q3 — When the docstring delegates validation to "downstream consumers", map the consumer

The most interesting contract in this class is the one that does **less** than you expect.
`RelayDepositAddressManager.trigger()` is fully permissionless and validates almost nothing:

```solidity
mapping(bytes32 triggerHash => bytes32 orderId) public triggers;   // the ONLY state

function trigger(Input, DerivationFields, bytes32 orderId, uint256 nonce,
                 Currency[] currencies, bytes extraData) external {
  if (orderId == bytes32(0)) revert InvalidOrderId();
  if (keccak256(input.vmType) != keccak256(df.inputVmType)) revert InputVmTypeMismatch();

  Price[] memory prices = IPricingOracle(df.pricingOracle)      // >>> CALLER-CHOSEN ORACLE
      .resolveUsdPrices(currencies, extraData);

  bytes32 triggerHash = _hashTrigger(..., prices, extraData);
  if (triggers[triggerHash] != bytes32(0)) revert AlreadyTriggered(triggerHash);
  triggers[triggerHash] = orderId;                              // >>> no orderId uniqueness
  emit Triggered(orderId, triggerHash);
}
```

Absent guards, all worth naming: no `pricingOracle` allowlist, no check that the oracle
matches the solver, **no `orderId` uniqueness** (the docstring admits the caller-supplied
`nonce` lets "otherwise-identical triggers be recorded multiple times"), and no caller check.

Its own docstring is the tell: *"downstream consumers **can** verify which oracle was used."*
`can` is doing a lot of work. Recorded-but-not-enforced is the whole design.

**Do not stop at the contract. The finding lives or dies on the consumer.**

```bash
grep -rn "Triggered\b" packages/ --include=*.ts          # who listens?
grep -rn "resolveUsdPrices" contracts/                   # who calls the oracle?
grep -rn "ALLOWED_ORACLES\|allowlist\|threshold" <attestation dir>
```

In this engagement the consumer was **not in the repo**, and the off-chain layer *did* carry
real gates — an `ALLOWED_ORACLES` set plus an `ORACLE_SIGNATURE_THRESHOLD` that the oracle
signers must satisfy over the `triggerHash` (which itself binds the oracle, so the choice is
attestable). That downgrades the finding from "exploitable" to **hardening / defence-in-depth**.

Correct output in that situation:

> On-chain `trigger()` is permissionless with a caller-chosen oracle and no `orderId`
> uniqueness; the only boundary is an off-chain consumer I could not inspect. The attestation
> layer does enforce an oracle allowlist and a signature threshold over the trigger hash, which
> is why I am calling this a hardening gap rather than an exploitable one.

That is a *better* report than an inflated one, and it survives triage. Say what you verified,
name what you could not, and let the operator decide — do not silently promote it.

---

## Q3b — The mirror case: an un-committed piece that IS independently bound

Check the inverse too, so you can say it was evaluated rather than missed. `PoolResolverBase`
keeps draw authorizations **outside** the oracle-attested commitment on purpose:

```solidity
// commitment the oracle signs:
//   keccak256(abi.encodePacked(address(this), keccak256(executionData)))
// executionData = { legs[], calls[], salt }   <- authorizations are NOT in here
```

Read as a smell this looks wrong ("authorizations are attacker-substitutable"). It is sound
because the un-committed bytes are bound by three *other* things:

- the legs (`pool`, `account`, `tokenIn/Out`, `amount`) come from `executionData`, which **is**
  committed and oracle-signed, so the attacker cannot change what is drawn;
- the authorization itself must verify against the account's configured `authorizer` for that
  `(account, orderAddress)` — `authorizer == address(0)` reverts `NoAuthorizer`, so there is no
  empty-signature path;
- the pool caps the total per `(order, account, token)` via `perOrderCap` / `budget` / balance,
  so even a freely-chosen `legIndex` cannot exceed the account's own configuration.

Write this down as a checked-and-clear item in the tool-coverage ledger. "Evaluated the
out-of-commitment authorization and found it independently bound" is worth as much as a
finding — it is the difference between coverage and a list of things you looked at.

---

## Checklist

- [ ] Every field in the signed struct: which line *enforces* it? Decorative fields named.
- [ ] `try/catch` on a "preferred" source: what reverts it, does the caller control that input,
      and who signs the fallback?
- [ ] Permissionless entry points: is there a caller allowlist, an input allowlist, and
      **uniqueness on the business key** (order id), not just on the hash?
- [ ] Docstring delegating to "downstream consumers": locate the consumer. If it is not in the
      repo, say so and do not claim the exploit.
- [ ] Off-chain attestation layer: allowlist? signature threshold? what exactly is signed?
- [ ] Un-committed payload pieces: bound by something else, or genuinely free?
- [ ] Domain separator binds `chainId` + `address(this)` (OZ `EIP712` does; hand-rolled may not).
- [ ] `authorizer`/`signer == address(0)`: reverts, or does `ecrecover` fallback open a hole?

## Severity honesty for this class

On-chain-minimal contracts are common by design (record-keeping on-chain, policy off-chain).
That produces real findings that are **not** exploitable from the artifact you hold. Label them
`hardening` / *defence-in-depth* and state the missing consumer explicitly. Inflating one of
these to Critical after you have already written "I could not find the consumer" is the exact
overclaim the parent skill's severity gate exists to prevent.
