// SPDX-License-Identifier: MIT
pragma solidity =0.8.28;

// COPY-AND-MODIFY HARNESS — diamond / role-based authorization audit.
//
// Proven shape (LIT-Protocol/chipotle, 2026-10): 5 tests, 256 fuzz runs, all green.
// Drop into the repo's own test tree (e.g. test/DifferentialAuthz.t.sol) so the
// maintainer runs it with their build:
//     forge test --match-contract DifferentialAuthz -vv
//
// Adapt: import the repo's BaseTest/deploy helper, replace the write/read calls with
// the target's facet API, and keep the four test intents intact:
//   1. every authorization predicate agrees, over the full (resource x wallet) product
//   2. a stranger cannot drive any write on the victim's account
//   3. a registered wallet/derivation-path cannot be re-registered by another account
//   4. a master/owner key does not implicitly gain execution authority
//
// PITFALLS baked in (each one cost a failing run on the real engagement):
//   - views return a SENTINEL (0) instead of reverting -> assert the value, never expectRevert
//   - do NOT nest vm.prank inside vm.startPrank ("cannot override an ongoing prank")
//   - first `forge build`/`forge test` with via_ir=true takes minutes -> run in background

import {BaseTest} from "./helpers/BaseTest.sol";

contract DifferentialAuthz is BaseTest {
    address internal alice = makeAddr("alice");
    address internal bob = makeAddr("bob");
    uint256 internal aliceMaster;

    address[4] internal wallets; // index 0 = all-wallets wildcard (address(0))
    uint256[4] internal cids;    // index 0 = all-actions wildcard (0)

    function setUp() public override {
        super.setUp();
        wallets[0] = address(0);
        wallets[1] = makeAddr("w1");
        wallets[2] = makeAddr("w2");
        wallets[3] = makeAddr("w3");
        cids[0] = 0;
        cids[1] = 111;
        cids[2] = 222;
        cids[3] = 333;

        vm.prank(alice);
        writes.newChainSecuredAccount("alice", "");
        aliceMaster = apiKeyHashOf(alice);
    }

    // ── 1. Differential: every predicate must agree ──────────────────────────
    // Reproduces the classic drift: slow view vs "Fast" view vs combined view.
    function testFuzz_predicatesAgree(uint256 seed) public {
        uint256 groupCount = 1 + (seed % 4);
        for (uint256 g = 0; g < groupCount; g++) {
            uint256 bits = uint256(keccak256(abi.encode(seed, g)));
            uint256[] memory cidSet = new uint256[](4);
            uint256 cidLen;
            for (uint256 i = 0; i < 4; i++) {
                if ((bits >> i) & 1 == 1) cidSet[cidLen++] = cids[i];
            }
            address[] memory pkpSet = new address[](4);
            uint256 pkpLen;
            for (uint256 i = 0; i < 4; i++) {
                if ((bits >> (8 + i)) & 1 == 1) pkpSet[pkpLen++] = wallets[i];
            }
            uint256[] memory trimCids = new uint256[](cidLen);
            for (uint256 i = 0; i < cidLen; i++) trimCids[i] = cidSet[i];
            address[] memory trimPkps = new address[](pkpLen);
            for (uint256 i = 0; i < pkpLen; i++) trimPkps[i] = pkpSet[i];

            vm.prank(alice);
            writes.addGroup(aliceMaster, "g", "", trimCids, trimPkps);
        }

        // Scope set for one usage key: subset of {0 (=wildcard), 1..groupCount},
        // plus a seed-chosen expiration (0 = never, future = live, past = expired).
        uint256 usage = uint256(keccak256(abi.encode(seed, "usage")));
        uint256[] memory execute = new uint256[](groupCount + 1);
        uint256 execLen;
        for (uint256 i = 0; i <= groupCount; i++) {
            if ((usage >> i) & 1 == 1) execute[execLen++] = i;
        }
        uint256[] memory trimExec = new uint256[](execLen);
        for (uint256 i = 0; i < execLen; i++) trimExec[i] = execute[i];
        uint256[] memory empty = new uint256[](0);

        uint256 expiration = ((usage >> 16) & 1 == 1) ? block.timestamp + 1000 : 0;
        uint256 usageHash = uint256(keccak256("usage-key"));
        vm.prank(alice);
        writes.setUsageApiKey(
            aliceMaster, usageHash, expiration, 0, "u", "",
            false, false, false, empty, empty, empty, trimExec
        );

        for (uint256 c = 0; c < 4; c++) {
            bool slowExec = views_.canExecuteAction(usageHash, cids[c]);
            bool fastExec = views_.canExecuteActionFast(usageHash, cids[c]);
            assertEq(slowExec, fastExec, "exec/fast exec disagree");

            for (uint256 w = 0; w < 4; w++) {
                bool slowWallet = views_.canUseWalletInAction(usageHash, cids[c], wallets[w]);
                bool fastWallet = views_.canUseWalletInActionFast(usageHash, cids[c], wallets[w]);
                (bool combExec, bool combWallet) =
                    views_.canExecuteActionAndUseWallet(usageHash, cids[c], wallets[w]);

                assertEq(slowWallet, fastWallet, "wallet/fast wallet disagree");
                assertEq(slowWallet, combWallet, "wallet/combined wallet disagree");
                assertEq(slowExec, combExec, "exec/combined exec disagree");
                if (slowWallet) assertTrue(slowExec, "wallet without exec"); // documented invariant
            }
        }
    }

    // ── 2. Stranger must not drive ANY write on the victim's account ─────────
    function test_strangerCannotWriteVictimAccount() public {
        uint256[] memory empty = new uint256[](0);
        address[] memory noPkps = new address[](0);

        vm.startPrank(bob);
        vm.expectRevert();
        writes.addGroup(aliceMaster, "x", "", empty, noPkps);

        vm.expectRevert();
        writes.setUsageApiKey(
            aliceMaster, uint256(keccak256("bob-key")), 0, 0, "x", "",
            true, true, true, empty, empty, empty, empty
        );

        vm.expectRevert();
        writes.registerWalletDerivation(aliceMaster, makeAddr("bobWallet"), wp(0xB0B), "x", "");

        vm.expectRevert();
        writes.removeWalletDerivation(aliceMaster, address(0xBEEF));

        // Own account + victim's group id must not resolve either.
        // NOTE: no inner vm.prank here — startPrank already impersonates bob.
        writes.newChainSecuredAccount("bob", "");
        vm.expectRevert();
        writes.updateGroup(apiKeyHashOf(bob), 1, "x", "", empty, noPkps);
        vm.stopPrank();
    }

    // ── 3. Registered wallet / derivation path cannot be hijacked ────────────
    function test_strangerCannotHijackRegisteredWalletOrPath() public {
        address wallet = makeAddr("aliceWallet");
        uint256 path = wp(0xA11CE);
        vm.prank(alice);
        writes.registerWalletDerivation(aliceMaster, wallet, path, "w", "");

        vm.prank(bob);
        writes.newChainSecuredAccount("bob", "");
        uint256 bobMaster = apiKeyHashOf(bob);

        vm.prank(bob);
        vm.expectRevert();
        writes.registerWalletDerivation(bobMaster, wallet, wp(0xB0B), "w", ""); // same id, new path

        vm.prank(bob);
        vm.expectRevert();
        writes.registerWalletDerivation(bobMaster, makeAddr("bobWallet"), path, "w", ""); // victim's path

        // Views return a SENTINEL (0) for an unregistered wallet — assert, never expectRevert.
        assertEq(views_.getWalletDerivation(aliceMaster, wallet), path);
        assertEq(views_.getWalletDerivation(bobMaster, wallet), 0);
    }

    // ── 4. Namespace squat: pre-registering the victim's hash must not block
    //       onboarding, and must not leave the squatter with access ───────────
    function test_namespaceSquatIsEvictedAndDoesNotGrantAccess() public {
        address victim = makeAddr("victim");
        uint256 victimHash = apiKeyHashOf(victim);

        vm.prank(bob);
        writes.newChainSecuredAccount("bob", "");
        uint256 bobMaster = apiKeyHashOf(bob);
        uint256[] memory empty = new uint256[](0);
        vm.prank(bob);
        writes.setUsageApiKey(
            bobMaster, victimHash, 0, 0, "squat", "", false, false, false,
            empty, empty, empty, empty
        );
        assertEq(views_.getAccountWalletAddress(victimHash), bob);

        vm.prank(victim);
        writes.newChainSecuredAccount("victim", "");
        assertEq(views_.getAccountWalletAddress(victimHash), victim);

        assertFalse(views_.canExecuteAction(victimHash, cids[1]));
        assertFalse(views_.canExecuteAction(victimHash, cids[0]));

        vm.prank(bob);
        vm.expectRevert();
        writes.addGroup(victimHash, "x", "", empty, new address[](0));
    }

    // ── 5. Master/owner key has no implicit execution authority ──────────────
    function test_masterKeyHasNoExecutionAuthority() public {
        uint256[] memory empty = new uint256[](0);
        vm.prank(alice);
        uint256 gid = writes.addGroup(aliceMaster, "g", "", empty, new address[](0));
        assertEq(gid, 1);
        assertFalse(views_.canExecuteAction(aliceMaster, cids[1]));
        assertFalse(views_.canUseWalletInAction(aliceMaster, cids[1], wallets[1]));
    }
}
