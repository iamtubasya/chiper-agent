# Immunefi PoC Guidelines & Rules

## ⚠️ VIOLATION = PERMANENT BAN

### PoC Rules
- ❌ **DO NOT TEST ON MAINNET OR PUBLIC TESTNET**
- ❌ Do not submit partial PoC if multiple tx needed
- ❌ Social engineering against employees
- ❌ DoS attacks against infrastructure
- ❌ Third-party attacks (not against protocol)

### PoC Requirements
- Must include flow of funds
- Proof of Identity required at PoC submission
- PoC must be **runnable code** (Foundry/Hardhat tests, NOT screenshots)
- Test on **mainnet fork** via Hardhat/Foundry, or project's test suite
- Calculate: **Total tokens at risk × average price = funds at risk**
- Optimize attack parameters to find **MAXIMUM economic damage**
- Clear print statements/comments detailing each attack step
- Show funds stolen/frozen in output
- Include all dependencies, config files, env variables needed

## Foundry PoC Template

```solidity
// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.15;

import "forge-std/Test.sol";

contract ExploitTest is Test {
    function setUp() public {
        // Fork mainnet at specific block
        vm.createSelectFork("mainnet", BLOCK_NUMBER);
    }

    function testExploit() public {
        // 1. Setup
        // 2. Execute attack
        // 3. Verify exploitation
        // 4. Print results
    }
}
```

### Foundry Execution
```bash
forge test --match-contract ExploitTest -vvvv
```

## Hardhat PoC Template

```javascript
const { ethers } = require("hardhat");

describe("Exploit", function () {
    it("Should exploit", async function () {
        // Fork mainnet
        await hre.network.provider.request({
            method: "hardhat_reset",
            params: [{
                forking: {
                    jsonRpcUrl: "YOUR_RPC_URL",
                    blockNumber: BLOCK_NUMBER,
                }
            }]
        });

        // 1. Setup
        // 2. Execute attack
        // 3. Verify exploitation
        // 4. Print results
    });
});
```

### Hardhat Execution
```bash
npx hardhat test
```

## Web3 PoC Submission
- Upload to Google Drive + share link, OR paste code directly if simple
- Include all dependencies in the upload
- README with setup instructions

## Web2 PoC Requirements
- Video showcasing attack (unlisted YouTube) + brief text explanation + HTTP request
- Screenshots of final attack acceptable
- HTTP requests acceptable
- Command line / runnable code acceptable
- Subdomain takeover with proof acceptable

### Web2 PoC Rules (VIOLATION = PERMANENT BAN)
- ❌ Do NOT insert malicious JavaScript payload
- ❌ Insert harmless JS only that doesn't affect other users/functionality
- ❌ Do NOT upload webshells (use empty/non-executable text files)
- ❌ Do NOT make invasive edits (use HTML comments if needed)
- ❌ Do NOT access sensitive info beyond what's needed for report

## Fund Calculation Formula
```
Funds at risk = Total tokens at risk × Average token price at submission time
Ideal bounty = 10% of funds at risk
```

## Bug Report Template Sections

1. **Title**: Concise description + severity + asset name
2. **Summary/Brief Intro**: 1-2 sentence overview
3. **Intro**: 1-3 paragraphs, high-level description, which asset affected
4. **Details**: Technical details, why/when it occurs, how it affects protocol, conditions for exploitation, core issue with evidence
5. **Impact**: Fund losses, affected scope, how exploit impacts funds, fundamental cause, cross-chain effects, most severe damages
6. **Risk Breakdown**: Category + Detail + Impact
7. **Recommendation**: Specific fix with code if possible
8. **References**: Code references, external links, related reports

### Submission Rules
- Every section on dashboard MUST be filled in
- Do NOT put everything in Bug Description section
- Do NOT write custom impact — pick from project's impact list
- Do NOT write custom asset — pick from project's asset list
- Dashboard supports Markdown format
