# Isolated-compile PoC — real runtime proof without building the project

**Problem.** You have a finding in a large codebase (Hedera consensus node = ~300 MB / 7k+ Java
files). A full `./gradlew` build is 30–90 min and may fail outright, yet a *runtime* PoC is stronger
than "the method returns `true`, trust me". Re-implementing the logic in a scratch script is weak —
it proves your copy, not the shipped code.

**Method.** If the security-relevant class has few imports, **copy it verbatim** from the repo and
compile it standalone with `javac`, supplying shims for any missing annotations, then drive it from a
tiny `Main`. The PoC then executes the *actual shipped source*.

## Steps

1. `read_file` the class; list its imports. Candidate if they are only JDK + a small annotation lib
   (e.g. `edu.umd.cs.findbugs.annotations.NonNull`).
2. Lay out a harness with **package-matching directories**:
   ```
   poc/src/<declared-package-path>/<Class>.java   # copied verbatim, unmodified
   poc/src/<annotation-package>/NonNull.java      # compilation shim (label it clearly!)
   poc/src/poc/Main.java                          # driver
   ```
3. Compile + run with no build system:
   ```bash
   javac -d out $(find src -name '*.java')
   java -cp out poc.Main | tee ../evidence/<name>-run.txt
   ```
4. Assert the bypass / the missing check and capture stdout as evidence.

## Caveats

- **Package vs directory mismatch.** `javac` given an explicit file list accepts a file whose
  directory doesn't match its `package` (Hedera ships
  `verifier/ethereum/BlsSignatureVerifier.java` that declares `package ...impl.verifier`). Put the copy
  in the *declared-package* directory anyway — cheapest way to avoid surprises.
- **Too many deps → stop.** If the class drags in protobuf runtime / logging / DI, do NOT re-implement.
  Ship the code-level PoC (exact lines + call sites) and a JUnit test for the maintainer.
- **Two forms, two audiences.** Isolated harness = YOUR evidence. JUnit test in the repo's own test
  tree = the MAINTAINER's run (`./gradlew :module:test --tests '*X*'`). Provide both.
- The shim file must say it's a shim — a reader must never mistake it for upstream code.

## Worked case — Hedera CLPR Ethereum verifier (2026-10)

- **Finding:** `FakeBlsSignatureVerifier.fastAggregateVerify(...)` returns `true` unconditionally (no
  BLS12-381 check), and it is the production wiring in `EthereumVerifyBundleCall` /
  `EthereumVerifyConfigCall` → a forged Ethereum sync-committee bundle passes verification.
- **Why isolated-compile worked:** the fake and its interface imported only `java.util.List` +
  `edu.umd.cs.findbugs.annotations.NonNull`. A ~6-line `NonNull` shim was the only thing needed.
- **Result** (`evidence/poc-fakebls-run.txt`):
  ```
  [1]  fastAggregateVerify(512 x 48B-zero pubkeys, 32B msg, 96B ZERO sig) = true
  [1b] ...with a 0xAB-filled 96-byte signature = true
  [2]  caller-supplied bitset -> participants=342; 3*n < 2*512 ? false => participation gate passes
  PROVEN: the BLS signature gate is a no-op and the participation gate is trivially met.
  ```
- **Impact tie-in:** the file that was run is `src/main/java/...` (ships in the node artifact), and it
  is the *only* implementation of the interface — so the PoC closes the "maybe a guard exists
  elsewhere" question. Reachability was a feature flag (`clpr.enabled`, default false) → honest
  downgrade recorded in the report rather than overclaiming Critical.
