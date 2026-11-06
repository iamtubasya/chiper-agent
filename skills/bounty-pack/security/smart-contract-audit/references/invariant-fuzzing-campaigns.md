# Invariant fuzzing campaigns on real (upgradeable, role-gated) contracts — medusa + echidna

Proven 2026-10-12 on Vana Data Portability: the escrow **implementation** (UUPS) behind its live proxy,
solc 0.8.24 / viaIR / optimizer runs=1 (the settings the verified deployment reports).

Property under test: **a caller WITHOUT the privileged role must never extract value, and the escrow's
ledger must stay covered by real token balance.** The harness is the attacker.

## Campaign shape that works

1. Foundry project with the recovered source under `contracts/` (recovery + remappings:
   `onchain-source-recovery`), `foundry.toml` pinned to the deployed compiler settings.
2. **The harness MUST live under the compiled source dir (`contracts/`), NOT `test/`.**
   crytic-compile — used by *both* medusa and echidna — compiles the project's `src`; a harness in
   `test/` is invisible. Neither symptom looks like a placement bug:
   * medusa: `error Failed to start fuzzer` / `no assertion, property, optimization, or custom tests were found to fuzz`
   * echidna: `Compiling '.'... Given contract "EscrowInvariant" not found in given file`
   Both cured by moving the file to `contracts/harness/` (rewrite the relative imports one level).
3. UUPS implementations call `_disableInitializers()` in the constructor, so `new Impl()` +
   `initialize(...)` reverts. Deploy behind a **minimal ERC1967 proxy** — ~30 lines is enough:
   `sstore` the impl slot `0xREDACTED_********`,
   `delegatecall` the init data, fallback-delegate with return-data bubbling, `receive() external payable {}`.
4. **Wire roles so the harness can set up fixtures but cannot act as the role under test:**
   * harness == `DEFAULT_ADMIN_ROLE` → `initialize(address(this), <facilitator>)`;
   * the privileged role goes to a separate constant address the harness can never become;
   * fixture setup must go through the admin path first. On the escrow that meant
     `setTokenWhitelisted(address(token), true)` **before** `depositToken(...)`, otherwise the harness
     reverts `AssetNotSupported(token)` during `setUp` and the campaign tests nothing while looking fine.
5. Expose every property under BOTH prefixes — `invariant_*` (foundry/medusa) and `echidna_*` (echidna
   wants `echidna_` bool functions). Aliases are cheaper than re-instrumenting.

## Commands (Windows host with forge/medusa/echidna on PATH)

```bash
medusa fuzz --compilation-target . --target-contracts <HarnessName> --timeout 600 --seq-len 15 --workers 2 --no-color
echidna . --contract <HarnessName> --test-mode property --timeout 300
```

Medusa prints `calls / seq-s / branches / corpus / failures N/M` every ~3 s and ends with a per-test PASS
table + `Test summary: N test(s) passed, M test(s) failed`. Example real negative: **3,606,416 calls,
514 branches, 16 corpus, 0 failures, 13/13 passed**. Keep `crytic-export/coverage/coverage_report.html` and
`lcov.info`.

Budget on a 4-vCPU box: 600 s medusa / 300 s echidna caps; do not run the fuzzers next to other heavy jobs
(symbolic execution, another fuzzer, WSL builds).

## ⛔ A falsification whose trace never touches the contract under test is a SPEC bug

echidna run 1 printed `echidna_no_unauthorized_extraction: failed! Reason: ReturnFalse` with a sequence of
two `deposit_more(...)` calls. The trace showed only `balanceOf` after two mints — **no escrow function was
ever entered**. Cause: the harness's own `deposit_more` calls `token.mint(address(this), amt)` (the harness
is the mock token's minter), so the "attacker" balance legitimately rose; the property compared against the
baseline only. The invariant was mis-specified, the protocol was not.

```solidity
uint256 public mintedByHarness;                                  // += amt inside deposit_more, after mint(...)
// tokens arriving FROM the escrow still break this:
return token.balanceOf(attacker) <= attackerBaseline + mintedByHarness;
```

Rules that follow:
* Read the counterexample **trace**, not just the verdict, before believing a falsification.
* Write it into the evidence file ("first falsification was the harness's own faucet, spec tightened,
  re-run") — a fuzzer falsifying a bad spec is expected behaviour, and filing it as a protocol bug would
  have been a **false finding**.
* Same discipline as a red control in a unit test: if the rig is red, fix the rig and say so.

## ⛔ Defect #2: `ErrorRevert` on a property with an EMPTY call sequence = harness arithmetic, not the target

After the spec fix above, echidna run 2 printed:

```
echidna_no_unauthorized_extraction: failed!💥
  Reason: ErrorRevert
  Call sequence:
echidna_escrow_ledger_covered: passing
```

A **reverting property function is reported as failed** by echidna, and the giveaway is the *empty*
sequence — nothing was executed, the view itself blew up. Cause: echidna feeds values near 2**256
(run 1's counterexample read `deposit_more(0x36…e76)`), the harness accumulated them into
`mintedByHarness`, and Solidity 0.8 checked arithmetic made `attackerBaseline + mintedByHarness`
overflow → revert. Again the rig, not the escrow (medusa's property table stayed 14/14 that same run).

Fix — bound every fuzz entry point and compute through named locals:

```solidity
function deposit_more(uint256 amt) public {
    amt = amt % 1_000_000 ether;   // bound input: keeps harness arithmetic in range
    ...
}
// and in the property:
uint256 bal = token.balanceOf(attacker);
uint256 allowed = attackerBaseline + mintedByHarness;   // inputs bounded -> cannot overflow
return bal <= allowed;
```

Triage table for a "failed" property on a harness like this — use it before touching the target again:

| verdict in the log | trace | read it as |
|---|---|---|
| `ReturnFalse` | sequence touches only harness helpers (mint/balanceOf) | bad PROPERTY (spec) |
| `ErrorRevert`, empty sequence | nothing executed | harness ARITHMETIC / unbound input |
| `ReturnFalse` | an escrow frame (`settle`/`withdraw`/`_payout`) appears | investigate — possibly real |

Final clean run on the same target (for the ledger row): medusa **14/14 passed, 1,776,135 calls, 518
branches**; echidna **both properties passing, 50,253 calls, seed 2568666351240263642** — after two
harness-level fixes that are documented as such in `B4_fuzzing_evidence.md`.

## Evidence + liveness conventions

* **Log to an ABSOLUTE path.** A relative redirect (`> ../../evidence/x.log`) is resolved against the
  *outer* shell's cwd, so the job dies instantly with `No such file or directory` and leaves an empty log —
  which reads exactly like "fuzzing found nothing".
* Logs piped through `tail`/`tee` buffer: a 24-byte log after 10 minutes is normal. Prove liveness by
  **CPU delta on the fuzzer process** (`+45 s CPU per 20 s wall` ≈ 2 workers actually working), never by
  log growth.
* Ledger rows for fuzzers must be one of: `clean (N calls, M branches)` / `FALSIFIED (spec) → re-run clean` /
  `BLOCKED: <reason>` — with the artifact path, so the row is checkable.
* Keep the harness source in the engagement tree: it is the proof that the property matched the claim.
