# Intent / Order-Derived Deposit Wallets — Review Discipline

For protocols that derive a **per-order deposit address** from a master key held off-chain
(TEE / MPC / KMS), by hashing the order's fields into a derivation path. Relay's
`lit-deposit-address` package is a worked example.

The failure mode this file prevents: seeing caller-supplied fields in the derivation input and
filing "attacker can force a collision and steal deposits" **without** checking whether a
collision is reachable. On 2026-10-08 that hypothesis was wrong twice over and the honest answer
was "not a finding" — worth writing down so it is not re-investigated next time.

---

## 1. The shape

```typescript
// fields hashed into the child-key path; every one is caller-supplied in the request
{ inputVmType, outputVmType, outputChainId, outputCurrency, outputRecipient,
  solver, pricingOracle, depositor, refundRecipient, priceImpactBps, salt }

const encoded = encodeAbiParameters(DERIVATION_FIELDS_ABI, [fields]);
const hex = keccak256(encoded).slice(2);
const indexes = Array.from({ length: 8 }, (_, i) =>
  Number.parseInt(hex.slice(i * 8, i * 8 + 8), 16) & 0x7fff_ffff);   // 8 x uint31
// -> derive 8 NON-HARDENED child segments from an account-level xpub -> the deposit address
```

Two properties stand out and both are **by design**:

- **`& 0x7fffffff` forces every segment non-hardened** (BIP32 hardened = index ≥ 2³¹). That is what
  lets anyone holding the xpub recompute the address locally, which the package documents
  (`local-derivation.ts` mirrors the in-TEE logic so callers can verify without TEE access).
- **All 256 bits of the hash are consumed** (8 × 32 bits, minus 1 bit each to the mask → **248
  bits of index entropy**), so path collisions are not reachable by search.

## 2. The two questions that decide it

Ask them in this order. Either one alone closes the hypothesis.

### Q1 — Is the field that would let you collide actually free?

For a collision you need **all 11 fields identical** to the victim's. Two of Relay's are
unbound by the order (`depositor`, `salt`) — which *looks* like the opening. But:

> **A caller-supplied field that changes the derivation is not a finding — it is the attacker
> getting their OWN address.**

Changing `depositor` or `salt` yields a different path, i.e. a wallet the attacker already
controls the derivation for. To reach the *victim's* wallet you must match their `salt`.

### Q2 — Is the salt / entropy guessable?

Relay's is `salt: bytesToBigInt(randomBytes(32))` — **256 random bits, per trigger**. Grinding a
collision is a 2²⁴⁸ search. **Check the salt's provenance before anything else**; if it is a
counter, a timestamp, a block number, a user id, or absent, the collision becomes reachable and
the finding becomes real. That single line decides the severity.

**Grep for it:** `grep -rnE "salt\s*[:=]" src/` and read where the value comes from. A random
`bytes32` is the fix; anything monotonic is the bug.

## 3. What the protocol usually does right, and why it matters

Relay's `verifyOrderData` binds most of the seemingly-free fields to the signed order, and the
docstring says so explicitly (*"so a malicious caller can't substitute a different order with the
same derivation fields"*). The checks worth confirming on any similar protocol, because their
**absence** is where the real bug lives:

| Check | What breaks without it |
|---|---|
| `getOrderId(order)` recomputed == `trigger.orderId` | caller swaps in an unrelated order with the same id |
| order signature (EIP-191 / EIP-712) recovers to `order.solver` | anyone can author the order they are deriving against |
| `derivationFields.solver` == virtual address derived from `(order.solverChainId, order.solver)` | **the solver field is the one derivation input that must be bound** — bind it or a caller picks whose path they land on |
| every refund entry validated (not just `refunds[0]`) | a solver-listed extra refund routes the money elsewhere while still passing signer checks |
| output chainId / currency / recipient match the derivation fields | derivation and settlement disagree about where funds go |
| price lookups exist, are unexpired, and the USD comparison is cross-multiplied with full precision | price-impact check can be made vacuously true by choosing scales |

If the protocol **has** these, the derivation is sound and the honest output is a negative. Say so
in one line and move on — do not dress a well-built design up as a finding to have something to
report.

## 4. Separating the derivation question from the accounting question

These are two different findings and they must not be merged:

- **Derivation** (this file): can an attacker land on a wallet whose key the TEE derives for
  someone else? Requires a collision → usually blocked by the salt.
- **Accounting** (see `event-only-accounting-and-attribution.md`): when the deposit contract keeps
  no balance mapping and its only output is an event carrying a caller-supplied `depositor` and
  `id`, attribution is forgeable at zero cost — **proven independently, on-chain, in seconds.**

The second is real and provable; the first usually is not. Do not let a weak derivation hypothesis
drag down a strong accounting finding, and do not let the accounting finding inflate the derivation
one. Report them as what each is.

## 5. Compensating controls to check before assigning severity

- **Does the allocator signature cover the withdrawal target?** If the allocator signs
  `(transferSpecHash, calls, nonce, expiration)` and the contract verifies the attestation hashes
  to that spec, then even a colliding deposit wallet cannot be drained to an attacker — the
  *destination* is signed. Relay's `RelayGatewayDepository` does exactly this, including a
  post-mint check that Circle marked the spec used.
- **Replay ordering:** the used-marker must be written **before** the external call
  (`callRequests[structHash] = true` then `gatewayMint(...)`), or a reentrant path reuses it.
- **Is there a rescue path?** A depository with `execute()` but no `withdraw`/`rescue` means a lost
  allocator key strands funds permanently. That is a design risk to *note*, not an exploit to file.

## 6. Effort budget

The temptation is to spend hours proving a collision is impossible. It is not: read the salt's
provenance (one grep), confirm the order-binding checks exist (one read of the verify function),
then write down whichever answer you got. If the salt is random, stop — there is nothing further
to test on the derivation path, and the remaining budget belongs to the accounting and
signature-binding surfaces.
