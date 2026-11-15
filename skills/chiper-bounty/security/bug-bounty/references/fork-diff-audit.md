# Fork-Diff Audit — Protocols That Fork Audited Codebases

Trigger: target admits forking audited code (CapyFi→Compound V2, many lending forks), or bytecode/source smells like a known codebase. Do NOT line-read the whole protocol — diff it.

## RULE 0 — SCOPE GATE FIRST (before ANY deep-dive on custom contracts)

Pull the bounty program's in-scope TARGET LIST before auditing anything custom.

Immunefi pages are SPAs — rendered text extraction fails. Targets/impacts are embedded as unicode-escaped JSON inside a script blob in the raw HTML:

```python
import re, json
s = open('page.html', encoding='utf-8', errors='ignore').read()
blob = s.encode().decode('unicode_escape', errors='ignore')
targets = re.findall(r'\\"description\\":\\"([^"\\\\]+)\\"', s)   # raw form
impacts = re.search(r'"impacts":\[.*?\]', blob)                    # decoded form
```

Fallback patterns: `__NEXT_DATA__` may be absent; search raw HTML for known impact strings ('Direct theft of any user funds', 'Permanent freezing').

Cost of skipping this: session spent a full audit pass on the oracle + IRM + whitelist of CapyFi — all THREE out of scope (only ca-pTokens + Comptroller + Unitroller + web app listed) → two real findings died at triage. Check target list + impact list, then allocate effort.

## STEP 1 — Fetch verified source (Blockscout v2 API, no key needed)

```
https://eth.blockscout.com/api/v2/smart-contracts/{addr}
```

Returns: `name`, `is_verified`, `is_proxy`, `implementations`, `abi`, `source_code`, and crucially **`additional_sources`** = the full flattened file tree (each entry `{file_path, source_code}`). Save all of them to disk — CToken.sol etc. live there, not in `source_code`. When Etherscan API key is missing, Blockscout (eth.blockscout.com) usually has the same contracts verified.

Proxy recognition:
- Gnosis Safe = SafeProxy bytecode (`0x363d3d373d3d3d363d73...` prefix) — standard, not a finding.
- Compound CustomProxy (CErc20Delegator, Unitroller) stores impl in **slot 0** / via `implementation()` getter — EIP1967 slot reads ZERO for them. Don't conclude "not a proxy" from a zero EIP1967 slot.

## STEP 2 — Diff vs upstream

```bash
curl -s "https://raw.githubusercontent.com/<org>/<repo>/master/contracts/X.sol" -o upstream_X.sol
diff <(tr -d '\r' < upstream_X.sol) <(tr -d '\r' < local_X.sol)
```

Normalize CRLF on BOTH sides (`tr -d '\r'`) or every line shows as changed. A 60KB Comptroller reduced to a 1-line diff takes minutes. Report ONLY the diff hunks as candidate findings; verbatim = clean, say so and move on.

Real example (CapyFi): Comptroller = upstream V7 (0.8.10 + proposal65 fix) verbatim except `getCompAddress()` → `address(0)`; CToken = upstream + whitelist mint-gate only; Unitroller/CErc20/JumpRateModelV2 verbatim. Whole core cleared in one session.

## STEP 3 — Audit only the diff + the genuinely custom glue

Custom layers that survive the diff: oracle wrapper, interest-rate params, access-control modules, deployer-set config. Classify each as trusted-admin (Safe multisig = NOT reportable) vs user-reachable.

## PITFALLS

- **Immutable public vars have NO getters** — `cast call baseRatePerYear()` reverts on JumpRateModelV2-style contracts (immutable storage). Read per-block sibling vars instead (`baseRatePerBlock`, `multiplierPerBlock`, `jumpMultiplierPerBlock`, `kink`) and convert (APY = perBlock × 2_628_000).
- **Latent admin-triggered bugs are not findings.** A hardcoded dead address that bricks the protocol IF the admin enables a dormant feature (e.g. compSpeeds>0 with `getCompAddress()==address(0)`) = trusted-admin action → Info at best. Immunefi rejects these. Do not inflate; do not submit.
- **Bounty scope list is authoritative over your finding list.** Out-of-scope target = finding dead regardless of quality. Re-check scope after every finding, before writing the report.
- Token units ≠ USD. Convert TVL/borrows to USD before judging "dust market" severity.
