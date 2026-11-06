# Multi-chain deployment audit — enumerate, verify, size

For protocols deployed across dozens of chains (bridges, intent/solver hubs,
deposit-address relays). The unit of work is not one contract — it is one
*deployment* repeated N times, plus the diffs between the repetitions.

Worked reference: a cross-chain settlement protocol with 61 configured chains
(51 EVM + 10 non-EVM). Full sweep took ~10 minutes of wall clock; it produced the
deployment-integrity result, the fleet-consistency result, the funds-at-rest map,
and the verified source — before a single line of Solidity was read by hand.

## Step 1 — Get the authoritative inventory from the protocol's OWN config API

Do not scrape docs for addresses, and do not assume the chains you can name are
the chains they run. These protocols usually serve a machine-readable deployment
map because their own solver consumes it.

Look for a `/chains`, `/config`, `/networks`, or `/deployments` route on the API
host. The response typically carries, per chain: `id`, `name`, `httpRpcUrl`,
`explorerUrl`, `disabled`, `depositEnabled`, `vmType`, a `contracts` map
(multicaller / receiver / router / approvalProxy / …), a versioned `protocol`
block with a `depository`, and a `solverAddresses` list.

```bash
curl -s https://api.<target>/chains -o chains.json
python -c "import json;d=json.load(open('chains.json'));cs=d['chains'];print(len(cs));print(sorted(cs[0]))"
```

That file becomes the worklist **and** the single source of truth for every
address you will test. Two things fall out immediately: the real chain count
(often far above the marketed number) and the `vmType` split, which tells you
which chains are even reachable from an EVM tool.

## Step 2 — Deployment integrity: does every advertised contract actually exist?

The highest-signal cheap check. For each chain, for each advertised address, ask
the chain whether there is code there. A configured-but-undeployed contract, or a
zero address in a live config, is a real finding class — an integrator following
that config will call a no-op.

- `eth_getCode(addr)` returns `0x` ⇒ **no bytecode**: either a not-yet-deployed
  address or an EOA where a contract is expected. Flag it.
- A zero address in the map is flagged outright — do not even query it.
- Non-EVM `vmType` (`svm`, `tvm`, `bvm`, `lvm`, `xrpvm`, `tonvm`, `hypevm`) has no
  JSON-RPC: bucket it and report it as *not covered by this sweep*, never as clean.

## Step 3 — Fleet consistency: read the same slot on every chain and diff

Roles are usually the same across the fleet. Read them everywhere and let the
outlier surface itself — a chain whose owner or signer differs is either a stale
deployment, a partially-migrated one, or a compromise. Any of the three is worth
the report.

```python
owner     = eth_call(depository, "0x8da5cb5b")  # owner()
allocator = eth_call(depository, "0xaa5dcecc")  # allocator()
```

Then `Counter()` the results and print every chain that deviates from the
majority. In the worked case: 53 `approvalProxy` owners and 51 depositories all
collapsed to **one** owner and **one** allocator, with **zero** outliers — a
clean result, and a genuinely useful thing to be able to state.

Also check: any chain flagged `disabled: true` that still holds a balance. That
is funds stranded in a decommissioned path.

## Step 4 — Detect the deterministic-deployment pattern (CREATE2)

If the addresses are byte-identical across chains, the protocol deploys with
CREATE2 / a deterministic deployer. Consequences that change your whole approach:

- **Audit the code ONCE.** It is the same runtime everywhere; a per-chain read of
  the source is wasted effort. Recover it once and apply the conclusion fleet-wide.
- A chain whose config points at a *different* address for the same role is now
  much more interesting than it would be otherwise.
- Proxy detection: read the EIP-1967 implementation slot
  `0xREDACTED_********` and the
  admin slot `0xREDACTED_********`.
  A **direct** (non-proxy) contract has neither, which means a bug in it is
  unfixable without migration — that is what makes the program's
  "permanently unrecoverable" (×1.5) and "high remediation cost" (×1.25)
  modifiers apply, so determine it early.

## Step 5 — Size the exposure (funds at rest, per chain)

Read the native balance of the money-holding contract on every chain, then sort
descending. This converts an abstract "the depository could be drained" into a
severity argument with numbers, and it tells you which chains actually matter.

```python
native = int(eth_getBalance(depository), 16) / 1e18
```

**Before you believe any number, run a CONTROL address through the same call.**
Query a burn address and a random address on the same endpoint. If they return the
same value as the interesting contract, the RPC serves a mock/placeholder and the
number is meaningless. Real case: one chain reported `4.2e57` native tokens — an
impossible amount that reads exactly like a catastrophic mint — and the *identical*
value came back for `0x…dEaD`. One extra request prevented a fabricated Critical.
(Cross-ref `triage-validation`, "control address" rule.)

## Step 6 — Source recovery, then read it once

Sourcify is the fastest verified-source route when the vendor's repo does not
carry the deployed version. Use the **v2** endpoint and read the **top-level**
`sources` key:

```bash
curl -s "https://sourcify.dev/server/v2/contract/<chainId>/<addr>?fields=all" -o sourcify.json
python -c "import json;d=json.load(open('sourcify.json'));print(d['match']);print(list(d['sources']))"
```

Working shape and the three traps (the legacy `/server/files/...` path 403s as
browser-only; `compilation.sources` is empty so it reads as "unverified";
`runtimeBytecode.onchainBytecode == .recompiledBytecode` proves your rebuild is
faithful): `onchain-source-recovery`.

## Step 7 — When there is no source, read the selectors

Bytecode-only targets still expose their interface. The dispatcher compares the
calldata selector, so the selector constants sit next to `EQ`/`GT`/`LT` (opcodes
`0x14`/`0x10`/`0x11`/`0x15`/`0x16`) as `PUSH4` (`0x63`) immediates:

```python
import re
b = open('target.hex').read()[2:]
sels = {m.group(1) for m in re.finditer(r'63([0-9a-f]{8})', b)
        if b[m.end():m.end()+2] in ('14','10','11','15','16')}
```

Resolve each against `https://www.4byte.directory/api/v1/signatures/?hex_signature=0x…`
(free, no key). This is enough to tell a fund-moving entry point from a view
helper — in the worked case six selectors resolved to `depositNative`,
two `depositErc20` overloads, `execute(...)`, `allocator()`, `setAllocator(address)`,
`owner()`, and the Solady ownership-handover trio, which told us the whole money
path was allocator-signature gated without a line of source.

## Harness pitfalls (each one cost real time)

1. **Sweep with threads and SHORT per-call timeouts.** A sequential loop over
   dozens of chains stalls for minutes because a handful of dead RPCs each burn the
   full timeout. `ThreadPoolExecutor(max_workers≈10-12)` + a 7-9 s timeout turns a
   stall into a ~2-minute run. Keep the per-request sleep policy honest — this is a
   read-only sweep against public endpoints, not a scan.
2. **Never name a helper after a stdlib module.** A working file called
   `selectors.py` in the engagement directory shadowed Python's stdlib `selectors`
   module, so an *unrelated* script (`import google.auth` → `asyncio` → `import
   selectors`) crashed with a traceback pointing deep inside `asyncio`. Any script
   in the CWD is importable ahead of the stdlib. Name them `dep_selectors.py`,
   `chain_audit.py`, etc.
3. **Rotate RPC endpoints.** Public RPCs 403/504 unpredictably. Keep a list and try
   them in order inside the `rpc()` helper rather than hard-coding one host.
4. **Windows/MSYS path trap:** `curl -o /tmp/x.json` then reading `/tmp/x.json`
   from a native Windows Python fails — the paths are not the same filesystem.
   Write into the engagement directory (a native `D:\…` path) and read that.

## Reporting discipline for this class

Consistency and hygiene results are usually **not payable**, and saying so is part
of the work. On a program whose rules state that admin-only paths cap at S1 and are
only eligible when an unprivileged party can reach the role, "the depository is
owned by a single EOA" is not a finding — it is context. Record it as an
observation, state the ineligibility reason plainly, and keep hunting the path that
an unprivileged caller can actually walk. A sweep that returns "fleet is clean,
here is the proof" is a legitimate deliverable; dressing it up as a vulnerability
is not.

**The exception that makes it payable: documented-vs-deployed divergence.** The
centralization itself is context — but when the vendor's own documentation asserts a
DIFFERENT control, the divergence *is* the finding, because the doc is what
integrators, auditors and reviewers rely on. Two worked instances from one fleet
sweep:

- The depository's `owner()` is a plain EOA (`eth_getCode` = `0x`, explorer
  `is_contract: false`) across all 51 EVM chains, while the protocol docs state the
  owner is "a security council multisig". What makes it credible rather than a
  generic "admin is an EOA" complaint: a real multisig **does** exist elsewhere in
  the same system — another privileged role's owner is a 3-of-5 Safe
  (`getThreshold()`/`getOwners()`), and the documented council address verifies as a
  multisig-signer contract. Cite that contrast: the EOA is the outlier, not the norm.
- The docs publish one oracle address; that contract has been stripped of its
  operator role, so every action it submits reverts inside a `try/catch` and is
  reported as an `ExecutionFailed` event, while its live replacement is undocumented.
  **Quantify it** rather than asserting it: pull the last N receipts at each address
  and count `Executed` vs `ExecutionFailed`, then give each one's last-seen block.
  ("published oracle: 0 Executed / 372 ExecutionFailed; live oracle: 396 Executed /
  0 Failed; V1 last active ~10 days after V2 went live.")

Both landed as S1-class documentation / privilege-management findings. The technique
generalizes: **for every published address and every stated control, read the
deployed value and diff.** Docs, `llms.txt`, AsyncAPI/OpenAPI specs, audit PDFs and
blog posts are all assertions you can falsify — and a falsified one is reportable
even when the underlying centralization would not be.

**Check for a deprecation channel before calling any endpoint behaviour a bug.** An
endpoint that looks like a version-downgrade auth gap is often a deliberately
retired one. Read the response body for a `deprecation` object and read the vendor's
docs (Mintlify-hosted docs usually serve every page as `<url>.md`). Real case:
`GET /requests/v2` returned bulk transaction data unauthenticated while `/v3`
demanded an API key — a textbook finding shape — but the body carried `deprecatedAt`,
`throttledFrom` (which also explained the 429s being seen), `sunsetAt`, a `successor`
and a migration-guide URL. A documented, deliberately-throttled, scheduled-retirement
endpoint is not a vulnerability. Do not report it; log it as coverage.

**A public, unrestricted sweep function is only a finding if the contract actually
holds funds.** Router-style helpers (`cleanupErc20s` / `cleanupNative`, where
`amount == 0` means "full balance" and the recipient is caller-chosen) look like a
theft primitive. Before reporting, sweep the contract's balance on every chain — if
it is zero everywhere, the issue is theoretical, and programs that exclude
"theoretical issues with no viable PoC" will reject it. Record it as a hardening
observation and re-check periodically: the moment any flow leaves residue there, it
becomes live.
