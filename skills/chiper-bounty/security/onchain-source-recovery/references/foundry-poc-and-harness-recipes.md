# Foundry PoC + isolated-harness recipes

Concrete recipes from validating recovered / deployed Superstate contracts (2026-10-01). All of these were hit for
real; each one cost a compile cycle.

## 1. Isolated project for a recovered single-file contract

When the recovered contract is a flattened file (or the original repo will not build), make a throwaway project and
give the tool something it can compile:

```bash
mkdir -p v42/src && cp recovered.sol v42/src/
cat > v42/foundry.toml <<'EOF'
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.28"
optimizer = true
optimizer_runs = 1000000     # match the explorer's reported settings exactly
EOF
cd v42 && forge build --build-info      # --build-info is REQUIRED before slither
slither . --foundry-ignore-compile
```

## 2. `allow_paths` — remappings may not point outside the project

If your `remappings.txt` points at a sibling directory (reusing another repo's libs), foundry refuses:

```
Error (6275): Source "../fresh/onchain-redemptions/lib/openzeppelin-contracts-upgradeable/contracts/..."
not found: File outside of allowed directories.
```

Fix by listing the roots you legitimately need. Include both the POSIX and the Windows spelling, because the same
config gets read by git-bash foundry and by tools running under WSL:

```toml
allow_paths = ["D:/data hermes/bug-bounty/_progress/<eng>/recon",
               "/mnt/d/data hermes/bug-bounty/_progress/<eng>/recon"]
```

## 3. Deploying behind a proxy in a test (initializers run in PROXY storage)

Calling `initialize()` on the bare implementation always reverts with
`Initializable: contract is already initialized` — the constructor calls `_disableInitializers()`. You must go
through a proxy:

```solidity
RedemptionIdle impl = new RedemptionIdle(address(token), address(feed), address(usdc));
bytes memory init = abi.encodeCall(
    Redemption.initialize,                                   // <- see 4
    (address(this), 3600, address(0xBEEF), fee)
);
RedemptionIdle r = RedemptionIdle(payable(address(new ERC1967Proxy(address(impl), init))));  // <- see 5
```

## 4. `abi.encodeCall` must name the contract that DECLARES the function

`abi.encodeCall(RedemptionIdle.initialize, ...)` fails with *"Member initialize not found or not visible after
argument-dependent lookup in type(contract RedemptionIdle)"* even though it is inherited and callable. Name the
declaring base instead: `abi.encodeCall(Redemption.initialize, ...)`, and import that base.

## 5. A payable fallback blocks the plain address cast

Contracts with `fallback() external payable` cannot be cast as `Contract(address(x))`:

```
Error (7398): Explicit type conversion not allowed from non-payable "address" to "contract X",
which has a payable fallback function.
```
Use `X(payable(address(x)))`.

Also: Solidity enforces EIP-55 on address literals. `0x000...ABCD` is rejected with
*"This looks like an address but has an invalid checksum"*; the correct form of that value is `0x000...ABcD`.

## 6. The "unguarded input in initialize" PoC shape

Useful template for any finding of the form *"initializer assigns X without the bound its setter enforces"*.
Prove three things, not one — the third is what decides the severity:

```solidity
function test_sane_value_works()      // live/mainnet-like value behaves
function test_bad_value_breaks()       // out-of-range value accepted; the dependent paths revert
function test_owner_can_repair()       // <-- decides High vs QA
```

For `redemptionFee`, `test_owner_can_repair()` PASSED (`setRedemptionFee(0)` works because the cap only blocks
INCREASES above 10), which is exactly why the mythril "High" was rated Informational instead of High. **Write the
recovery assertion before assigning severity** — a self-inflicted assertion failure is the cheapest severity
downgrade there is.

Do not add mocked plumbing by hand if the repo already has it: check `test/` for existing mock tokens/feeds and
extend the repo's own base test contract when one exists.

## 7. Bytecode-only symbolic execution

`myth analyze -f <hex>` has no source maps, so `Function name:` is always "constructor". Attribute findings by
matching the calldata's leading 4 bytes against `cast sig "<candidate signature>"` for every ABI entry. Keep
`--no-onchain-data` so the executor does not make RPC calls you did not sanction.
