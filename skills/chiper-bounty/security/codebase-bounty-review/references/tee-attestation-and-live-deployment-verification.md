# Live-deployment attribution + TEE attestation verification

Companion to PART 9 (on-chain ACL + service monorepo). Two jobs that turn a source review into a
reportable, load-bearing result:

1. **Is the thing running the thing I read?** (diamond-aware, build-profile-aware)
2. **Does the vendor's own trust anchor actually hold?** (re-implement their verifier, don't trust it)

Both are "verified negative / verified match" work by default. Their value is that they make every
other claim in the report credible — and occasionally one of them is itself the finding.

---

## 1. Attribute the live diamond to a commit

### 1a. Enumerate facets over RPC

An EIP-2535 proxy's own runtime code is ~200 bytes of dispatch; the logic is in N facets. Get the map:

```python
# raw selectors, all view calls
facets()                           0x7a0ed627   -> (address facet, bytes4[] selectors)[]
facetAddresses()                   0x52ef6b2c   -> address[]
facetFunctionSelectors(address)    0xadfca15e   -> bytes4[]   (address ABI-encoded, left-padded to 32B)
owner()                            0x8da5cb5b
supportsInterface(bytes4)          0x01ffc9a7
```

Return data is ABI: `[0]=offset`, `[1]=count`, then `count` words. For a facet's selector list the
entries are 4-byte values right-aligned in a word — take `word[:8]`.

```
faucet-check: (len(eth_getCode(proxy)) - 2)//2 should be ~200 bytes;
              if it is in the thousands you are looking at a non-diamond or already-delegated code.
```

Cross-check the diamond address against the service's own config endpoint where one exists
(e.g. `GET /core/v1/get_node_chain_config` returned `contract_address` — cheaper and authoritative
vs. hardcoding from docs).

### 1b. Diff the selector SET, in both directions

```bash
for n in WritesFacet ViewsFacet APIConfigFacet BillingFacet DiamondCutFacet DiamondLoupeFacet OwnershipFacet; do
  forge inspect "$n" methodIdentifiers --json | tr -d '\r' > "sel_$n.json"
done
```

```python
norm = lambda s: s[2:] if s.startswith("0x") else s
live_all = {norm(s) for ss in live_facet_selectors.values() for s in ss}
repo_all = {norm(s) for ss in (set(json.load(open(f)).values()) for f in selfiles) for s in ss}
print("hidden  :", sorted(live_all - repo_all))   # functions no source shows you
print("missing :", sorted(repo_all - live_all))   # stale deployment, predates a fix
```

⛔ **Normalise `0x` first.** Raw comparison gave *76 hidden + 76 missing* on a diamond whose source
matched exactly. An all-hidden-and-all-missing result is a normalisation bug, not a finding.

Per-facet identity: `max(repo.items(), key=lambda kv: len(set(ss) & kv[1]))` and require
`overlap == len(ss) == len(best)`; anything else is a facet you have not identified.

### 1c. Byte-diff with the DEPLOYMENT's compiler

Read the `Makefile` / CI `compile:` target — **not** `foundry.toml`. A repo can ship both and build
with only one.

Observed (LIT-Protocol/chipotle, 2026-10):

| facet | live | `forge build` | `npx hardhat compile` |
|---|---|---|---|
| APIConfigFacet | 2037B | 1961B | 2037B |
| BillingFacet | 1339B | 1302B | 1339B |
| ViewsFacet | 9217B | 8957B | 9217B |
| WritesFacet | 14916B | 14604B | 14916B |

Cause: Foundry's default `evmVersion` is **cancun** (PUSH0, 1-byte push for small constants);
Hardhat's default is **paris**. The `forge build` numbers look like a real divergence and are not.
Under Hardhat every length matched exactly and the byte diff was **32 bytes, all inside the trailing
CBOR metadata block** (the IPFS hash) — i.e. every executable byte identical.

How to state it, safely:

```
Runtimes match the deployed code byte-for-byte in length; the only differing bytes are the
metadata hash at offset <N>. Executable code is identical ⇒ the deployed implementation is the
audited commit, with no hidden or backported logic.
```

Checklist before writing that sentence:
- compiler = the one the pipeline uses; settings = `optimizer.runs`, `viaIR`, `evmVersion` all copied
- contract selected by the explorer's/`artifacts` NAME, not "first object with bytecode"
- enumerate the diff offsets and confirm each one lands in the trailing metadata blob
- facets under `libraries/` have **no Hardhat artifact** (outside `sources`) — say you verified them
  by selector match only, rather than implying a byte diff you did not run
- record the per-facet table in COVERAGE.md; "0 hidden, 0 missing, N bytes = metadata hash"

### 1d. Report shape

Live-vs-source attribution belongs in the report as a **stated premise**, not an appendix: it is what
lets the vendor triage the real finding instead of arguing about which commit you read.

---

## 2. Verify the vendor's attestation by re-implementing it

Trigger: the program pays for "forge attestation" / "extract keys" / "break the sandbox", and the repo
ships a verifier module (TS/JS/Rust) of a few hundred to ~1500 lines. Reading it is not review — it is
reading the thing that is supposed to be trusted.

**Method:** write a second implementation from the *spec* (docs + the on-chain contracts), in a
different language, and run it against the live endpoint. Agreement is the evidence. Disagreement is
either your bug or theirs — resolve it before writing anything.

`scripts/verify_tdx_attestation_v2.py` is the working shape (Lit Chipotle: 40+ checks, all green).
Run it as `python scripts/verify_tdx_attestation_v2.py https://api.example.com`.

### Check ladder (TDX + dstack-style)

1. **Response shape** — `version`, nonce echoed, signer object present.
2. **Quote** — version 4, tee type 2 (ECDSA-P256), att-key type 0x81 (TDX), TD attributes not debug.
3. **Quote signature** over `b[0:632]` under the attested key.
4. **QE report binds the attested key** — `sha256(att_key_xy || qe_auth) == qe_report[320:352]`.
5. **PCK chain** → pinned Intel SGX root key (compare the *public key bytes*, and the CNs).
6. **Event log replay** → RTMR0..3 must equal the quote's values.
7. **Measured identity** — `app-id` event == policy app id; `sha256(app_compose)` == `compose-hash`
   event; `/info` agrees; `vm_config.os_image_hash` == `os-image-hash` event.
8. **Images digest-pinned** — `/@sha256:[0-9a-f]{64}$/` on every `image:` line of the compose.
9. **KMS key-release chain** — `app_signature` → app key over `purpose:signer`;
   `kms_signature` → KMS root over `dstack-kms-issued: || app_id || app_key`; root must equal the
   **pinned** value (pinning is what stops a dishonest RPC from substituting its own root).
10. **KMS identity** — the quote's `key-provider` event id == the on-chain `caPublicKey`.
11. **Freshness** — signer's statement signature over `domain || nonce || keccak(quote)` recovers to
    the signer key.

### The traps (each cost a debugging cycle)

- ⛔ **`cryptography` wants DER; TDX quotes carry raw `r||s`.** A 64-byte raw signature handed to
  `verify()` always fails `InvalidSignature`. Wrap it:
  `encode_dss_signature(int(sig[:32]), int(sig[32:]))`. Same for the QE report signature.
- ⛔ **PCK chain verify direction.** Each cert is signed by its PARENT:
  `root.public_key().verify(root.signature, root.tbs)` (self),
  `root.public_key().verify(ca.signature, ca.tbs)`,
  `ca.public_key().verify(leaf.signature, leaf.tbs)`.
  Using `ca.public_key()` for the CA's own signature fails the moment the chain is real.
- ⛔ **pycryptodome keccak needs an explicit size**: `keccak.new(digest_bits=256)` — plain
  `keccak.new()` raises `Digest size not provided`.
- ⛔ **The `ecdsa` package may reject the point** (`Point does not lay on the curve`) on a perfectly
  valid P-256 key. Prefer `cryptography` for verification; if you need recovery maths, hand-roll it
  (a 25-line affine add/mul over the P-256 params is enough and is a genuinely independent check).
- **Recoverable secp256k1 signatures:** split `r||s||v`, normalise `v` (`>=27 → v-27`), get candidates
  with `VerifyingKey.from_public_key_recovery_with_digest(r_s, digest, curve=SECP256k1,
  sigdecode=sigdecode_string)` and index by `v`.
- **Quote `report_data` being all-zero is not a finding.** In dstack-style designs the *quote* carries
  no caller nonce by design; freshness is provided one layer up by the signer's statement over
  `nonce || keccak(quote)`. Read how the v2 endpoint adds freshness before reporting "no freshness".
- **Verify twice when the claim is High+**: `cryptography` + hand-rolled point maths. Two independent
  implementations of the same check is the multi-tool reproduction bar, applied to crypto.

### Outcome shapes

- **All green** → verified negative for the forgery/replay/re-pairing class. Say so explicitly with
  the check count, and stop spending budget there. This is a *result*, not an absence of one.
- **A pin mismatch** (`PINNED_KMS_ROOTS` vs on-chain) → could be rotation or a dishonest RPC; the
  honest write-up is "the SDK fails closed on rotation", not "the deployment is forged".
- **A check the vendor verifier runs but the spec does not require** → look for the inverse: a
  guarantee the docs claim (freshness, boot binding, image pinning) that the verifier never checks.
  That gap is the finding class worth hunting here.

---

## 3. What "done" looks like for this lane

```
verified-with-tool-evidence:
  live selector set == repo (0 hidden, 0 missing), per-facet table
  live bytecode == Hardhat build of HEAD except the CBOR metadata hash
  attestation re-implementation: N checks green against <origin>
reviewed-negative-with-reason:
  egress filter verified against the pinned upstream crate source
NOT-tested:
  facets under libraries/ (no artifact; selector match only)
  any lane needing Linux + a full runtime build
```
