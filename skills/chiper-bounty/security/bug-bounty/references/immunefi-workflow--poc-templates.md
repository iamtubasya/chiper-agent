# Immunefi PoC Templates

## Foundry PoC Template (Web3)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "./src/VulnerableContract.sol";

contract ExploitTest is Test {
    VulnerableContract vulnerable;
    address attacker = address(0xBEEF);
    address owner = address(0xDEAD);
    
    function setUp() public {
        // Fork mainnet
        vm.createSelectFork("mainnet");
        
        // Setup contract state
        vulnerable = VulnerableContract(<address>);
        
        // Fund attacker
        vm.deal(attacker, 100 ether);
    }
    
    function testExploit() public {
        // Step 1: Attacker deposits
        vm.prank(attacker);
        vulnerable.deposit{value: 10 ether}();
        
        uint256 balanceBefore = address(vulnerable).balance;
        console.log("Contract balance before:", balanceBefore);
        
        // Step 2: Execute exploit
        vm.prank(attacker);
        vulnerable.withdraw(); // Reentrant call
        
        uint256 balanceAfter = address(vulnerable).balance;
        console.log("Contract balance after:", balanceAfter);
        
        // Step 3: Verify drain
        assertEq(balanceAfter, 0, "Contract should be drained");
        assertGt(address(attacker).balance, 10 ether, "Attacker should profit");
        
        console.log("Attacker profit:", address(attacker).balance - 10 ether);
    }
}
```

## Hardhat PoC Template (Web3)

```javascript
const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Exploit", function () {
    let vulnerable, attacker;
    
    before(async () => {
        // Fork mainnet
        await hre.network.provider.request({
            method: "hardhat_reset",
            params: [{
                forking: {
                    jsonRpcUrl: `https://eth-mainnet.g.alchemy.com/v2/${process.env.ALCHEMY_KEY}`,
                },
            }],
        });
        
        [attacker] = await ethers.getSigners();
        
        const Vulnerable = await ethers.getContractFactory("VulnerableContract");
        vulnerable = await Vulnerable.attach("<address>");
    });
    
    it("Should drain contract", async () => {
        const balanceBefore = await ethers.provider.getBalance(vulnerable.address);
        console.log("Balance before:", ethers.utils.formatEther(balanceBefore));
        
        // Execute exploit
        await vulnerable.connect(attacker).withdraw();
        
        const balanceAfter = await ethers.provider.getBalance(vulnerable.address);
        console.log("Balance after:", ethers.utils.formatEther(balanceAfter));
        
        expect(balanceAfter).to.equal(0);
    });
});
```

## Key Elements Checklist
- [ ] Runnable code (not screenshots)
- [ ] Mainnet fork or test suite
- [ ] Clear print/comment for each step
- [ ] Funds stolen/frozen displayed
- [ ] All dependencies documented
- [ ] Total funds at risk calculated
- [ ] No testing on public testnet/mainnet
- [ ] Complete and non-partial
