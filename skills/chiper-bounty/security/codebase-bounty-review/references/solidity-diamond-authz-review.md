# Solidity diamond ACL + service monorepo review

Worked case: **LIT-Protocol/chipotle** (commit `af5f682`, 2026-10-22). Repo-only bounty: in scope were
`lit-api-server` (Rust/Rocket), `lit-actions` (Deno sandbox), `lit-static` (dapps + SDK), the
`AccountConfig` diamond (Solidity 0.8.28, EIP-2535) and the TEE attestation/governance flow.
Program paid only Medium+ with a mandatory PoC; OOS included insider/governance-signer preconditions,
the Intel TDX/dstack/Phala platform, third-party CVEs, **all DoS**, and the usual hygiene list.

## 1. The four files that ARE the model

For any EIP-2535 diamond the authorization story lives in exactly four places — read them before
anything else, in this order:

| File | What it gives you |
|---|---|
| `AppStorage.sol` | the namespaced storage struct = the complete data model + every custom error. Note **which mappings share a namespace**. |
| `SecurityLib.sol` | every guard (`revertIfNotMasterAccount`, `revertIfNoAccountAccess`, `canAccount*`, `adminWriteAccountHash`). The guard set defines the privilege ladder. |
| `WritesFacet.sol` | every mutation and the guard it calls. Scan down the function list and look for the one that calls a *weaker* guard than its siblings. |
| `ViewsFacet.sol` | every authorization **predicate**. These are what the off-chain service calls; drift between them is the bug class. |

Privilege ladder to enumerate explicitly (Lit's): diamond `owner` → `configOperator` (node config)
→ `api_payer` (relayer for *managed* accounts only) → account `adminWalletAddress` → usage key
(scoped by group). Then ask of every write: *which rung, and how is it proven?*

Namespace-confusion hot spot: Lit kept masters, usage-key hashes **and** admin-wallet aliases in one
mapping (`allApiKeyHashesToMaster`). Consequences worth probing on any such design: same-namespace
squatting (victim's `keccak256(wallet)` pre-registered as someone's usage key), alias vs master
authority, and "a usage key that resolves to master but must not act as master"
(`revertIfNotMasterAccount` after resolution).

## 2. Relay-layer identity laundering (the check that transfers to every target of this shape)

The Rust service hashes the caller's credential and passes a `uint256` hash into the contract. Two
independent failure modes:

1. **Body-field injection** — an endpoint takes `account_api_key_hash` from the request body. In Lit
   every handler derives it from the header credential (`api_key_hash(api_key)`); verify this
   endpoint-by-endpoint, it is cheap and it is where clones of this architecture break.
2. **Hash passthrough** — `usage_api_key_to_hash()` returns the input unchanged when it is
   `0x` + 64 hex. If any endpoint accepts that shape as a *header* credential (or as a body value that
   is later treated as an identity), you can present a victim's account hash without signing. Lit had
   the passthrough but the billing/auth guards rejected hash-shaped header input (`is_precomputed_hash_shape`)
   and read paths hashed unconditionally → closed. **Check both halves on every target**: the passthrough
   function, and whether any inbound path lets the shape through.

Same family: EIP-712 mint endpoints. Read the verifier for (a) per-flow `primaryType` pinning,
(b) schema equality with `deny_unknown_fields` on field/domain/message, (c) the timestamp window,
(d) **single-use dedup**. Lit's dedup is a process-local moka cache and the code *documents* that a
multi-replica deployment widens the window — a documented limitation, not a finding.

## 3. Differential predicate harness (the deliverable that proves direction, not just absence)

`templates/DifferentialAuthz.t.sol` is the working shape. What makes it worth writing:

- **Fuzz the cross-product.** Random `uint256` seed → build N groups with seed-chosen membership
  (including the `address(0)` all-wallets and `0` all-actions wildcards) → build a seed-chosen scope
  set for a usage key (including `0` = execute-everywhere and a past/zero expiration) → then for every
  `(cid, wallet)` pair assert the slow, fast and combined views agree.
- **Assert the documented implication**, e.g. `canUseWallet ⇒ canExecute`. One line, catches real drift.
- **Four cross-tenant tests** that are worth reusing verbatim on any diamond:
  `strangerCannotWriteVictimAccount` (every write with the victim's hash, from a stranger account),
  `strangerCannotHijackRegisteredWalletOrPath` (same `pkpId` with fresh path, **and** fresh `pkpId`
  with the victim's public path — the second is the one that matters when keys are derived statelessly),
  `namespaceSquatIsEvictedAndDoesNotGrantAccess`, `masterKeyHasNoExecutionAuthority`.
- Keep it as `test/DifferentialAuthz.t.sol` in the repo's own tree so the maintainer runs it with
  their build; cite `forge test --match-contract DifferentialAuthz -vv`.

Lit result: 5/5 pass on `af5f682` with the upstream suite at 146/146 — i.e. the on-chain ACL held
**this round**. Report that as a verified negative with the command, never as "the code is secure".

## 4. Selector collisions across facets

Diamond facets share one dispatcher, so two facets exposing the same 4-byte selector is a real
privilege/behaviour bug (last cut wins). Mechanically:

```bash
cd <contracts dir>
for n in WritesFacet ViewsFacet APIConfigFacet BillingFacet DiamondCutFacet DiamondLoupeFacet OwnershipFacet; do
  forge inspect "$n" methodIdentifiers --json 2>/dev/null | tr -d '\r' > /tmp/sel/$n.json
done
# then group selector -> [(facet, signature)] in Python and print groups with len > 1
```

Use the **bare contract name**; the `path/File.sol:Contract` form errors with
*"Could not find source file for contract … at …"*. `tr -d '\r'` is required on Windows or the JSON
will not parse. Lit: 76 selectors across 8 facets, 0 collisions.

## 5. Sandbox egress — verify against the pinned upstream crate

Lit's own `egress.rs` comments assert that literal-IP URLs are caught by Deno's `deny_net` and
hostname/DNS-rebinding answers by a custom resolver. Believing the comment is how you miss the bug;
the check is 10 minutes:

```bash
mkdir -p ~/audit/deno_src && cd ~/audit/deno_src
curl -sLO https://static.crates.io/crates/deno_net/deno_net-0.240.0.crate
curl -sLO https://static.crates.io/crates/deno_permissions/deno_permissions-0.107.0.crate
tar xzf deno_net-0.240.0.crate && tar xzf deno_permissions-0.107.0.crate
grep -n "check_net_resolved" deno_net-0.240.0/ops.rs deno_net-0.240.0/ops_tls.rs
grep -n "fn check_resolved_ip_deny" -A40 deno_permissions-0.107.0/lib.rs
```

In 0.240.0 every net op (`Deno.connect`, `connectTls`, `listen`, `listenDatagram`) performs
`check_net` on the hostname **and** `check_net_resolved` on the resolved `IpAddr`, with deny-wins
semantics; `resolve_addr` does `lookup_host` then the caller consults the deny list before
`TcpStream::connect`. Conclusion: numeric-hostname aliases (`2130706433`) and DNS-rebinding records
are blocked at the permission layer, and the resolver-level `is_forbidden_ip` blocks the rest. That
closed the top hypothesis (SSRF into the co-located IPFS daemon / cloud metadata) — record it.

Adjacent surface worth the same treatment on any JS-sandbox target:
- **module loader**: allowlist must normalise `..` and re-parse before validating (a raw
  `starts_with("https://cdn.jsdelivr.net/npm/")` is escaped by `/npm/x/../../gh/evil/x.js`);
  `load()` at execution time should reject, not fetch.
- **custom HTTP clients**: `Deno.createHttpClient` builds its own `dns_resolver` and bypasses the
  sandbox resolver — deleting it plus stripping the `client` option inside the wrapped `fetch` is the
  correct pairing (both, not one).
- **native ops**: `process.binding('tcp_wrap').TCP.bind/listen/open`, `TTY(-1)`, `process.abort`,
  and feature-gated ops that call `std::process::exit(70)` in a V8 callback (a whole-server kill from
  one action). Grep the runtime for the replacement middleware; if it exists for all of them, the
  class is closed.

## 6. The leads that were disproved (say them out loud next time)

1. **Cross-tenant `getPrivateKey` via a wildcard usage key** — fixed (`#62`); the fuzz harness confirms
   a wildcard no longer skips `(cid, wallet)` resource scoping.
2. **Read endpoint accepting `X-Api-Key: 0x<accountHash>`** — read paths hash unconditionally
   (`api_key_hash`, no passthrough), so the hash never resolves.
3. **Double-crediting a Stripe top-up** (manual confirm + auto-topup webhook) — blocked four ways:
   `metadata[source]=auto_topup` filter, `status=="succeeded"`, PI amount vs DB row, DB
   `try_insert_credit`, plus a stable idempotency key derived from the PaymentIntent on the manual path.
4. **Replaying an EIP-712 mint signature** — single-use digest cache (documented per-replica caveat).
5. **`(pkpId, derivationPath)` aliasing to steal a key** — the release chokepoint re-derives the signer
   from the path and compares to the requested `pkpId`, so on-chain registry tricks fail closed.
6. **Hostname / DNS-rebinding egress bypass** — post-resolution deny check in the pinned crate (§5).

## 7. Where the remaining value was (honest coverage)

Left untested and ranked: (a) `lit-actions` **execution** differentials — native guards, fd adoption
via `open(fd)`, `node:fs` bindings, WASM/WASI — needs Linux + a full `deno_core` build; (b) the TS
attestation verifier (`protocol/attestation.ts`, ~1.3k lines: quote chain, RTMR replay, KMS signature
chain, TLS binding) — zero setup cost, highest "forge attestation" upside; (c) live production with a
self-provisioned account; (d) `lit-payments` auto-topup / SCA-resume / enterprise billing arithmetic.

That ordering — *cheapest path to the highest-impact class first* — is what to hand the next session.
