# Auditing a source-codebase / DLT-code bounty (Immunefi Blockchain/DLT, GitHub-repo assets)

Verified shape: 2026-10, Hedera (Immunefi). Assets in scope were **8 GitHub source repos** under
`hiero-ledger` (`hiero-consensus-node`, `hiero-mirror-node`, `hiero-json-rpc-relay`,
`hiero-cryptography`, `hiero-sdk-{js,go,java}`). The program forbids *any* mainnet/public-testnet
testing and DoS. There is **no HTTP host to scan**.

## 1. Recognise the shape (do this in 0A before touching a tool)
- Program tab = **Blockchain/DLT** and "Assets in Scope" lists **repositories**, not domains/IPs.
- Rules text contains: "all testing should be done on local-forks" / "no testing on mainnet" /
  "no DoS" / "no automated testing that generates significant traffic".
- ⇒ **Track = WHITE-BOX source review. 0D web2 scanner gate = `N/A-BLOCKED`** (never "passed";
  there is no surface, and firing scanners would breach the program). Same 0E/0F deliverables.
- This is the codebase cousin of the smart-contract/protocol track already in SKILL.md.

## 2. Where high-value bugs actually live (priority order)
1. **Newest / unreviewed modules.** `git log --oneline -60` on each repo; flags and schema bumps
   (`V0780…Schema`) mark fresh code. "NEW == UNREVIEWED". In Hedera the richest area was the
   brand-new **CLPR cross-ledger service** (peer-ledger bridge: Ethereum sync-committee, Besu QBFT,
   Sei CometBFT verifiers).
2. **Feature-gated paths.** A new service behind `config.enabled=false` is still in scope (the
   program says reports "remain in scope and are encouraged"), just downranked one level for
   "Functionality Not Active in Production". Always check the default + the master gate
   (Hedera: `AbstractClprSystemContract.isDisabled()` → `clpr.enabled`).
3. **Shipped security primitives that are no-ops / stubs** (see §3) — the single best hit this
   session.
4. **Signature / authorization / proof-verification paths** — anything that decides "who approved
   this" (signature maps, multisig quorums, SSZ Merkle branches, MPT/RLP proofs, TSS seals).
5. **Dependency CVEs** — run them, but they are *informational* unless a reachable path to real
   impact is shown. Expect most to be transitive/dev and N/A.

## 3. The "shipped verification stub" hunt (reusable recipe)
A security check that is stubbed in **`src/main`** (not test) and wired into a production call site
is a high-severity authentication bypass. Hunt for it:

```bash
# 3a. No-op / stub primitives shipped in production source (exclude tests)
rg -n -i -e 'accepts every|accepts any|Temporary,|insecure stand-in|return true;|no-op|placeholder' \
   <repo> -g '!**/test/**' -g '!**/testFixtures/**' -g '!*.md'

# 3b. Is there a REAL implementation, or is the fake the only one?
rg -n --no-heading 'implements <SecurityInterface>' <repo> | grep -v '/test/'

# 3c. Wiring — who instantiates the fake in main?
rg -n -e 'new <Verifier>\((Fake|Stub|NoOp|Dummy)' <repo> -g '!**/test/**'
```
Real example (Hedera, report-ready): `FakeBlsSignatureVerifier.fastAggregateVerify()` returns
`true` unconditionally; it is the **only** `BlsSignatureVerifier` impl in the tree and is wired into
the CLPR Ethereum verifier system contract (`0x171`) at two production call sites. The sync-committee
BLS signature is the trust root of the whole proof chain, so its absence lets an attacker forge
cross-ledger bundles. Reported as **High** (Critical impact, downranked per the "not active in
production" clause because `clpr.enabled` defaults `false`).
Lesson: distinguish *self-documented temporary* stubs (triager may call them "known") from genuine
unknown logic bugs — report the stub anyway (in scope, encouraged) but ALSO keep hunting the
non-obvious logic flaws that survive once the real crypto lands.

## 4. Windows clone & SAST invocation fixes (these are *fixes*, not "tool broken")
- **Large repo checkout fails (`git clone` rc=128, "unable to checkout working tree"):**
  Windows long-path limit. Fix inside the clone dir, then restore:
  `git config core.longpaths true && git config core.protectNTFS false && git restore --source=HEAD :/`
  Verify: `find <repo> -name '*.java' | wc -l` (a usable tree is present even if `git status` looks dirty).
- **`git -C <msyspath>` fails** (native git can't read `/d/...`) — `cd` into the repo instead, or use
  native `D:/...` paths. Same MSYS trap for `rg`/`python`/`gosec` when `MSYS_NO_PATHCONV=1` is set:
  hand them **Windows-style** paths (`D:/data/...`), not `/d/data/...`.
- **`go install`/govulncheck/gosec "GOMODCACHE entry is relative":** set
  `export GOPATH='C:/Users/<u>/go'; export GOMODCACHE='C:/Users/<u>/go/pkg/mod'` (forward-slash
  Windows form). A TLS-timeout during `go install` is transient — plain retry succeeds.
- **`gosec ./...` is impractically slow** on a repo with many `examples/` (compiles every package,
  50+ min). Scope it: `gosec -fmt=json -out=x.json -exclude-dir=examples,tck,testing ./sdk/...`.
- **semgrep may be broken on this host** (semgrep-core) — fall back to `rg` sweeps + `gosec` +
  `govulncheck` + `npm audit`. Do not record this as a permanent constraint; retry semgrep when fixed.

## 5. Answering the coverage question mechanically ("sudah pakai all tools? all varian?")
Never "yes, all done". For a multi-repo codebase target, "all tools / all variants" is not
achievable in one session — say so. Produce, from disk:
1. **Phase status** (0A/0B/0C/0D=N/A-blocked/0E/0F) read off the artifact set, not memory.
2. **Per-tool table:** INSTALLED-and-fired (with the evidence file that proves it) vs
   INSTALLED-but-never-fired (the real gap) vs NOT-INSTALLED. Scanner-class tools (nuclei/ffuf/
   sqlmap/dalfox/…) are **N/A by program rule** here — state that, never "passed".
3. **Coverage ledger:** which modules/files were read in depth; a "NOT reviewed" list
   (Besu/Sei verifiers, mirror-node importer, SDK signing, WRAPS/Nova cryptanalysis, relay runtime…).
4. Every negative that was *actually tested* is a documented result; everything untouched is "not done".

## 6. Pitfalls
- Do **not** fire web2 scanners at a repo-only program — there is nothing to hit and it may breach
  the rules; mark 0D N/A and say why.
- Do **not** overclaim: "the code was reviewed" ≠ "the scanner gate passed".
- `delegate_task` for per-repo deep review timed out at 600s with no output here — do the review
  in-session with targeted `rg`/`read_file`, not delegated reading.
- `npm audit` on a monorepo reports nested dev/transitive advisories (e.g. `axios` under a dev CLI)
  that do not touch runtime — separate `dependencies` from `devDependencies` before calling anything a finding.
- Well-known **local/test keys** committed in `tck/docker-compose.yml` are not secrets (Hedera ships
  a public local operator key) — verify against the project's own docs before reporting.
