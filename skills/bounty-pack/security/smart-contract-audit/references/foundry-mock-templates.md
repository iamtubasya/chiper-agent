# Foundry Mock Contract Templates — DeFi Testing

## Attacker Philosophy
Mock contracts = simulate DeFi protocols to test exploit chains. If you can't fork mainnet, mock it.

## MockAavePool — Supply/Withdraw Exploit Testing

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract MockAavePool {
    mapping(address => mapping(address => uint256)) public userBalances;
    mapping(address => uint256) public totalDeposits;
    
    // Configurable failure modes for testing
    bool public shouldFailSupply;
    bool public shouldFailWithdraw;
    uint256 public supplyDelay;
    
    function supply(address asset, uint256 amount, address onBehalfOf) external {
        require(!shouldFailSupply, "MockAavePool: supply failed");
        if (supplyDelay > 0) { /* sim delay */ }
        IERC20(asset).transferFrom(msg.sender, address(this), amount);
        userBalances[onBehalfOf][asset] += amount;
        totalDeposits[asset] += amount;
    }
    
    function withdraw(address asset, uint256 amount, address to) external {
        require(!shouldFailWithdraw, "MockAavePool: withdraw failed");
        require(userBalances[msg.sender][asset] >= amount, "Insufficient balance");
        userBalances[msg.sender][asset] -= amount;
        totalDeposits[asset] -= amount;
        IERC20(asset).transfer(to, amount);
    }
    
    function setUserBalance(address user, address asset, uint256 amount) external {
        userBalances[user][asset] = amount;
    }
    
    function setFailSupply(bool fail) external { shouldFailSupply = fail; }
    function setFailWithdraw(bool fail) external { shouldFailWithdraw = fail; }
}
```

## MockUniswapV3Pool — Swap Exploit Testing

```solidity
contract MockUniswapV3Pool {
    address public token0;
    address public token1;
    uint24 public fee;
    uint160 public sqrtPriceX96;
    
    // Configurable price for oracle manipulation testing
    function setPrice(uint160 newPrice) external { sqrtPriceX96 = newPrice; }
    
    function swap(
        address recipient,
        bool zeroForOne,
        int256 amountSpecified,
        uint160 sqrtPriceLimitX96,
        bytes calldata data
    ) external returns (int256 amount0, int256 amount1) {
        // Simulate swap with configurable price impact
        if (zeroForOne) {
            amount0 = amountSpecified;
            amount1 = -int256(uint256(amountSpecified) * sqrtPriceX96 / 1e18);
        } else {
            amount1 = amountSpecified;
            amount0 = -int256(uint256(amountSpecified) * 1e18 / sqrtPriceX96);
        }
        // Transfer tokens
        IERC20(zeroForOne ? token0 : token1).transfer(recipient, uint256(amount0 > 0 ? amount0 : 0));
    }
}
```

## MockERC20 — Token with Configurable Behavior

```solidity
contract MockERC20 is IERC20 {
    string public name;
    string public symbol;
    uint8 public decimals;
    uint256 public totalSupply;
    mapping(address => uint256) private _balances;
    
    // Failure modes for testing unchecked return values
    bool public shouldFailTransfer;
    bool public shouldFailApprove;
    bool public isFeeOnTransfer;
    uint256 public feePercent;
    
    constructor(string memory _name, string memory _symbol, uint8 _decimals) {
        name = _name; symbol = _symbol; decimals = _decimals;
    }
    
    function mint(address to, uint256 amount) external {
        _balances[to] += amount;
        totalSupply += amount;
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        if (shouldFailTransfer) return false; // Silent failure!
        uint256 actualAmount = isFeeOnTransfer ? amount * (100 - feePercent) / 100 : amount;
        _balances[msg.sender] -= amount;
        _balances[to] += actualAmount;
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        if (shouldFailApprove) return false;
        return true;
    }
    
    function balanceOf(address account) external view returns (uint256) {
        return _balances[account];
    }
    
    function setFeeOnTransfer(bool enabled, uint256 _feePercent) external {
        isFeeOnTransfer = enabled;
        feePercent = _feePercent;
    }
}
```

## MockChainlinkOracle — Price Feed Manipulation

```solidity
contract MockAggregatorV3 {
    int256 private _price;
    uint8 private _decimals;
    
    constructor(int256 initialPrice, uint8 _dec) {
        _price = initialPrice;
        _decimals = _dec;
    }
    
    function setPrice(int256 newPrice) external { _price = newPrice; }
    function decimals() external view returns (uint8) { return _decimals; }
    
    function latestRoundData() external view returns (
        uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound
    ) {
        return (1, _price, block.timestamp, block.timestamp, 1);
    }
    
    function getRoundData(uint80) external view returns (
        uint80, int256 answer, uint256, uint256, uint80
    ) {
        return (1, _price, block.timestamp, block.timestamp, 1);
    }
}
```

## Foundry Test Patterns

### Testing Reentrancy
```solidity
contract ReentrancyTest is Test {
    function test_reentrancy() public {
        // 1. Setup: deploy victim + attacker
        // 2. Fund victim with tokens
        // 3. Call attacker.attack()
        // 4. Assert: attacker drained all tokens
        // 5. Assert: victim balance = 0
    }
}
```

### Testing Access Control
```solidity
function test_unauthorizedAccess() public {
    vm.prank(attacker);
    vm.expectRevert("Not authorized");
    victim.withdraw(amount);
}
```

### Testing Flash Loan Attacks
```solidity
function test_flashloanManipulation() public {
    // 1. Deploy MockAavePool with flash loan
    // 2. Deploy MockUniswapV3Pool with manipulable price
    // 3. Deploy MockAggregatorV3 with oracle price
    // 4. Execute flash loan: borrow → manipulate price → profit → repay
    // 5. Assert: profit > 0 (attack succeeded)
}
```

## Common Pitfalls
1. `vm.warp()` required for time-locked functions
2. Mock tokens need `name()`, `symbol()`, `decimals()` if constructor calls them
3. `nonReentrant` blocks re-entry — test via callback, not same-function re-entry
4. Approval amounts — set `type(uint256).max` in mock setup
5. Balance assertions — use `assertGt` for relative checks, not exact amounts
6. OZ v5 `_transfer` NOT virtual — use manual IERC20 for test tokens
7. `vm.startPrank` + `new Constructor()` FAILS — use one-shot `vm.prank` before `new`
8. **`vm.warp(block.timestamp + X)` INSIDE A LOOP ONLY ADVANCES THE CLOCK ONCE.** The optimizer
   (`via_ir` especially) treats `block.timestamp` as loop-invariant and hoists the read, because it
   cannot see that the `vm.warp` external call mutates it. Symptom seen in a real harness:
   `SegmentNotComplete(0, 3585)` — second iteration elapsed time was 0, so the state machine refused
   to advance; the `-vvvv` trace showed `VM::warp(3601)` twice in a row. Fix: carry an explicit cursor.
   ```solidity
   uint256 t = block.timestamp;
   for (uint256 i = 0; i < 6; i++) { t += SEGMENT; vm.warp(t); step(); }
   ```
9. **Approving the wrong token: approve the STAKED token, not the reward token.** In a farm harness
   `deposit(pid, lp)` pulls the LP via `transferFrom`, so it needs `pair.approve(farm, max)` — approving
   the reward token instead yields `ERC20InsufficientAllowance(spender, 0, amount)` in `setUp()`.
10. **Shared harness constants go at file scope.** `ContractName.PUBLIC_CONSTANT` is not reliably
    reachable through the contract type, and `///` (NatSpec) on a file-level variable is a compile
    error: `@notice not valid for file-level variables`. Use a file-level `uint256 constant` with a
    `//` comment.
11. **Prank ordering:** `vm.deal` (and any cheatcode call) consumes a pending `vm.prank`. Fund first,
    then prank, then call.

## Deterministic-winner harness (prize / lottery / reward flows)

To drive a full payout end to end with no real oracle, mock the entropy so the outcome is computable
off-chain, then mint a ticket that is guaranteed to win:

```solidity
contract MockEntropy {
    mapping(bytes32 => bool) public req;
    function requestFor(bytes32 s) external returns (uint256) { req[s] = true; return 1; }
    function rerequest(bytes32 s) external returns (uint256) { req[s] = true; return 2; }
    function isReady(bytes32) external pure returns (bool) { return true; }        // settle in one pass
    function isRequested(bytes32 s) external view returns (bool) { return req[s]; }
    function entropyFor(bytes32 s) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(WORD, s));                               // fixed word
    }
}
```

Reproduce the contract's own derivation to predict each segment's character:
`salt = keccak256(abi.encodePacked(round, segment))`,
`mix = uint256(keccak256(abi.encodePacked(WORD, salt)))`,
`char = ALPHABET[mix % 26]` (when the class counter keeps the segment in the letter class — with no
nudges the counters are seeded from previous letter chars, so the class never changes).

Two traps:
- **The entry validator may reject your computed winner.** A `_validateString` that bans repeated
  characters makes some winning strings unmintable. Search for the first round whose winner has six
  distinct characters (`_findCleanRound()`) instead of hard-coding round 2.
- **Settle the round the ticket actually plays.** Entry functions usually target `currentRound + 1`,
  so mint while `currentRound == r - 1`, then settle `r - 1` (no winners) and `r` (winners found).

Assert the **balance-sheet identity after every step**, not once at the end —
`escrow.balance() == livePot + unclaimedPool + protocolCutAccrued` (+ any other earmarked bucket).
A per-step assertion turns a passing test into a proof and names the exact operation that broke it.
