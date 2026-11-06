// SPDX-License-Identifier: MIT
// Starter invariant harness for medusa / echidna on a UUPS (or any upgradeable) target.
// Copy into <project>/contracts/harness/  (NOT test/ - crytic-compile must see it), then:
//   forge build
//   medusa fuzz --compilation-target . --target-contracts TargetInvariant --timeout 600 --seq-lines 15 --workers 2
//   echidna . --contract TargetInvariant --test-mode property --timeout 300
//
// Verified working on the Vana DataPortabilityEscrow (2026-10): the campaign started only after
// (a) moving this file under contracts/, (b) deploying the target behind MiniProxy because the
// implementation's constructor calls _disableInitializers(), (c) whitelisting the mock asset as ADMIN.

pragma solidity ^0.8.24;

// ---- minimal ERC1967 proxy: often needed because recovered OZ trees ship ERC1967Utils.sol but NOT ERC1967Proxy.sol
contract MiniProxy {
    bytes32 internal constant IMPL_SLOT = 0xREDACTED_********;
    constructor(address impl_, bytes memory initData) {
        assembly { sstore(IMPL_SLOT, impl_) }
        if (initData.length > 0) {
            (bool ok, bytes memory ret) = impl_.delegatecall(initData);
            require(ok, string(abi.encodePacked("init failed: ", ret)));
        }
    }
    fallback() external payable {
        assembly {
            let impl_ := sload(IMPL_SLOT)
            calldatacopy(0, 0, calldatasize())
            let r := delegatecall(gas(), impl_, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch r
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
    receive() external payable {}
}

// ---- minimal ERC20 (no OZ import needed; keeps the harness independent of the target's remappings)
contract MockERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    function mint(address to, uint256 a) external { balanceOf[to] += a; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s] = a; return true; }
    function transfer(address to, uint256 a) external returns (bool) {
        require(balanceOf[msg.sender] >= a, "bal"); balanceOf[msg.sender] -= a; balanceOf[to] += a; return true;
    }
    function transferFrom(address f, address t, uint256 a) external returns (bool) {
        require(balanceOf[f] >= a, "bal");
        uint256 al = allowance[f][msg.sender];
        if (al != type(uint256).max) { require(al >= a, "allow"); allowance[f][msg.sender] = al - a; }
        balanceOf[f] -= a; balanceOf[t] += a; return true;
    }
}

interface ITarget {
    function initialize(address admin, address privileged) external;
    function depositToken(address account, address token, uint256 amount) external;
    function settle(address from, address to, address asset, uint256 amount, uint8 opKind, bytes32 ref) external;
    function withdraw(address account, address asset, uint256 amount, bytes32 ref) external;
    function balanceOf(address account, address asset) external view returns (uint256);
}

contract TargetInvariant {
    ITarget public target;
    MockERC20 public token;

    address internal constant PRIV  = address(0xFAC);   // the privileged role: the harness must NOT hold it
    address internal constant VICTIM = address(0xB0B);
    address internal attacker;                          // = the harness (a role-less caller)

    uint256 public deposited;        // what this harness legitimately put in
    uint256 public attackerBaseline; // the attacker's own balance snapshot

    constructor() {
        attacker = address(this);
        // 1) deploy the implementation, 2) initialise THROUGH the proxy as the ADMIN
        address impl = deployImpl();                    // replace with: new TargetImplementation()
        bytes memory initData = abi.encodeWithSignature("initialize(address,address)", address(this), PRIV);
        target = ITarget(address(new MiniProxy(impl, initData)));
        token = new MockERC20();
        token.mint(address(this), 1_000_000 ether);
        token.approve(address(target), type(uint256).max);
        // 3) administer the target (harness IS the admin) - e.g. whitelist the asset, else
        //    depositToken reverts AssetNotSupported and every later step is a no-op.
        _adminSetup();
        target.depositToken(VICTIM, address(token), 1000 ether);   // deposits are usually open by design
        deposited = 1000 ether;
        attackerBaseline = token.balanceOf(attacker);
    }

    function deployImpl() internal returns (address) { /* return address(new TargetImplementation()); */ }
    function _adminSetup() internal { /* e.g. ITarget(admin).setTokenWhitelisted(address(token), true); */ }

    // ---- actions a role-less caller may attempt (ALL must fail) ----
    function settle_attacker(uint256 amt) public {
        try target.settle(VICTIM, attacker, address(token), amt, 5, bytes32(0)) {} catch {}
    }
    function withdraw_attacker(uint256 amt) public {
        try target.withdraw(VICTIM, address(token), amt, bytes32(0)) {} catch {}
    }

    // ---- invariants: BOTH naming styles so medusa and echidna share one harness ----
    function invariant_no_unauthorized_extraction() public view returns (bool) {
        return token.balanceOf(attacker) <= attackerBaseline;
    }
    function echidna_no_unauthorized_extraction() public view returns (bool) {
        return token.balanceOf(attacker) <= attackerBaseline;
    }
    function invariant_ledger_covered_by_balance() public view returns (bool) {
        return token.balanceOf(address(target)) >= target.balanceOf(VICTIM, address(token));
    }
    function echidna_ledger_covered_by_balance() public view returns (bool) {
        return token.balanceOf(address(target)) >= target.balanceOf(VICTIM, address(token));
    }
}
