// SPDX-License-Identifier: MIT
// Template: live fork test for a recovered, signature-gated allowlist / permission contract.
// Proven on Superstate AllowlistV4_2 (v4.2) on Sepolia, 9/9 PASS.
//
// Layout: recon/<name>f/{foundry.toml, src/<Recovered>.sol, test/<ThisFile>.t.sol, lib/forge-std}
// foundry.toml must use the SAME solc + optimizer settings the explorer reports.
// Run: SEP_RPC=https://ethereum-sepolia-rpc.publicnode.com forge test -vv
pragma solidity ^0.8.28;

import {Test} from "forge-std/Test.sol";
// Concrete type, NOT the interface: the interface usually lacks owner()/VERSION()/constants.
import {
    AllowlistV4_2,
    IAllowlistV4_2,
    IAllowlistV4_0,
    IAllowlistChecker,
    OwnableUpgradeable,
    PermissionFlag,
    PermissionFlags
} from "../src/AllowlistV4_2.sol";

/// @notice A contract that presents the SAME symbol() as the real token without being it.
contract SymbolSpoofer {
    function symbol() external pure returns (string memory) {
        return "USTB"; // <- substitute the real instrument symbol
    }

    function probePrivate(address allowlist, address target) external view returns (bool) {
        return IAllowlistV4_2(allowlist).isAddressAllowedForPrivateInstrument(target, "USTB");
    }

    function probeFund(address allowlist, address target) external view returns (bool) {
        return IAllowlistV4_2(allowlist).isAddressAllowedForFund(target, "USTB");
    }
}

contract AllowlistV42LiveTest is Test {
    AllowlistV4_2 internal constant A = AllowlistV4_2(0x04c19BBC13BE44388ABFC9123c259143F8D0fac6);
    address internal constant TOKEN = 0x39727692cF58137Bd8c401eFE87Cc8A190D62ead;
    address internal constant DOC_OWNER = 0x4e71a3233fdea518147C82DeDeF8BCF917B57c80;
    address internal constant RAND = address(0xBEEF);
    // NOTE: Solidity enforces EIP-55 checksum on address literals. 0x...ABCD is REJECTED;
    // the correct form for that value is 0x...ABcD.
    address internal constant FRESH = address(0x000000000000000000000000000000000000ABcD);

    function setUp() public {
        // publicnode serves eth_call; use an ARCHIVE rpc if you need a pinned historical block
        vm.createSelectFork(vm.envOr("SEP_RPC", string("https://ethereum-sepolia-rpc.publicnode.com")));
    }

    function test_live_metadata() public view {
        assertEq(A.VERSION(), "4.2.0", "version");
        assertEq(A.owner(), DOC_OWNER, "owner");
        assertTrue(A.DOMAIN_SEPARATOR() != bytes32(0), "domain separator set");
        assertTrue(A.SET_ALLOWED_TYPEHASH() != bytes32(0), "typehash set");
        assertTrue(A.supportsInterface(type(IAllowlistChecker).interfaceId), "ERC165 IAllowlistChecker");
        // DEFAULT DENY is the single most important property of a permission contract
        assertFalse(A.isAllowed(RAND, TOKEN), "rand not allowed");
        assertFalse(A.isAllowedPublic(RAND), "no public permission");
        assertEq(A.nonces(RAND), 0, "nonce starts at 0");
        assertEq(PermissionFlag.unwrap(A.checkAllowlist(RAND, TOKEN)), 0x0000, "v4 hook path denies");
    }

    function test_nonOwner_cannot_setAllowed() public {
        // error identifiers live inside the declaring contract -> must be qualified
        vm.expectRevert(abi.encodeWithSelector(OwnableUpgradeable.OwnableUnauthorizedAccount.selector, address(this)));
        A.setAllowed(RAND, TOKEN, true);
        assertFalse(A.isAllowed(RAND, TOKEN), "state unchanged after failed call");
    }

    function test_bogus_signature_rejected_and_nonce_not_burned() public {
        uint256 deadline = block.timestamp + 1 hours;
        vm.expectRevert(); // ECDSAInvalidSignature / InvalidSigner
        A.setAllowedWithSignature(RAND, TOKEN, true, 0, deadline, 27, bytes32(uint256(1)), bytes32(uint256(1)));
        assertEq(A.nonces(RAND), 0, "nonce must NOT be consumed on failure");
        assertFalse(A.isAllowed(RAND, TOKEN));
    }

    function test_wrong_nonce_rejected_before_signature() public {
        vm.expectRevert(IAllowlistV4_0.InvalidNonce.selector);
        A.setAllowedWithSignature(RAND, TOKEN, true, 7, block.timestamp + 1 hours, 27, bytes32(uint256(1)), bytes32(uint256(1)));
    }

    function test_expired_deadline_rejected() public {
        vm.expectRevert(IAllowlistV4_0.SignatureExpired.selector);
        A.setAllowedWithSignature(RAND, TOKEN, true, 0, block.timestamp - 1, 27, bytes32(uint256(1)), bytes32(uint256(1)));
    }

    function test_direct_call_to_v3_compat_read_reverts() public {
        vm.expectRevert(IAllowlistV4_2.OnlyCallableByTokenContract.selector);
        A.isAddressAllowedForPrivateInstrument(RAND, "USTB");
    }

    /// @notice DECISIVE test: does a symbol-identical impersonator gain anything?
    function test_symbol_spoofer_cannot_read_real_permissions() public {
        SymbolSpoofer spoofer = new SymbolSpoofer();

        // make a REAL grant on the fork so the test is not vacuously true
        vm.prank(DOC_OWNER);
        A.setAllowed(FRESH, TOKEN, true);
        assertTrue(A.isAllowed(FRESH, TOKEN), "grant landed");

        // the genuine token address sees it
        vm.prank(TOKEN);
        assertTrue(A.isAddressAllowedForPrivateInstrument(FRESH, "USTB"), "real token sees its own grant");

        // the impersonator does NOT
        assertFalse(spoofer.probePrivate(address(A), FRESH), "spoofer reads its own namespace");
        assertFalse(spoofer.probeFund(address(A), FRESH), "spoofer reads its own namespace");
        assertFalse(A.isAllowed(FRESH, address(spoofer)), "spoofer namespace untouched");
    }
}
