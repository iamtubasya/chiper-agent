# EVM + recon triage walkthrough — Superstate, 2026-10-01

Raw material behind RULE 36/37/38. Numbers are measured, not estimated.

## 1. Scoreboard: 4 scanner "High" labels -> 0 vulnerabilities

| tool | label | after triage | why |
|------|-------|--------------|-----|
| aderyn (onchain-redemptions) | High: "ETH transferred without address checks" | FALSE POSITIVE | flagged `redeem(address,uint256)` / `redeem(uint256)`; caller pays, `receive()`+`fallback()` revert so contract holds no ETH |
| aderyn (ustb) | High: "Arbitrary `from` passed to transferFrom" | FALSE POSITIVE | `ERC20Upgradeable.transferFrom({from: src, ...})` inside a standard `transferFrom(src,dst,amount)` that calls `_spendAllowance` first |
| aderyn (ustb) | High: "Storage array edited with memory" | FALSE POSITIVE | callee `_comparePermissionStructs` is `internal pure`; compares `keccak256(abi.encode(...))` and reverts `AlreadySet()`. Real write is the next line: `permissions[entityId] = permission;` |
| mythril (deployed bytecode) | High: SWC-101 "arithmetic operator can underflow" | REAL BUT QA (not High) | selector `e24df754` = `initialize(address,uint256,address,uint256)`; see below |

## 2. mythril on REAL DEPLOYED bytecode — the working recipe

Source analysis kept failing on imports (`chainlink/`, `openzeppelin-contracts/`), so pivot to bytecode.

Obstacles hit, in order:
1. `myth analyze <file> --solv 0.8.28` -> `requests.exceptions.ConnectionError` to
   `solc-bin.ethereum.org` / `Failed to resolve`. **That host is dead** (Solidity moved to
   `binaries.soliditylang.org`); it is a stale-tool bug, not a target problem.
   Fix: `SOLC=/home/windows10/.local/bin/solc` (WSL already had 0.8.28) and DROP `--solv`.
2. `--solc-json '{"remappings":[...]}'` was **not applied** — crytic still reported
   `Searched the following locations: ""`. Don't burn time here; use bytecode.
3. Get the bytecode that actually matters — the DEPLOYED one:

```bash
export PATH="$PATH:/home/agentuser/.foundry/bin"
RPC=https://ethereum-rpc.publicnode.com
# EIP-1967 implementation slot behind a proxy
cast storage <PROXY> 0xREDACTED_******** --rpc-url $RPC
# strip the leading 0x000000000000000000000000 to get the impl address
cast code <IMPL_OR_NONPROXY_ADDR> --rpc-url $RPC > target_deployed.hex
```

Measured sizes: oracle 7,123 B (14,247 hex chars); RedemptionIdle impl 10,371 B (20,743 hex chars).

4. Bounded run (unbounded symbolic execution on ~10 KB bytecode will not finish):

```bash
wsl -d Ubuntu -- bash -lc "cd '<dir>' && timeout 800 myth analyze -f target_deployed.hex \
  --execution-timeout 240 --solver-timeout 20000 -t 1 --no-onchain-data 2>&1 | tail -50"
```

`--no-onchain-data` matters: it stops mythril from making network calls. Keep it on for any third-party target.

Result: oracle -> `The analysis was completed successfully. No issues were detected.`
RedemptionIdle -> SWC-101 High + SWC-116 Low.

## 3. Selector attribution — the step that changes the verdict

mythril prints the exact calldata in the txn sequence. Map the first 4 bytes:

```
mythril calldata: e24df754...  ->  initialize(address,uint256,address,uint256)
mythril calldata: 3aeef3d3...  ->  getChainlinkPrice()
mythril calldata: bbffa979...  ->  calculateUsdcOut(uint256)
```

Generate the table once and keep it:

```bash
for s in "redeem(uint256)" "redeem(address,uint256)" "calculateUstbIn(uint256)" "calculateUsdcOut(uint256)" \
         "calculateFee(uint256)" "maxUstbRedemptionAmount()" "withdraw(address,address,uint256)" \
         "withdrawToSweepDestination(uint256)" "setRedemptionFee(uint256)" "initialize(address,uint256,address,uint256)" ; do
  printf "%-46s %s\n" "$s" "$(cast sig "$s")"
done
```

`initialize(...)` — a deployer-only, one-shot path — is a completely different severity conversation from
`calculateUsdcOut(...)` in the live money path.

## 4. The PoC that corrected its own author

Root cause: `Redemption.initialize` does `redemptionFee = _redemptionFee;` with **no bound**, while the setter
`_setRedemptionFee` enforces `if (_newFee > 10) revert FeeTooHigh();`. A fee above `FEE_DENOMINATOR` (10_000)
makes `usdcOutAmountBeforeFee - calculateFee(...)` underflow (0.8.x checked maths -> revert).

PoC file: `recon/fresh/onchain-redemptions/test/InitFeeBrick.t.sol`

Iteration log (each failure taught something):
- v1 asserted fee 10_001 **permanently** bricks the contract and `setRedemptionFee(0)` reverts too.
  Result: `[FAIL: next call did not revert as expected]` on the LAST assertion.
  Discovery: `_setRedemptionFee` only rejects `newFee > 10` — **lowering is allowed**, so the owner repairs it.
- v2 (passing, 2/2) asserts: fee 0 -> `calculateUsdcOut(1e6) == 11e6`; fee 10_001 -> `calculateUsdcOut`,
  `calculateUstbIn`, `maxUstbRedemptionAmount` all revert; then `setRedemptionFee(0)` succeeds and the price path
  works again.

Final rating: **Informational / QA** — deployer-only, no funds at risk, owner-recoverable.

Other compile traps in the same file (foundry working copies of these repos):
- `RedemptionIdle.initialize` is inherited from the abstract base -> must be referenced as `Redemption.initialize`
  in `abi.encodeCall`, else `Member "initialize" not found ... in type(contract RedemptionIdle)`.
- `RedemptionIdle(payable(address(proxy)))` — the contract has a payable `fallback()`, so a plain
  `address -> contract` conversion is rejected (`Explicit type conversion not allowed`).
- Solidity enforces EIP-55 on address literals: `0x...ABCD` is rejected, the correct form is `0x...ABcD`.
- Custom errors declared inside a contract/interface must be qualified for `expectRevert`:
  `IAllowlistV4_0.InvalidNonce.selector`, `IAllowlistV4_2.OnlyCallableByTokenContract.selector`,
  `OwnableUpgradeable.OwnableUnauthorizedAccount.selector`.

## 5. Recon differentials — measured outcomes

**Wildcard DNS:** `zzz-nope-12345.target.com` and `totally-random-9f3a.target.com` -> NXDOMAIN.
So no wildcard. 10 subfinder hosts were NXDOMAIN anyway (cert-transparency/mis-join FPs) and were NOT reported.
`eks.dev` + `mail.eks.dev` DID resolve (Cloudflare-proxied) but both served 000 over HTTPS and
`nslookup -type=CNAME` returned no CNAME -> dangling proxied record, information-only.

**Takeover:** `nuclei -l subs.txt -t <mirror>/http/takeovers` (77 templates) -> 0 findings.

**S3/CloudFront:** all four `assets.*` hosts returned `<Code>AccessDenied</Code>` for `/?list-type=2`.
AccessDenied = bucket exists and is private. `NoSuchBucket` would be the takeover signal. Also tried
`/index.html`, `/robots.txt` — 403 across the board.

**Catch-all SPA:** `.well-known/{security.txt,openid-configuration,ai-plugin.json,assetlinks.json,trust.txt,gpc.json,nodeinfo}`
ALL 200 at ~31.5 KB. Compared against a bogus path: same `<title>Superstate</title>` shell. Not real files.
Same test retired `/signup`, `/forgot-password`, `/reset-password`, `/api`, `/app`, `/portal`, `/onboarding`, `/kyc`.
Real routes were distinguishable by a *different* size: `/signin` 11,516 B, `/dashboard` 303-redirects.

**Dir bust:** gobuster with a 4,751-word list against three hosts -> 0 results outside the published OpenAPI.

**CORS:** CORScanner on four hosts -> "Finished CORS scanning" with zero findings.

## 6. JS bundle mining -> app API surface

`katana -u <host> -d 2 -jc -silent` (18,228 URLs on the portal, 34,914 on docs) -> 1,677 unique `.js` -> 30
downloaded and regex-mined. Recovered from the bundles:

```
/admin , /admin/entities/${entity_id} , /admin/organizations/${organization_id}
/api/${env}/entity_application/${id}                      (used with method: "PUT")
/api/admin/funds/${fundInstrumentId}/gas-costs/invoice
```

Browser-setup note: the shell `while read` download loop produced 0 files twice (subshell counter + `md5sum`
pipeline). A ~30-line Python script using `urllib.request` downloaded 30/55 reliably and did the regex mining in
the same pass — prefer that for bundle mining.

Then `OPTIONS` (not GET) proved which recovered names are real routes:
`/api/admin/funds/1/gas-costs/invoice` -> `405 allow=GET, HEAD`; the sibling guesses returned 200 with empty
`allow` (catch-all) and are NOT evidence of routes.

An unauthenticated `GET` on that proven route returned `500 {"message":"Internal Error"}`. Recorded as an unrated
LEAD with the exact request/response, explicitly noting that no data was returned and that no state-changing
method was sent to confirm it.

## 7. Bonus: CSP as an inventory source

The `Content-Security-Policy` on the portal's sign-in page enumerated `assets.dev`, `assets.staging` AND
`assets.devddx` in `img-src`, independently corroborating the otherwise-undocumented non-production environment
found via subdomain enumeration; `connect-src` listed the Solana Pyth feed, Plume RPCs, an Alchemy endpoint and a
live Helius RPC hostname. Read the CSP before you enumerate — it is a free map of first-party and third-party hosts.
