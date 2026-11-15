# Repo Bootstrap + On-Chain Source Recovery (EVM audit)

Recipe proven on the Superstate engagement (2026-09-30), but written to be target-agnostic.
Two independent problems this solves:

1. A public Solidity monorepo whose `lib/` submodules are empty and whose imports use
   `<lib>/src/...` paths — you cannot compile, so slither/aderyn/echidna are dead.
2. The public repo HEAD is months/years behind what is actually deployed, so the code you
   CAN read is not the code that is live. The real artifact is reachable from the chain.

---

## A. Bootstrap a repo whose submodules are empty

```bash
git clone --depth 1 https://github.com/<org>/<repo>.git work
cd work

# init only the submodules you need; depth 1 so it is fast
git submodule update --init --depth 1 lib/forge-std lib/openzeppelin-contracts \
      lib/openzeppelin-contracts-upgradeable lib/openzeppelin-contracts-v4
# SKIP huge monorepos (chainlink is hundreds of MB) — vendor just the interface file
```

For a vendored interface, fetch the file from a **release tag**, not a branch: several
`chainlink` paths 404 on `develop`/`master` but serve fine from a tag.

```bash
mkdir -p lib/chainlink/src/v0.8/shared/interfaces
curl -sL "https://raw.githubusercontent.com/smartcontractkit/chainlink/v2.14.0/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol" \
  -o lib/chainlink/src/v0.8/shared/interfaces/AggregatorV3Interface.sol
head -3 lib/chainlink/src/v0.8/shared/interfaces/AggregatorV3Interface.sol   # verify it is NOT "404: Not Found"
```

### ⛔ The foundry auto-remap trap (cost the most time)

Foundry derives remappings from library directory names. **Once `<lib>/src/` exists it
rewrites `<libname>/` → `<lib>/src/`.** So an import written as `chainlink/src/v0.8/...`
resolves to `lib/chainlink/src/src/v0.8/...`. Creating that nested dir makes foundry detect
it again and escalate to `src/src/src/...` — an unwinnable chase.

Symptom:
```
Error (6275): Source "lib/chainlink/src/src/src/v0.8/shared/interfaces/AggregatorV3Interface.sol" not found
```

**Fix — pin it with an explicit `remappings.txt` entry pointing at a dir that does NOT
contain `src/`.** Explicit `remappings.txt` beats the auto-derived mapping.

```bash
echo "chainlink/=lib/chainlink-dep/" >> remappings.txt
echo "onchain-redemptions/=lib/onchain-redemptions/" >> remappings.txt
mkdir -p lib/chainlink-dep/src/v0.8/shared/interfaces
cp lib/chainlink/src/v0.8/shared/interfaces/AggregatorV3Interface.sol \
   lib/chainlink-dep/src/v0.8/shared/interfaces/
rm -rf lib/chainlink/src/src        # remove the escalating duplicates you created
forge build --skip test
```

Some repos import a literal path (`lib/onchain-redemptions/lib/chainlink/contracts/src/...`);
those are resolved relative to the project root, not via remappings, so the file must exist
at that literal path too. Create every distinct path the compiler asks for, then re-run.

### ⛔ Tests that import a SIBLING repo through a literal relative path

A shallow clone of repo A leaves `lib/B/lib/C/` empty when C is B's own submodule (A↔B↔C
nesting is common in vendor monorepos). If a test imports through that literal path, no
remapping can help — the directory itself must exist:

```bash
# test/v3/RedemptionYieldV3.t.sol:
#   import {IRedemptionIdle} from
#     "../../lib/ustb/lib/onchain-redemptions/src/interfaces/IRedemptionIdle.sol";
mkdir -p lib/ustb/lib/onchain-redemptions
cp -r src lib/ustb/lib/onchain-redemptions/          # resolves against the project root
```

Two things to recognise so you do not misread it as a broken repo:

1. **The sibling test file imports the SAME file via a completely different path**
   (`src/interfaces/IRedemptionIdle.sol`) in the same directory. That inconsistency is a
   copy-paste artefact from the sibling repo, not a missing contract — do not go hunting for
   an absent `RedemptionYieldV3.sol`.
2. Add `remappings.txt` entries for the siblings that lib B's own sources import —
   crucially `<lib>/=lib/<lib>/` **without** `/src`, otherwise the auto-remap turns
   `ustb/src/allowlist/AllowList.sol` into `ustb/src/src/allowlist/AllowList.sol`:

```
openzeppelin/=lib/openzeppelin-contracts-upgradeable/contracts/   # lib B's AllowList.sol needs this
ustb/=lib/ustb/
onchain-redemptions/=lib/onchain-redemptions/
```

Outcome on the redemptions repo: 32 files compiled, 7 suites green, **231/231** once an
archive RPC was supplied (see section B).

---

## B. Slither on a foundry project

```bash
forge build --build-info --skip test      # ⛔ REQUIRED before slither
slither . --foundry-ignore-compile
```

- Without `--build-info`, `out/build-info/` holds a stub and crytic-compile dies with
  `FileNotFoundError: .../<id>.output.json`. It wants a JSON that has an `output` key.
- **Do NOT pass `--solc 0.8.28`** — slither treats the argument as an executable path:
  `FileNotFoundError: [WinError 2]` / `InvalidCompilation`. Let forge pick solc.
- **`$?` is not trustworthy for the `slither.exe` shim.** Both `slither . --foundry-ignore-compile`
  runs here returned **exit=127** while `out` held a complete, correct analysis ending in
  slither's own summary. Read the artifact's last line (`analyzed (N contracts …), M result(s)
  found`), not the exit code.
- Slither analysed 77–89 contracts and produced 600–750 results; 95% is `unused-state` /
  `constable-states` noise. Triage by detector name, and filter to `src/` to drop
  `lib/forge-std/**` and `script/**` hits:

```bash
grep -oE "^Detector: [a-z-]+" report.txt | sort | uniq -c | sort -rn
# the ones worth reading: divide-before-multiply, reentrancy-*, incorrect-equality,
# arbitrary-send, unchecked-transfer, uninitialized-state, access-control
```

`forge test` on a fresh clone also needs the **nested** submodule:
`git submodule update --init --depth 1 lib/forge-std/lib/ds-test`
(if that leaves the dir empty, `git clone --depth 1 https://github.com/dapphub/ds-test.git lib/forge-std/lib/ds-test`).

Fork tests failing with `vm.envString: environment variable "RPC_URL" not found` is an
**environment** result — not a code failure. Report PASS/FAIL counts excluding those.

### ⛔ Fork suites need an ARCHIVE node — a live-read RPC is not enough

Two distinct failure modes, both environmental, only one of which looks dangerous:

| Symptom | Cause | Verdict |
|---|---|---|
| `vm.envString: environment variable "RPC_URL" not found` | env var not exported | ENVIRONMENT |
| `[FAIL: EVM error; database error: failed to get account for 0x5615dEB7…: HTTP error 403 … "Archive requests require a personal token"]` | RPC is not an archive node | PROVIDER GAP |

The second one is the trap: the address in the message is **Foundry's own deterministic
deployer**, not the target, and every forked suite fails identically while all non-fork suites
pass. Provider wording varies — publicnode says `-32602 Archive requests require a personal
token`, `rpc.flashbots.net` says `state at block #N is pruned`, and both mean the same thing.

Measured fix on the redemptions suite (pinned fork blocks 19,976,215 and 21,933,146):

```bash
ETH_RPC_URL=https://eth.drpc.org forge test
# before (publicnode): 24 passed, 6 failed
# after  (drpc):      231 tests passed, 0 failed, 0 skipped
```

Never write the first number up as failing tests. It is **NO RESULT / provider gap / re-run
pending** — and closing it with an archive RPC converts the whole suite into a live-contract
regression check against the deployed addresses.

---

## C. Testing an upgradeable implementation directly does not work

Implementation contracts call `_disableInitializers()` in their constructor. So
`new Impl(); impl.initialize(...)` reverts with `Initializable: contract is already
initialized`. To exercise initializer logic you MUST deploy behind a proxy:

```solidity
import {ERC1967Proxy} from "openzeppelin-contracts/contracts/proxy/ERC1967/ERC1967Proxy.sol";

SuperstateTokenV4 impl = new SuperstateTokenV4();
bytes memory initData = abi.encodeCall(SuperstateTokenV4.initialize, ("Name", "SYM"));
ERC1967Proxy proxy = new ERC1967Proxy(address(impl), initData);
SuperstateTokenV4 t = SuperstateTokenV4(address(proxy));
assertEq(t.owner(), address(0));   // now real state, not implementation state
```

Immutable variables live in the **implementation** bytecode, not in proxy storage. An
immutable that no constructor assigns reads as its zero value through delegatecall — that is
exactly how the Superstate fresh-deploy ownership dead-end was proven (see appendix).

---

## D. Recovering the deployed source when the repo is stale

Decision point: if the docs announce a new contract version (e.g. "in September 2026 we
update the allowlists to v4.2") and `git ls-remote origin` shows no branch with that code,
the source does not exist publicly. Get it from the chain.

```bash
# 1. confirm it is really an upgradeable proxy and find the implementation
cast storage <PROXY> 0xREDACTED_******** \
  --rpc-url <RPC>
# 2. sanity-check the proxy's own version getter
cast call <PROXY> "VERSION()(string)" --rpc-url <RPC>

# 3. fetch the VERIFIED source of the implementation (no API key needed)
curl -s "https://eth-sepolia.blockscout.com/api/v2/smart-contracts/<IMPL>" -o impl.json
python - <<'PY'
import json
d = json.load(open('impl.json', encoding='utf-8'))
print(d['name'], '|', d['file_path'], '| verified:', d['is_verified'])
print('compiler:', d['compiler_version'], '| opt:', d['optimization_enabled'], d['optimization_runs'])
print('source_code len:', len(d['source_code'] or ''), '| additional_sources:', len(d.get('additional_sources') or []))
json.dump(d['abi'], open('impl.abi.json', 'w'), indent=1)
open('Impl.sol', 'w', encoding='utf-8').write(d['source_code'])
PY
```

Endpoint notes:
- **Correct path is `/api/v2/smart-contracts/{ADDR}`** (returns `name`, `file_path`,
  `source_code`, `abi`, `additional_sources`, `compiler_version`, `optimization_runs`,
  `verified_at`). `/api/v2/addresses/{ADDR}/source-code` is a different, older shape.
- Sourcify (`sourcify.dev/server/v2/contract/{chainId}/{addr}`) returns
  `{"match": null, ...}` when the contract is verified elsewhere — `match: null` is NOT proof
  the contract is unverified. Try Blockscout before concluding "no source".
- Explorer hosts differ per chain: `eth.blockscout.com`, `eth-sepolia.blockscout.com`,
  Plume/other testnets have their own.

### ⛔ Validate the recovered source before trusting it

A flattened file from an explorer is only useful if it is the real artifact. Recompile it
with the **exact** settings from the verification record — a clean build at the same
`solc` + `optimizer_runs` is strong evidence the source is complete and bytecode-consistent.

```bash
mkdir -p v42/src && cp Impl.sol v42/src/
cat > v42/foundry.toml <<'EOF'
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.28"
optimizer = true
optimizer_runs = 1000000
EOF
cd v42 && forge build --build-info && slither . --foundry-ignore-compile
```

Then read the recovered source for the areas the repo *couldn't* show you — usually signed
writes (`setAllowedWithSignature`-style relayable EIP-712 paths), access-control guards, and
ERC-7201 storage-slot constants. Check that duplicated slot constants actually match:
`keccak256(abi.encode(uint256(keccak256("ns")) - 1)) & ~bytes32(uint256(0xff))`.

---

## E. Live read verification with `cast`

Public RPCs are not interchangeable — and "works for reads" says nothing about archive
support, which is a separate capability fork tests depend on. Measured on this box:

| RPC | live reads | archive (fork tests) | notes |
|---|---|---|---|
| `https://ethereum-rpc.publicnode.com` | ✅ | ❌ | mainnet reads only; archive → `-32602 Archive requests require a personal token` |
| `https://eth.drpc.org` | ✅ | ✅ | **the one that made the fork suite green (231/231)**; free plan excludes some L2s (Sepolia refused: `chain is not available on free plan`) |
| `https://eth-mainnet.public.blastapi.io` | ✅ | ✅ (probe) | served `eth_getStorageAt`/`eth_getBalance` at block 19,976,215 |
| `https://ethereum-sepolia-rpc.publicnode.com` | ✅ | — | Sepolia reads |
| `https://rpc.flashbots.net` | ⚠️ | ❌ | `state at block #N is pruned` |
| `https://eth.merkle.io` | ⚠️ | — | `-32005 Rate limit exceeded` |
| `https://eth.llamarpc.com` | ❌ | ❌ | HTTP 525 |
| `https://cloudflare-eth.com` | ⚠️ | — | `-32603 Internal error` on some calls |
| `https://rpc.ankr.com/eth` | ❌ | ❌ | demands an API key |
| `https://1rpc.io/eth` | ❌ | ❌ | HTTP 502 |

Probe archive support in one call before launching a fork suite — asking for state at an old
block is the discriminator, and a non-archive node answers with a provider error rather than
pruning silently:

```bash
curl -s -m 20 -X POST -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"eth_getBalance","params":["<ADDR>","0x130D9E7"]}' \
  "$RPC"        # 0x130D9E7 = block 19,976,215; a JSON-RPC error = not archive
```

`cast call` argument-order gotcha: for a no-arg function pass **no** extra args —
`cast call $ADDR "VERSION()(uint8)" --rpc-url $RPC`. Appending a stray `0` yields
`Error: encode length mismatch: expected 0 types, got 1`.

---

## F. Engagement anchors — Superstate (2026-09-30)

- Vendor policy: `security@superstate.co`, **no formal reward** (acknowledgement only), safe
  harbour in `docs.superstate.com/investors/security`. Scope named in the docs =
  `github.com/superstateinc/ustb` + `github.com/superstateinc/onchain-redemptions` + the API.
- Public repo HEAD was **2025-04-14** on both repos; live mainnet USTB reports
  `VERSION() "1.3.0"` while repo main declares `"4"` → repo main is AHEAD of mainnet.
  Treat repo findings as unreleased code unless reproduced on a live address.
- Non-prod API hosts are public while their frontends are behind Cloudflare Access:
  `api.dev.superstate.com`, `api.staging.superstate.com` → `200` on `/api-docs/openapi.json`
  (`dev.superstate.com`, `staging.superstate.com` → 302 to `superstate.cloudflareaccess.com`).
- The whole authenticated API is HMAC-signed (`Authorization: Bearer <apikey>` plus
  `X-Nonce`/`X-Timestamp`/`X-Params-Hash`/`X-Body-Hash`/`X-Hmac`, signature covers
  `api_key + nonce + timestamp + params_hash + body_hash`, 60 s window). **Without a key the
  signed surface is untestable** — say so instead of implying coverage.
- The README of `request-with-api-key` contains a **known-disclosed** npm supply-chain
  incident (SECURITY.md, UNC5142, 2026-01-16 → 2026-05-28). Already public; do not re-report.
- Allowlist **v4.2** source recovered from Sepolia (impl `0x9e5e9653…`, proxy `0x04c19BBC…`,
  `VERSION() "4.2.0"`, verified 2026-07-20). Review result: clean. Two things worth knowing
  if you pick it up again:
  - `isAddressAllowedForPrivateInstrument` / `isAddressAllowedForFund` gate on
    `_callerSymbolMatches()` — a **symbol-string** check, not an identity check. Harmless
    because the guarded reads return `allowed[msg.sender][addr]` (self-scoped), so it never
    leaked cross-token state and never granted permission. Do not report it as auth bypass.
  - The EIP-712 domain separator is **cached at `initialize()`** and only rebuilt when
    `chainid`/`address(this)` change, so after an in-place upgrade the domain's `version`
    field keeps the version string captured at init time. Integration footgun only; signers
    must read `DOMAIN_SEPARATOR()` from the contract rather than deriving it from `VERSION()`.
- Fresh-deploy ownership dead-end (proven, Low): `SuperstateToken` v3/v4 declare
  `address private immutable _deprecatedAdmin;` and **no constructor assigns it**, while
  `initializeV2()` (the only caller of `__Ownable2Step_init()`) requires
  `msg.sender == _deprecatedAdmin` → it always reverts, `owner()` stays `address(0)`, and
  every `_checkOwner()` admin path is permanently dead. PoC pattern in section C.

### Verified negatives — do not re-test on resume

- `onchain-redemptions` fork suite is **fully green (231/231)** against mainnet state at blocks
  19,976,215 (v1) and 21,933,146 (v2) → the deployed redemption path behaves as the repo's
  tests expect. Re-running this is confirmation, not discovery.
- Slither on `onchain-redemptions` (683 results) and `ustb` (745 results): no high/critical in
  `src/`. Only `divide-before-multiply` (rounding favours the protocol), benign
  `reentrancy-events`, timestamp comparisons, view-only external calls in loops.
- API: no auth/enumeration routes exist (`/v1/auth/*`, `/v1/users`, `/v1/me`, `/v1/entities`,
  `/v1/organizations`, `/graphql`, `/health`, `/metrics`, `/status` → all `404`, 9 B) on prod,
  dev and staging alike; `/v1/accounts/onboard/*/mock` → `404` prod, `401` dev/staging; only
  `/api-docs/openapi.json` + `/swagger-ui/*` are exposed. Error bodies leak the stack type
  (`Invalid URL: Cannot parse 'abc' to a i32` — Rust/axum) = informational only.
- `POST /v1/funds/{id}/real-time-price` ignores `unix_timestamp` (0 and 1 → `400`, anything
  larger returns the *current* price), so there is no price-tampering primitive there.
- Cloudflare fronts the API and blocks injection payloads (`1%20OR%201=1` → CF block page;
  arjun aborts with `Encountered an error`). That is **BLOCKED, not a clean negative** — record
  it as such rather than implying sqlmap/dalfox-class coverage was achieved.
